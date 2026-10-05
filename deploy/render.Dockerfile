# Cloud demo API image (DEC-43): the same backend as docker-compose, with the rulebook baked in and
# the port taken from $PORT (Render sets it). Build context: the repository root.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    TEMPLATE_DIR=/app/templates UPLOAD_DIR=/tmp/specid-uploads
WORKDIR /app
COPY backend/requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY backend/app ./app
COPY backend/alembic.ini ./
COPY templates ./templates
RUN useradd --create-home specid && chown -R specid /app
USER specid
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
