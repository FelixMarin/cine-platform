FROM python:3.11-slim-bullseye

# Instalar dependencias del sistema (versión slim ya tiene repos correctos)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install debugpy

# Copiar el código de la aplicación
COPY . .

RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
    
# Crear directorios para operación
RUN mkdir -p uploads temp outputs logs

# Variables de entorno por defecto
ENV FLASK_HOST=0.0.0.0
# ENV FLASK_PORT=5000

EXPOSE 9443

CMD ["python", "server.py"]