# Dockerfile para el bot_daily
FROM python:3.11-slim

# Crear directorio del bot
WORKDIR /usr/src/bot_daily

# Copiar archivos del proyecto
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Ejecutar bot al iniciar el contenedor
CMD ["python", "bot_daily.py"]