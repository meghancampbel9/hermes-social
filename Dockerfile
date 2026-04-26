# --- Stage 1: Build frontend ---
FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts
COPY frontend/ .
RUN npm run build

# --- Stage 2: Python backend ---
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Copy built SPA into /app/static
COPY --from=frontend /build/dist /app/static

RUN mkdir -p /app/data/identity

EXPOSE 8340 8341

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8340 & uvicorn app.mcp_run:app --host 0.0.0.0 --port 8341 & wait"]
