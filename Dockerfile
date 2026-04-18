# ── build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Dependências de sistema (paramiko precisa de libssl)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Dependências de runtime (libssl para paramiko)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Copiar pacotes instalados do stage de build
COPY --from=builder /install /usr/local

# Copiar código da aplicação
COPY . .

# Criar diretório de sessões (será sobreposto por volume em produção)
RUN mkdir -p /app/.sessions /app/staticfiles

ENV DJANGO_SETTINGS_MODULE=config.settings \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SESSION_FILE_PATH=/app/.sessions

# Coletar arquivos estáticos
RUN python manage.py collectstatic --noinput

EXPOSE 8008

# Gunicorn: 2 workers síncronos são suficientes para uso corporativo interno
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8008", \
     "--workers", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
