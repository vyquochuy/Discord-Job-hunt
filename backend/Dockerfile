# Sử dụng Python 3.11 Slim làm base image nhẹ và bảo mật
FROM python:3.11-slim

# Thiết lập biến môi trường Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Cài đặt các gói hệ thống cần thiết cho việc build C extensions (nếu có) và curl kiểm tra healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Tạo thư mục làm việc
WORKDIR /app

# Copy requirements và cài đặt dependencies trước để tận dụng Docker cache layer
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy toàn bộ mã nguồn backend vào container
COPY . /app

# Mở cổng 8000
EXPOSE 8000

# Lệnh khởi động FastAPI bằng Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
