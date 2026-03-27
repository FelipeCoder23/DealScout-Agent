# ============================================================
# DealScout Agent - Dockerfile
# Imagen multi-stage con Python 3.12 + Playwright/Chromium
# Base: python:3.12-bookworm (Ubuntu, compatible con Playwright)
# ============================================================

# --- Stage 1: Builder (instala dependencias) ---
FROM python:3.12-bookworm AS builder

WORKDIR /app

# Instalar uv para gestion de dependencias
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copiar archivos de dependencias
COPY pyproject.toml ./
COPY uv.lock* ./

# Instalar dependencias en directorio aislado
RUN uv sync --frozen --no-dev --no-install-project 2>/dev/null || \
    uv sync --no-dev --no-install-project

# --- Stage 2: Runtime (imagen final) ---
FROM python:3.12-bookworm AS runtime

# Instalar dependencias del sistema necesarias para Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencias de Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    # Fuentes para renderizar paginas en español
    fonts-liberation \
    fonts-noto \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copiar entorno virtual desde builder
COPY --from=builder /app/.venv /app/.venv

# Instalar Playwright y descargar solo Chromium (mas liviano)
ENV PATH="/app/.venv/bin:$PATH"
RUN playwright install chromium

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 -s /bin/bash dealscout

# Copiar codigo fuente
WORKDIR /app
COPY src/ ./src/
COPY cli.py ./

# Crear directorio para output
RUN mkdir -p /app/output && chown dealscout:dealscout /app/output

# Variables de entorno (sin valores — se pasan en runtime via .env o -e)
ENV PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    DEALSCOUT_MODEL="anthropic:claude-sonnet-4-6"

# Cambiar a usuario no-root
USER dealscout

# Healthcheck: verificar que el CLI responde
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=2 \
    CMD python cli.py --help > /dev/null 2>&1 || exit 1

# Entry point: el CLI
ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]
