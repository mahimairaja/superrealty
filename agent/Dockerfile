# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.11
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS base

ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/app/.cache/huggingface

# --- Build stage ---
FROM base AS build

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    python3-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .

# download-files builds the pool, which constructs the STT/LLM/TTS providers, and
# those validate that an API key is present at construction. The build has no
# secrets, so pass throwaway keys scoped to this RUN only (not persisted as ENV;
# the real keys come from the runtime environment at `start`).
# HF_HUB_DISABLE_XET avoids a native SIGABRT some hosts hit (Apple Silicon) when the
# HuggingFace Xet backend tears down after the turn-detector model downloads. The `|| echo`
# is a safety net: the model files are cached by the time it could abort, and livekit-agents
# re-fetches anything missing at runtime, so a nonzero exit here must not fail the build.
RUN HF_HUB_DISABLE_XET=1 DEEPGRAM_API_KEY=build OPENAI_API_KEY=build \
    uv run python main.py download-files \
    || echo "download-files exited nonzero (models cache at runtime); continuing"

# --- Production stage ---
FROM base

ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

WORKDIR /app

COPY --from=build --chown=appuser:appuser /app /app

USER appuser

EXPOSE 8081

CMD ["uv", "run", "python", "main.py", "start"]
