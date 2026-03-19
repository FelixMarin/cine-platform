#!/bin/bash

# Script de optimización con GPU NVIDIA
# Uso: ./optimize.sh <input> <output> [profile]

INPUT="$1"
OUTPUT="$2"
PROFILE="${3:-balanced}"  # balanced, quality, speed

# Verificar argumentos
if [ -z "$INPUT" ] || [ -z "$OUTPUT" ]; then
    echo "❌ Uso: $0 <input> <output> [profile]"
    exit 1
fi

# Verificar que el archivo existe
if [ ! -f "$INPUT" ]; then
    echo "❌ Archivo de entrada no encontrado: $INPUT"
    exit 1
fi

echo "🎬 Iniciando optimización con GPU NVIDIA"
echo "📁 Input: $INPUT"
echo "📁 Output: $OUTPUT"
echo "⚙️  Perfil: $PROFILE"

# Configuración según perfil
case $PROFILE in
    "quality")
        # Alta calidad (más lento)
        PRESET="p7"
        MULTIPASS="fullres"
        CQ="26"
        ;;
    "speed")
        # Rápido (menor calidad)
        PRESET="p4"
        MULTIPASS="disabled"
        CQ="30"
        ;;
    *)
        # Balanceado (recomendado)
        PRESET="p6"
        MULTIPASS="fullres"
        CQ="28"
        ;;
esac

# Ejecutar FFmpeg con todos los parámetros
ffmpeg -hwaccel cuda \
    -i "$INPUT" \
    -c:v h264_nvenc \
    -preset "$PRESET" \
    -rc vbr \
    -tune hq \
    -multipass "$MULTIPASS" \
    -cq "$CQ" \
    -b:v 1800k \
    -maxrate 2200k \
    -bufsize 4400k \
    -rc-lookahead 32 \
    -profile:v high \
    -level 4.1 \
    -pix_fmt yuv420p \
    -g 120 \
    -c:a aac -b:a 128k -ac 2 -ar 48000 \
    -c:s copy \
    -f matroska \
    -y "$OUTPUT"

# Verificar resultado
if [ $? -eq 0 ]; then
    echo "✅ Optimización completada: $OUTPUT"
else
    echo "❌ Error durante la optimización"
    exit 1
fi