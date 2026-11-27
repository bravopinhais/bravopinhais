FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app /app/backend/app
COPY frontend /app/frontend

RUN useradd --system --uid 10001 --create-home bravo \
    && chown -R bravo:bravo /app
USER bravo

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1

# Hosted Shadow must fail closed without explicit PostgreSQL and Google configuration.
CMD ["sh", "-c", "test \"$BRAVO_STORAGE_BACKEND\" = postgres && test -n \"$BRAVO_DATABASE_URL\" && test -n \"$GOOGLE_CLIENT_ID\" && exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
