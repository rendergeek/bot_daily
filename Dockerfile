FROM python:3.10-slim

# Define el directorio de trabajo
WORKDIR /usr/src/app

# Copia todos los archivos al contenedor
COPY . .

# Instala dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Comando de inicio apuntando al script en /usr/src/app
CMD ["python", "bot_kraken_daily.py"]