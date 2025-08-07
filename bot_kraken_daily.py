import ccxt, pandas as pd, ta, os, json
from datetime import datetime

# === Cargar entorno ===
PAIR = os.getenv("PAIR")
DRY_RUN = os.getenv("DRY_RUN") == "True"
CAPITAL = float(os.getenv("CAPITAL_INICIAL"))
LOG_FILE = os.getenv("LOG_FILE")

# === Inicializar exchange ===
exchange = ccxt.kraken()
ohlcv = exchange.fetch_ohlcv(PAIR, timeframe='1d', limit=100)
df = pd.DataFrame(ohlcv, columns=['timestamp','open','high','low','close','volume'])
df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

# === Calcular indicadores ===
df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
macd = ta.trend.MACD(df['close'])
df['macd'] = macd.macd()
df['macd_signal'] = macd.macd_signal()
ema_fast = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
ema_slow = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()
df['ema_fast'] = ema_fast
df['ema_slow'] = ema_slow

# === Señales ===
ultima = df.iloc[-1]

# Dashboard básico
print("🔎 Señales del día:")
print(f"Fecha: {ultima['datetime']}")
print(f"Cierre: {ultima['close']}")
print(f"RSI: {ultima['rsi']:.2f}")
print(f"MACD: {ultima['macd']:.2f}, Signal: {ultima['macd_signal']:.2f}")
print(f"EMA 9/21: {ultima['ema_fast']:.2f}/{ultima['ema_slow']:.2f}")
print(f"Volumen: {ultima['volume']:.0f}")

# Lógica de venta
if ultima['rsi'] > 70 and ultima['macd'] < ultima['macd_signal'] and ultima['ema_fast'] < ultima['ema_slow']:
    accion = "VENDER"
# Lógica de recompra
elif ultima['rsi'] < 30 and ultima['macd'] > ultima['macd_signal'] and ultima['ema_fast'] > ultima['ema_slow']:
    accion = "COMPRAR"
else:
    accion = "ESPERAR"

print(f"✅ Acción recomendada: {accion}")

# === Logging ===
if DRY_RUN:
    operacion = {
        "fecha": str(ultima['datetime']),
        "accion": accion,
        "precio": ultima['close'],
        "rsi": ultima['rsi'],
        "macd": ultima['macd'],
        "ema_fast": ultima['ema_fast'],
        "ema_slow": ultima['ema_slow'],
        "volumen": ultima['volume']
    }
    os.makedirs("logs", exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(operacion) + "\n")