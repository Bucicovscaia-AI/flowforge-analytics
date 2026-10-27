# One container that serves both the API and the built React app,
# suitable for a single web service (for example on Render).

FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend/app backend/app
COPY sample-data sample-data
COPY --from=frontend /app/frontend/dist frontend/dist
RUN useradd --create-home flowforge && mkdir -p backend/data && chown flowforge backend/data
USER flowforge
WORKDIR /app/backend
EXPOSE 8000
# Hosting platforms set PORT; 8000 is the local default.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
