FROM ghcr.io/astral-sh/uv:0.12.19 AS uv
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg tesseract-ocr tesseract-ocr-eng libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/reel_to_md ./src/reel_to_md
RUN uv sync --locked --no-dev --extra asr --no-editable \
    && useradd --uid 10001 --create-home runner \
    && mkdir /input /models /config /outputs \
    && chown runner:runner /outputs
COPY docs/examples/example.json /app/example.json
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HOME=/tmp/huggingface PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER runner
ENTRYPOINT ["/app/.venv/bin/reel-to-md"]
CMD ["--help"]
