FROM python:3.10-slim

# Instalar dependencias del sistema (FFmpeg es requerido)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar y instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear directorios para operación
RUN mkdir -p uploads temp outputs logs

# Variables de entorno por defecto
ENV FLASK_HOST=0.0.0.0
# ENV FLASK_PORT=5000

EXPOSE 9443

CMD ["python", "server.py"]