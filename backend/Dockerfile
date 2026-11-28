FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home appuser

COPY backend/ backend/
COPY alembic.ini .

USER appuser

EXPOSE 8001

CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8001} --no-access-log"]