from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

# 1. Định nghĩa các tham số mặc định cho DAG
default_args = {
    'owner': 'Sinh_Vien_DUE',
    'depends_on_past': False,
    'start_date': datetime(2023, 10, 1),
    'email_on_failure': False,
    'retries': 1, # Thử lại 1 lần nếu lỗi
    'retry_delay': timedelta(minutes=5),
}

# 2. Khởi tạo DAG
with DAG(
    'End_to_End_Pipeline', # Tên hiển thị trên giao diện
    default_args=default_args,
    description='ETL Pipeline từ Web cào dữ liệu vào Postgres DWH',
    schedule_interval=None, # None nghĩa là chỉ chạy khi bạn bấm nút (Trigger thủ công)
    catchup=False,
    tags=['DATN', 'Udemy'],
) as dag:

    # 3. Mảng Cào Dữ Liệu (EXTRACT) - Chỉ chạy Tracker
    task_scrape_tracker = BashOperator(
        task_id='TEST_Scrape_Tracker',
        bash_command='cd /opt/airflow/project/Scraper && xvfb-run --auto-servernum python run_group.py --group group2 --job tracker'
    )

    # 4. Mảng Đổ dữ liệu vào kho (LOAD)
    task_load_to_postgres = BashOperator(
        task_id='Load_To_Postgres',
        bash_command='cd /opt/airflow/project/Data_Pipeline && python load_to_postgres.py'
    )

    # 5. Mảng Biến đổi và kiểm định dữ liệu với dbt (TRANSFORM & TEST)
    task_dbt_run = BashOperator(
        task_id='dbt_Run_Transform',
        bash_command='cd /opt/airflow/project/dbt_udemy && dbt run'
    )

    task_dbt_test = BashOperator(
        task_id='dbt_Test_Quality',
        bash_command='cd /opt/airflow/project/dbt_udemy && dbt test'
    )

    # 6. ĐỊNH NGHĨA QUY TRÌNH CHẠY (Dependencies)
    task_scrape_tracker >> task_load_to_postgres >> task_dbt_run >> task_dbt_test
