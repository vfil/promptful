# Production image for the Promptful API (FastAPI + SQLAlchemy + Postgres).
# Written for the gist-lang-trainer hosted-deployment work — see that repo's
# docs/adr/0083-hosted-oci-backend-for-testflight.md for why this exists and
# how the image is built/pushed/run. No Dockerfile existed for this app
# before that; only api/docker-compose.yml (Postgres + Adminer for local dev).

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
RUN uv sync --frozen --no-dev

FROM python:3.11-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
