# Udemy Price Scraping & Analytics Pipeline 📈

Dự án này là một hệ thống tự động hóa luồng dữ liệu (End-to-End Data Pipeline) nhằm theo dõi biến động giá các khóa học trên Udemy. Hệ thống thu thập dữ liệu bằng Scraper, quản lý luồng bằng Airflow, biến đổi dữ liệu bằng dbt và hiển thị trực quan hóa.

## 🏗 Kiến trúc hệ thống (Architecture)
Dự án được xây dựng dựa trên kiến trúc Modern Data Stack:
1. **Source**: Thu thập dữ liệu từ Udemy bằng Selenium/Playwright (Scraper).
2. **Orchestration**: Sử dụng **Apache Airflow** để lập lịch và điều phối các tác vụ.
3. **Storage**: Lưu trữ dữ liệu thô (Raw Data) và dữ liệu sau xử lý vào **PostgreSQL**.
4. **Transformation**: Sử dụng **dbt (data build tool)** để thực hiện các mô hình hóa dữ liệu (Data Modeling) theo cấu trúc Staging và Marts.
5. **Visualization**: Hiển thị báo cáo thông qua ứng dụng Web (Streamlit/Flask/Django).

## 🛠 Công nghệ sử dụng
* **Ngôn ngữ:** Python
* **Data Pipeline:** Apache Airflow
* **Biến đổi dữ liệu:** dbt (Postgres adapter)
* **Cơ sở dữ liệu:** PostgreSQL
* **Containerization:** Docker & Docker Compose
* **Scraping:** Selenium / Cloudscraper

## 📂 Cấu trúc dự án
```text
├── Data_Pipeline/          # Các file cấu hình Airflow DAGs và scripts ETL
├── Scraper/                # Source code cào dữ liệu từ Udemy
├── dbt_udemy/              # Các model dbt (staging, marts)
├── database/               # Scripts khởi tạo DB và cấu hình schema
├── Web/                    # Giao diện người dùng hiển thị báo cáo
└── docker-compose.yml      # File cấu hình triển khai toàn bộ hệ thống
