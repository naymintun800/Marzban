ARG PYTHON_VERSION=3.12

FROM ghcr.io/astral-sh/uv:python$PYTHON_VERSION-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libc6-dev \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install pnpm
RUN npm install -g pnpm

ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /build
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev
ADD . /build

# Build dashboard
WORKDIR /build/dashboard
RUN pnpm install --frozen-lockfile
RUN pnpm run build --outDir build --assetsDir statics

# Build Python app
WORKDIR /build
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


FROM python:$PYTHON_VERSION-slim-bookworm

COPY --from=builder /build /code
WORKDIR /code

ENV PATH="/code/.venv/bin:$PATH"

COPY cli_wrapper.sh /usr/bin/marzban-cli
RUN chmod +x /usr/bin/marzban-cli
RUN chmod +x /code/start.sh

ENTRYPOINT ["/code/start.sh"]