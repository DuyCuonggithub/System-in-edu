import os
import pandas as pd
import boto3
import io
from botocore.exceptions import ClientError
from dotenv import load_dotenv

def main():
    print("========================================")
    print("  CSV TO PARQUET & UPLOAD TO MINIO")
    print("========================================")

    # Load environment variables
    load_dotenv()
    
    MINIO_ENDPOINT = "http://minio:9000"
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
    BUCKET_NAME = "udemy123"

    print(f"[INFO] Connecting to MinIO at {MINIO_ENDPOINT}")

    from botocore.client import Config
    # Initialize S3 client
    s3_client = boto3.client(
        's3',
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name='us-east-1',
        config=Config(signature_version='s3v4', s3={'addressing_style': 'path'})
    )

    # Create bucket if it doesn't exist
    try:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
        print(f"[OK] Bucket '{BUCKET_NAME}' exists.")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            print(f"[INFO] Bucket '{BUCKET_NAME}' not found. Creating...")
            s3_client.create_bucket(Bucket=BUCKET_NAME)
            print(f"[OK] Bucket '{BUCKET_NAME}' created.")
        else:
            print(f"[ERROR] Could not check bucket: {e}")
            return

    # Define paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(script_dir, "..", "Scraper", "log", "Dữ liệu chưa xử lý", "data")

    # Map CSV files to their Parquet destinations in MinIO
    # Note: Using names that will match `load_to_postgres.py` determine_target_table()
    file_mappings = [
        {
            "csv_file": "courses.csv",
            "minio_key": "dashboard/PROD_dashboard_courses.parquet"
        },
        {
            "csv_file": "instructors.csv",
            "minio_key": "dashboard/PROD_dashboard_instructors.parquet"
        },
        {
            "csv_file": "price_tracker.csv",
            "minio_key": "tracker/PROD_tracker_courses.parquet"
        }
    ]

    success_count = 0

    for mapping in file_mappings:
        csv_path = os.path.join(source_dir, mapping["csv_file"])
        minio_key = mapping["minio_key"]

        print(f"\n[Processing] {mapping['csv_file']}")
        if not os.path.exists(csv_path):
            print(f"  [ERROR] File not found: {csv_path}")
            continue

        try:
            # Read CSV
            print(f"  -> Reading CSV...")
            df = pd.read_csv(csv_path)
            
            # Write to Parquet in memory
            print(f"  -> Converting to Parquet ({len(df)} rows)...")
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False)
            parquet_buffer.seek(0)
            
            # Upload to MinIO
            print(f"  -> Uploading to MinIO: {BUCKET_NAME}/{minio_key}")
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=minio_key,
                Body=parquet_buffer.getvalue()
            )
            print(f"  [OK] Successfully uploaded.")
            success_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to process {mapping['csv_file']}: {e}")

    print("\n========================================")
    print(f"  RESULT: {success_count}/{len(file_mappings)} files successfully uploaded.")
    print("========================================")

if __name__ == "__main__":
    main()
