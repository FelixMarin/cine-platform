FROM python:3.11-slim-bullseye

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Madrid

# Instalar dependencias del sistema (versión slim ya tiene repos correctos)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

    # Instalar Docker CLI
RUN curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    rm get-docker.sh

RUN ln -sf /usr/bin/docker /usr/local/bin/docker

WORKDIR /app

# Copiar y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Limpiar pycache
RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} +

# Crear directorios para operación
RUN mkdir -p uploads temp outputs logs

# Variables de entorno por defecto
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=5000

# Healthcheck para verificar que la app responde
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${FLASK_PORT}/api/auth/check || exit 1

EXPOSE 5000

CMD ["python", "server.py"]