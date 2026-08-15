FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=8000

# MA12 — the production image installs the hash-pinned lock, not the `>=` ranges. The lock is
# resolved for linux/CPython 3.11, which is exactly this base image. `--require-hashes` makes
# pip refuse anything that is not byte-for-byte the artifact the lock was resolved against, so
# a yanked-and-replaced release or a compromised mirror fails the build instead of shipping.
# requirements*.txt are copied too: they stay the readable declaration and the local path.
COPY requirements.txt requirements-saas.txt requirements-saas.lock.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements-saas.lock.txt

COPY . .
RUN mkdir -p data

EXPOSE 8000
# Scans belong in the worker (see Procfile), so a long web timeout is just a safety net.
# Shell form so $PORT (Render provides it) and $WEB_CONCURRENCY expand. Default to a
# memory-light 2 workers + threads so it fits Render's 512 MB free/Starter box
# (4 workers each load pandas/numpy and OOM there). Set WEB_CONCURRENCY=1 if it still OOMs.
CMD gunicorn valuation.saas.app_saas:app \
    --workers ${WEB_CONCURRENCY:-2} --threads 4 \
    --timeout 180 --bind 0.0.0.0:${PORT:-8000}
