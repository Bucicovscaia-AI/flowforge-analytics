# Single-service image: the FastAPI backend serves the built React frontend and the API
# from one origin. Used by Render (render.yaml) and works on any Docker host.

# 1. Build the frontend
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# 2. Run the backend
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FRONTEND_DIST_DIR=/app/frontend/dist \
    DATA_DIR=/app/backend/data \
    PORT=8000

# Run as an unprivileged user (uid 1000 also matches what Hugging Face Spaces expects).
RUN useradd --create-home --uid 1000 app
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt
COPY backend/app ./app
COPY sample-data /app/sample-data
COPY --from=frontend /app/frontend/dist /app/frontend/dist
RUN mkdir -p /app/backend/data && chown -R app:app /app/backend/data
USER app

EXPOSE 8000
# Hosts such as Render set PORT; default to 8000 elsewhere.
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
