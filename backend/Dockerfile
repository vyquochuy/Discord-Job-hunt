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

# Thiết lập non-root user theo chuẩn bảo mật Hugging Face Spaces (UID 1000)
RUN useradd -m -u 1000 user

WORKDIR /app

# Copy mã nguồn backend và cấp quyền cho user 1000
COPY --chown=user:user . /app

# Khởi tạo thư mục lưu trữ PDF/Resume và phân quyền ghi
RUN mkdir -p /app/storage/resumes && chown -R user:user /app

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
