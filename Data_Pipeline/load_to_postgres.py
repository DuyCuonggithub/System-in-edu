# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
LOADER SCRIPT: Local Parquet files -> PostgreSQL Data Warehouse
=============================================================================
Tính năng:
1. Ưu tiên đọc file từ LOCAL folder (../Scraper/data/) -- không cần MinIO
2. Fallback đọc từ MinIO nếu LOCAL không có file
3. Incremental Load: Chỉ nạp file mới chưa từng nạp
4. Auto Schema: Tự động tạo bảng và schema 'raw' nếu chưa có
5. Credentials đúng với docker-compose.yml (user_dw / password_dw / udemy_dw)
"""

import os
import glob
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# --- CẤU HÌNH ---
load_dotenv()

# ============================================================
# 1. Postgres DW Config (khớp với docker-compose.yml)
#    docker-compose: POSTGRES_USER=user_dw / POSTGRES_PASSWORD=password_dw / POSTGRES_DB=udemy_dw
#    Port ngoài Windows: 5433
# ============================================================
DB_USER = os.getenv("DB_USER", "user_dw")
DB_PASS = os.getenv("DB_PASS", "password_dw")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5433")
DB_NAME = os.getenv("DB_NAME", "udemy_dw")

DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ============================================================
# 2. Đường dẫn LOCAL chứa file parquet (relative từ script này)
#    Script đặt ở: project/database/
#    Data ở:       project/Scraper/data/
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_DIR = os.path.join(SCRIPT_DIR, "..", "Scraper", "log")

# ============================================================
# 3. MinIO Config (dùng khi LOCAL không có file)
# ============================================================
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
BUCKET_NAME = "udemy123"


# ============================================================
# DATABASE HELPERS
# ============================================================
def get_db_engine():
    return create_engine(DB_URL)


def init_infrastructure(engine):
    """Khởi tạo Schema 'raw' và Bảng Log nếu chưa có"""
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw;"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS raw.loaded_files_log (
                filename TEXT PRIMARY KEY,
                loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                row_count INT,
                status TEXT
            );
        """))
    print("[setup] ✅ Đã kiểm tra hạ tầng DB (Schema raw + Log Table).")


def get_loaded_files(engine):
    """Lấy danh sách file đã nạp thành công"""
    try:
        df = pd.read_sql("SELECT filename FROM raw.loaded_files_log WHERE status = 'SUCCESS'", engine)
        return set(df['filename'].tolist())
    except Exception:
        return set()


def log_file_status(engine, filename, status, row_count=0):
    """Ghi lại trạng thái nạp file"""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO raw.loaded_files_log (filename, status, row_count, loaded_at)
                VALUES (:fn, :st, :rc, NOW())
                ON CONFLICT (filename) DO UPDATE
                SET status = :st, row_count = :rc, loaded_at = NOW();
            """),
            {"fn": filename, "st": status, "rc": row_count}
        )


# ============================================================
# TABLE MAPPING
# ============================================================
def determine_target_table(filename: str):
    """
    Ánh xạ tên file → tên bảng trong schema raw.
    Kết quả: 'courses' | 'instructors' | 'price_tracker' | None
    
    Quy tắc dựa trên đuôi file (sau timestamp):
      *_courses.parquet      -> raw.courses
      *_instructors.parquet  -> raw.instructors
      tracker*_courses.parquet -> raw.price_tracker
    """
    base = os.path.basename(filename).lower()

    if base.endswith("_instructors.parquet"):
        return "instructors"
    elif "tracker" in base and base.endswith("_courses.parquet"):
        return "price_tracker"
    elif base.endswith("_courses.parquet"):
        return "courses"
    return None


# ============================================================
# DATA CLEANING
# ============================================================
def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa dữ liệu trước khi nạp vào Postgres"""
    # 1. Tên cột: chữ thường, bỏ khoảng trắng
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

    # 2. rating_distribution: ép sang string (JSON text) để tránh lỗi type
    if "rating_distribution" in df.columns:
        df["rating_distribution"] = df["rating_distribution"].astype(str)

    # 3. Replace NaN bằng None để psycopg2 hiểu là NULL
    df = df.where(pd.notnull(df), None)

    return df


# ============================================================
# LOCAL FILE LOADER
# ============================================================
def list_local_parquet_files(data_dir: str):
    """Liệt kê tất cả file .parquet trong thư mục LOCAL"""
    pattern = os.path.join(data_dir, "*.parquet")
    files = glob.glob(pattern)
    # Trả về list các tên file (relative) để dùng làm key trong log
    return [os.path.basename(f) for f in files]


def load_from_local(filename: str, data_dir: str) -> pd.DataFrame:
    """Đọc file parquet từ thư mục LOCAL"""
    path = os.path.join(data_dir, filename)
    return pd.read_parquet(path)


# ============================================================
# MINIO FILE LOADER (fallback)
# ============================================================
def get_s3_client():
    """Khởi tạo kết nối đến MinIO"""
    import boto3
    return boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name='us-east-1'
    )


def list_minio_parquet_files(s3_client, bucket):
    """Liệt kê file parquet trong MinIO bucket"""
    parquet_files = []
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=bucket)
    for page in pages:
        if 'Contents' in page:
            for item in page['Contents']:
                if item['Key'].endswith('.parquet'):
                    parquet_files.append(item['Key'])
    return parquet_files


def load_from_minio(s3_client, bucket, key) -> pd.DataFrame:
    """Đọc file parquet từ MinIO"""
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    file_content = obj['Body'].read()
    return pd.read_parquet(io.BytesIO(file_content))


# ============================================================
# CORE LOADER
# ============================================================
def load_dataframe_to_postgres(engine, df: pd.DataFrame, table_name: str):
    """Nạp DataFrame vào bảng raw.<table_name> trong Postgres"""
    from pandas.io.sql import get_schema

    create_stmt = get_schema(df, table_name, schema="raw")
    create_stmt = create_stmt.replace("CREATE TABLE", "CREATE TABLE IF NOT EXISTS")

    with engine.begin() as conn:
        conn.execute(text(create_stmt))
        cols = ",".join([f'"{c}"' for c in df.columns])
        vals = ",".join([f":{c}" for c in df.columns])
        insert_stmt = f'INSERT INTO raw."{table_name}" ({cols}) VALUES ({vals})'
        data = df.to_dict(orient='records')
        if data:
            conn.execute(text(insert_stmt), data)


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("  [START] LOAD DATA -> PostgreSQL DW")
    print(f"  DB: {DB_HOST}:{DB_PORT}/{DB_NAME} (user={DB_USER})")
    print("=" * 60)

    # 1. Kết nối DB
    try:
        engine = get_db_engine()
        init_infrastructure(engine)
    except Exception as e:
        print(f"[ERROR] Loi ket noi DB: {e}")
        return

    # 2. Xác định nguồn dữ liệu: MinIO (ưu tiên) hoặc LOCAL
    # [MỚI] Ưu tiên MinIO nếu có kết nối được
    print(f"\n[CHECK] Ket noi MinIO ({MINIO_ENDPOINT})...")
    s3_client = None
    try:
        s3_client = get_s3_client()
        # Thử list để check connection
        s3_client.list_objects_v2(Bucket=BUCKET_NAME, MaxKeys=1)
        use_local = False
        print(f"   [OK] Ket noi MinIO thanh cong. Dung MinIO lam nguon chinh.")
    except Exception as e:
        print(f"   [WARN] Khong the ket noi MinIO: {e}")
        use_local = True

    if not use_local:
        try:
            all_files = list_minio_parquet_files(s3_client, BUCKET_NAME)
            print(f"\n[SOURCE] MinIO")
            print(f"   Total .parquet files in bucket '{BUCKET_NAME}': {len(all_files)}")
        except Exception as e:
            print(f"[ERROR] MinIO listing failed: {e}")
            return
    else:
        local_dir = os.path.abspath(LOCAL_DATA_DIR)
        if os.path.isdir(local_dir):
            print(f"\n[SOURCE] LOCAL folder:")
            print(f"   {local_dir}")
            all_files = list_local_parquet_files(local_dir)
            print(f"   Total .parquet files: {len(all_files)}")
        else:
            print(f"[ERROR] LOCAL folder khong ton tai: {local_dir}")
            return

    # 3. Lọc file chưa nạp
    loaded_files = get_loaded_files(engine)
    new_files = [f for f in all_files if os.path.basename(f) not in loaded_files]

    print(f"\n[INFO] Already loaded: {len(loaded_files)} files")
    print(f"[INFO] New files to load: {len(new_files)} files")

    if not new_files:
        print("\n[OK] System is up-to-date. No new files.")
        return

    # 4. Nạp từng file
    success_count = 0
    fail_count = 0

    for filename in new_files:
        base_name = os.path.basename(filename)
        table_name = determine_target_table(base_name)

        if not table_name:
            print(f"\n[SKIP] Cannot identify target table for: {base_name}")
            continue

        print(f"\n[Processing] {base_name}")
        print(f"    -> raw.{table_name}")

        try:
            # Đọc file
            if use_local:
                df = load_from_local(base_name, local_dir)
            else:
                df = load_from_minio(s3_client, BUCKET_NAME, filename)

            # Làm sạch
            df = clean_dataframe(df)

            # Nạp vào Postgres
            load_dataframe_to_postgres(engine, df, table_name)

            # Ghi log thành công
            log_file_status(engine, base_name, "SUCCESS", len(df))
            print(f"    [OK] Loaded +{len(df)} rows")
            success_count += 1

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"    [ERROR] {e}")
            log_file_status(engine, base_name, "FAILED", 0)
            fail_count += 1

    print("\n" + "=" * 60)
    print(f"  RESULT: {success_count} SUCCESS  |  {fail_count} FAILED")
    print("=" * 60)


if __name__ == "__main__":
    main()