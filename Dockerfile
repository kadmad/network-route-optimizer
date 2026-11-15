# ---------------------------------------------------------------------------
# Stage 1 - build the virtualenv with uv (exact versions from uv.lock)
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.6.2 /uv /usr/local/bin/uv

# COMPILE_BYTECODE: faster start-up. LINK_MODE=copy: the uv cache mount is on another filesystem,
# so hard links are impossible. PYTHON_DOWNLOADS=never: always use the image's own Python.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app
# Manifests only, so this layer is cached until the dependencies change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group prod

# ---------------------------------------------------------------------------
# Stage 2 - runtime image: Python + venv + app code. No uv, no build tools.
# Same base image as the builder, so the copied venv's interpreter path matches.
# ---------------------------------------------------------------------------
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    WEB_CONCURRENCY=2

# Unprivileged user. The code below stays root-owned and read-only to it.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY manage.py ./
COPY config ./config
COPY common ./common
COPY apps ./apps
COPY scripts/entrypoint.sh /entrypoint.sh

# Run as the unprivileged user above, never as root.
USER 10001:10001
EXPOSE 8000

# Used by `docker compose --wait` (`make up` waits until the API is healthy).
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

ENTRYPOINT ["/entrypoint.sh"]
# Sync workers (gunicorn's default) fit short, DB-bound requests; WEB_CONCURRENCY sets their number.
# --worker-tmp-dir /dev/shm: gunicorn's recommended setting in containers, because its heartbeat
# files on the overlay filesystem can cause spurious worker timeouts.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--worker-tmp-dir", "/dev/shm"]
