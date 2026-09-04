FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash postgresql-client \
    && rm -rf /var/lib/apt/lists/*
COPY backend /app/backend
COPY scripts /app/scripts
RUN pip install --no-cache-dir /app/backend
RUN mkdir -p /app/data/archives /backups

EXPOSE 8000
CMD ["sh", "-c", "python -m alembic -c backend/alembic.ini upgrade head && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
