FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Ho_Chi_Minh

WORKDIR /app

# Cai thu vien he thong toi thieu: font Unicode (xuat PDF tieng Viet co dau) + OpenCV headless + libpq
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    libglib2.0-0 \
    libgl1 \
    libpq5 \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Cai dat Python dependencies rieng cho Backend Web/API (nhe, build nhanh)
COPY requirements-web.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-web.txt

# Copy ma nguon can thiet cho Backend API & Face Embedding 128D
COPY backend/ ./backend/
COPY config/ ./config/
COPY database/ ./database/
COPY face_auth/embedding_service.py ./face_auth/embedding_service.py

# Tao cac thu muc du lieu mount volume
RUN mkdir -p /app/snapshots /app/exports /app/logs

EXPOSE 5000

# Dung 1 worker + 8 threads de SSE realtime event broker chia se chung bo nho
# va phuc vu dong thoi Web Admin + Mobile App Expo + Camera AI
CMD ["gunicorn", "--workers", "1", "--threads", "8", "--timeout", "120", "--bind", "0.0.0.0:5000", "backend.app:app"]
