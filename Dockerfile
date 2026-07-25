FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=8000

COPY requirements.txt requirements-saas.txt ./
RUN pip install --no-cache-dir -r requirements-saas.txt

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
