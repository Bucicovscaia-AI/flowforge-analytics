# Deployment

## Production build

```bash
cd frontend
npm ci
npm run build                  # type checks, then writes frontend/dist

cd ../backend
FRONTEND_DIST_DIR=../frontend/dist uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

The backend then serves the application at `/` and the API at `/api` from one origin. Run it behind an HTTPS reverse proxy, keep `DATA_DIR` on persistent storage and back it up.

## Docker

The `Dockerfile` builds the frontend and serves it from the backend. It listens on `PORT` (default `8000`).

```bash
docker build -t flowforge .
docker run -p 8000:8000 flowforge
```

## Render

`render.yaml` is a Render Blueprint that deploys this image as a free web service and redeploys on every push to `main`. To deploy your own copy, choose **New → Blueprint** in Render, select the repository and apply it, then add optional secrets such as `AI_API_KEY` or `MAKE_WEBHOOK_URL` under the service's **Environment** tab.

On Render's free plan the service sleeps after about 15 minutes without traffic and its disk is not persistent, so datasets and reports are cleared on every restart or redeploy. The Blueprint sets `STORAGE_PERSISTENT=false`, so the app tells users this, and `LOAD_SAMPLE_ON_STARTUP=true`, so the sample dataset is always available.

Configuration options are listed in [configuration.md](configuration.md).
