# Common stage
# 1) Pin the python base image for all stages.
FROM python:3.11-slim AS base

# 2) Install only the shared runtime dependencies.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      git \
      libcairo2

# 3) Tweak Python to run better in Docker
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8


# Build stage.
FROM base AS build

# 1) Install the build dependencies (they are pretty heavy).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libcairo2-dev

# 2) Install app dependencies into a virtual environment for
#    easier copying to the runtime stage.
WORKDIR /workspace

RUN python -m venv .venv
ENV PATH="/workspace/.venv/bin:$PATH"

COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

RUN playwright install --with-deps chromium

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

# 1) Avoid running as a privileged user.
RUN addgroup --gid 1001 --system nonroot && \
    adduser --no-create-home --shell /bin/false \
      --disabled-password --uid 1001 --system --group nonroot

USER nonroot:nonroot

ENV VIRTUAL_ENV=/workspace/.venv \
    PATH="/workspace/.venv/bin:$PATH"

# 2) Copy the self-contained app from the build stage.
COPY --from=build --chown=nonroot:nonroot /workspace ./

CMD ["./entrypoint.sh"]
