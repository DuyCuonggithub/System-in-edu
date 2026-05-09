# 1. Lấy "móng nhà" là môi trường có sẵn Python và Playwright
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 2. Tạo thư mục làm việc trong container
WORKDIR /app

# 3. Copy danh sách thư viện và cài đặt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Cài đặt trình duyệt Chromium để cào web
RUN playwright install chromium

# 5. Copy toàn bộ code vào trong container
COPY . .

# 6. Lệnh để chạy (Airflow sẽ điều khiển lệnh này sau)
CMD ["python", "udemy_scraper.py", "--job", "dashboard"]