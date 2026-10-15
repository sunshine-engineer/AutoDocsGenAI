FROM python:3.12.15-slim-bookworm AS build
RUN pip install --no-cache-dir uv==0.12.3
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --only-group site --no-install-project
COPY scripts/__init__.py scripts/build_docs_site.py ./scripts/
COPY docs/generated ./docs/generated
COPY docs/ecosystem ./docs/ecosystem
COPY website ./website
COPY mkdocs.yml ./
RUN .venv/bin/python -m scripts.build_docs_site

FROM caddy:2.11.7-alpine
ARG RELEASE_ID=local-build
LABEL org.opencontainers.image.revision=$RELEASE_ID
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/.site-work/site /srv/site
