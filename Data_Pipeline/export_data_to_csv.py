import psycopg2
import csv
import os

DB_HOST = "localhost"
DB_PORT = "5433"
DB_USER = "user_dw"
DB_PASS = "password_dw"
DB_NAME = "udemy_dw"

def export_table_to_csv(schema_name, table_name, output_dir):
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            dbname=DB_NAME
        )
        cur = conn.cursor()
        
        cur.execute(f"SELECT * FROM {schema_name}.{table_name};")
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        
        output_path = os.path.join(output_dir, f"{table_name}.csv")
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(colnames)
            writer.writerows(rows)
            
        print(f"[{schema_name}.{table_name}] -> {output_path} ({len(rows)} dong)")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error {schema_name}.{table_name}: {e}")
        return False

if __name__ == "__main__":
    dir_raw = "Dataset_Chua_Xu_Ly"
    dir_processed = "Dataset_Da_Xu_Ly"
    
    if not os.path.exists(dir_raw): os.makedirs(dir_raw)
    if not os.path.exists(dir_processed): os.makedirs(dir_processed)
        
    print("=== XUAT DU LIEU CHUA XU LY (RAW) ===")
    export_table_to_csv("raw", "courses", dir_raw)
    export_table_to_csv("raw", "instructors", dir_raw)
    export_table_to_csv("raw", "price_tracker", dir_raw)
    
    print("\n=== XUAT DU LIEU DA XU LY (MARTS) ===")
    marts_tables = [
        "dim_course", "dim_instructor", "dim_category", 
        "dim_language", "dim_level", "dim_date",
        "bridge_course_instructors", "fct_course_snapshot", 
        "fct_price_history", "fct_instructor_prestige"
    ]
    for t in marts_tables:
        export_table_to_csv("public_marts", t, dir_processed)
        
    print("\n[OK] Hoan tat viec xuat CSV!")
