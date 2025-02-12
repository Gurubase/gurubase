# Common stage
# 1) Pin the python base image for all stages.
FROM python:3.11-slim AS base

# 2) Install only the shared runtime dependencies.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      git

# 3) Tweak Python to run better in Docker
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8


# Build stage.
FROM base AS build

WORKDIR /workspace

RUN python -m venv .venv
ENV PATH="/workspace/.venv/bin:$PATH"

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Run crawl4ai setup to install browsers and dependencies
RUN crawl4ai-setup

COPY . .

# Development stage.
FROM build AS dev

# 1) Install extra development tools.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        curl \
        iputils-ping \
        openssh-client \
        python3-dev \
        telnet \
        tzdata \
        unzip \
        vim \
        wget \
        zip

WORKDIR /workspace

ENV PATH="/workspace/.venv/bin:$PATH"

# 2) Install extra development dependencies.
COPY requirements-dev.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-dev.txt

CMD ["bash"]


# Runtime stage.
FROM base AS runtime

WORKDIR /workspace

# 2) Avoid running as a privileged user.
RUN addgroup --gid 1001 --system nonroot && \
    adduser --no-create-home --shell /bin/false \
      --disabled-password --uid 1001 --system --group nonroot

ENV CRAWL4_AI_BASE_DIRECTORY=/workspace/.crawl4ai \
    PLAYWRIGHT_BROWSERS_PATH=/workspace/.cache/ms-playwright

RUN mkdir -p $CRAWL4_AI_BASE_DIRECTORY $PLAYWRIGHT_BROWSERS_PATH && \
    chown -R nonroot:nonroot $CRAWL4_AI_BASE_DIRECTORY $PLAYWRIGHT_BROWSERS_PATH

USER nonroot:nonroot

ENV VIRTUAL_ENV=/workspace/.venv \
    PATH="/workspace/.venv/bin:$PATH"

# 3) Copy the self-contained app from the build stage.
COPY --from=build --chown=nonroot:nonroot /workspace ./

# 4) Run crawl4ai setup as non-root user
RUN crawl4ai-setup

CMD ["./entrypoint.sh"]
