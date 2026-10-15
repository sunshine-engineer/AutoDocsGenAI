FROM python:3.12.15-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN pip install --no-cache-dir uv==0.12.3
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project \
    && .venv/bin/python -m playwright install --with-deps chromium \
    && chmod -R a+rX /opt/playwright \
    && rm -rf /var/lib/apt/lists/* /root/.cache
COPY . .
RUN useradd --uid 10001 --create-home worker
ARG RELEASE_ID=local-build
LABEL org.opencontainers.image.revision=$RELEASE_ID
USER 10001:10001
ENTRYPOINT ["python", "/app/deploy/worker_entrypoint.py"]
CMD ["python", "-m", "scripts.generation", "--help"]
