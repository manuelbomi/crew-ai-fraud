# Multi-stage build: compile/install dependencies in a full image, ship a
# slim runtime image with no build toolchain, running as a non-root user.
# Base image is pinned to a specific digest-eligible tag (not `latest`) so
# builds are reproducible.

# ---- Stage 1: builder -------------------------------------------------
FROM python:3.11.9-slim-bookworm AS builder

WORKDIR /build

# Build tooling needed only to resolve/compile wheels; not shipped in the
# final image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# ---- Stage 2: runtime ---------------------------------------------------
FROM python:3.11.9-slim-bookworm AS runtime

# Create an unprivileged user/group; the app never needs root.
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /usr/sbin/nologin --create-home appuser

WORKDIR /app

COPY --from=builder /build/wheels /wheels
COPY requirements.txt ./
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY src ./src
COPY pyproject.toml ./
RUN pip install --no-cache-dir --no-deps -e .

# Drop privileges before running application code.
USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=docker

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz', timeout=3)" || exit 1

CMD ["uvicorn", "fraud_crew.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
