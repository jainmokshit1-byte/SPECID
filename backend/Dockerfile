FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 SENTENCE_TRANSFORMERS_HOME=/models
WORKDIR /app
COPY requirements.lock requirements-ml.lock ./
RUN pip install --no-cache-dir -r requirements.lock \
 && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-ml.lock
COPY app ./app
COPY alembic.ini ./
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
