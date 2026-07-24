FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PORT=8000

COPY requirements.txt requirements-saas.txt ./
RUN pip install --no-cache-dir -r requirements-saas.txt

COPY . .
RUN mkdir -p data

EXPOSE 8000
# Scans belong in the worker (see Procfile), so a long web timeout is just a safety net.
CMD ["gunicorn", "valuation.saas.app_saas:app", "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "180"]
