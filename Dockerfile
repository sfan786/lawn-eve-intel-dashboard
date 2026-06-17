# ─── Stage 1: Build Vite frontend ───────────────────────────────────────────
FROM node:22-slim AS frontend-builder
WORKDIR /build

# Install deps first (cached unless package.json changes)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Copy source and build
# outDir in vite.config.js is '../static/dist' (relative to /build),
# so output lands at /static/dist
COPY frontend/ ./
RUN npm run build

# ─── Stage 2: Python application ─────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

# Install Python deps (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Overlay the Vite build output from stage 1
COPY --from=frontend-builder /static/dist ./static/dist

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Gunicorn: 2 workers, 120s timeout for slow ESI startup
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "120", "app:app"]
