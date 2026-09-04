# ==============================================================================
# Stage 1: Build dependencies (wheels)
# ==============================================================================
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Cài đặt công cụ build chỉ trong stage này (sẽ bị loại bỏ hoàn toàn khỏi runtime image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ==============================================================================
# Stage 2: Minimal Runtime Image
# ==============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Chỉ cài đặt runtime dependencies cần thiết:
# - libpq5: thư viện C runtime kết nối PostgreSQL (thay thế build-essential/libpq-dev nặng nề)
# - curl: phục vụ healthcheck của Docker
# - texlive-latex-base, texlive-latex-recommended, texlive-fonts-recommended:
#   Bộ LaTeX tối giản cho biên dịch CV PDF (đã loại bỏ texlive-latex-extra nặng >450MB)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/* /root/.cache

# Copy toàn bộ Python packages đã build từ Stage 1
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy mã nguồn backend
COPY . /app

# Khởi tạo thư mục lưu trữ PDF/Resume
RUN mkdir -p /app/storage/resumes

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
