# Backend Dockerfile — FastAPI + data_science pipeline
FROM python:3.12-slim

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Önce requirements (cache için)
COPY requirements.txt data_science/requirements-ds.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir -r requirements-ds.txt

# Uygulama kodu
COPY . .

EXPOSE 8000

# Railway dinamik PORT kullanır; yoksa 8000 default
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
