# syntax=docker/dockerfile:1.4
# ==============================================================================
# Cyrene Reactor Production Container Image
# Provides:
#   1. cyrene-reactor (Product API controller & deployment manager)
#   2. cy-exec (canonical inference runtime coordinator)
#   3. cyrene-reactor-host-placement (Rust Platform placement adapter)
# ==============================================================================

# --- Stage 1: Build Rust Host Placement Adapter ---
FROM rust:1.85-slim-bookworm AS rust-builder
WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    pkg-config \
    libssl-dev \
    git \
    protobuf-compiler \
    && rm -rf /var/lib/apt/lists/*

COPY Cyrene-Services/Cyrene-Reactor/Cargo.toml Cyrene-Services/Cyrene-Reactor/Cargo.lock /build/
COPY Cyrene-Services/Cyrene-Reactor/components /build/components

RUN cargo build --locked --release -p cyrene-reactor-host-placement

# --- Stage 2: Runtime Image (Python 3.12) ---
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/usr/local/bin:$PATH" \
    CYRENE_DATA_DIR="/data" \
    REACTOR_PORT="19300"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    openssl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy Rust host-placement binary
COPY --from=rust-builder /build/target/release/cyrene-reactor-host-placement /usr/local/bin/cyrene-reactor-host-placement

WORKDIR /app

# Pre-install third-party runtime dependencies
RUN pip install --no-cache-dir \
    "fastapi>=0.115.0" \
    "pydantic>=2.0.0,<3.0.0" \
    "pydantic-settings>=2.0.0,<3.0.0" \
    "httpx>=0.27.0" \
    "uvicorn>=0.30.0" \
    "grpcio>=1.60.0" \
    "grpcio-tools>=1.60.0" \
    "protobuf>=4.25.0" \
    "PyYAML>=6.0" \
    "packaging>=23.0" \
    "watchdog>=3.0.0"

# Copy dependency SDKs
COPY Cyrene-Platform/sdk/python/cyrene_artifacts /app/deps/cyrene_artifacts
COPY Cyrene-Services/Cyrene-Yield/sdk/python/cyrene_yield_contracts /app/deps/cyrene_yield_contracts
COPY Cyrene-Plugins-Official/sdk/python/cyrene_plugin_runtime /app/deps/cyrene_plugin_runtime

# Install local monorepo SDKs with --no-deps to prevent git clone overhead
RUN pip install --no-cache-dir --no-deps \
    /app/deps/cyrene_artifacts \
    /app/deps/cyrene_yield_contracts \
    /app/deps/cyrene_plugin_runtime

# Copy Reactor source trees
COPY Cyrene-Services/Cyrene-Reactor/runtime/core /app/reactor/runtime/core
COPY Cyrene-Services/Cyrene-Reactor/runtime/pro /app/reactor/runtime/pro
COPY Cyrene-Services/Cyrene-Reactor/product /app/reactor/product
COPY Cyrene-Services/Cyrene-Reactor/pyproject.toml Cyrene-Services/Cyrene-Reactor/README.md /app/reactor/

# Install Reactor packages with --no-deps
RUN pip install --no-cache-dir --no-deps \
    /app/reactor/runtime/core \
    /app/reactor/runtime/pro \
    /app/reactor/product

# Create data directories and non-root user
RUN mkdir -p /data/credentials /data/certs /data/config && \
    useradd -u 10001 -m -s /bin/bash cyrene && \
    chown -R cyrene:cyrene /data /app

# Copy entrypoint script
COPY Cyrene-Services/Cyrene-Reactor/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER cyrene

EXPOSE 19300 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://127.0.0.1:19300/healthz || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
