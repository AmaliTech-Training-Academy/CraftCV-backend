# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Fail fast on missing output, and keep .pyc files out of the layer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies are their own layer, so source edits do not reinstall them.
# psycopg[binary] ships its own libpq, so no compiler or libpq-dev is needed.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Run as a normal user; uid 1000 lines up with the usual host user on Linux.
RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8000

# Overridden by compose for local development.
CMD ["gunicorn", "craftcv.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
