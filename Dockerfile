FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH
WORKDIR /srv

# Dependencies sit in their own stage, so a code change does not reinstall them.
FROM base AS deps
COPY requirements.txt .
RUN python -m venv /opt/venv && pip install --no-cache-dir -r requirements.txt

# Test tools live here and never reach the runtime image.
FROM deps AS test
COPY requirements-dev.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY app ./app
COPY tests ./tests
CMD ["pytest"]

# The image that ships: no test tools, no root user.
FROM base AS runtime
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --from=deps /opt/venv /opt/venv
COPY app ./app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"]
# One worker with threads, because Prometheus counters live in one process.
# Scale by adding pods, not gunicorn workers.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", \
     "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "--error-logfile", "-", \
     "app:create_app()"]
