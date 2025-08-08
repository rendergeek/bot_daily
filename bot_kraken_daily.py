#!/usr/bin/env python3
# bot_kraken_daily.py — Trading bot con RSI, EMA, MACD con envío de órdenes en EUR (paper trading)

import os
import time
import logging
from datetime import datetime

import ccxt
import pandas as pd
import requests
from dotenv import load_dotenv

# 1) Carga de .env
load_dotenv()
KRAKEN_API_KEY       = os.getenv("KRAKEN_API_KEY")
KRAKEN_API_SECRET    = os.getenv("KRAKEN_API_SECRET")
DRY_RUN              = os.getenv("DRY_RUN", "True").lower() == "true"
CAPITAL              = float(os.getenv("CAPITAL_INICIAL", "0"))  # en EUR

# 2) Parámetros de estrategia
RSI_OVERBOUGHT       = 70
RSI_OVERSOLD         = 30
MIN_VOLUME           = 1000      # volumen mínimo (en EUR de base)
TIMEFRAME            = "1h"      # “1m”, “5m”, “15m”, “30m”, “1h”, “4h”, “1d”
SLEEP_SECONDS        = 3600      # 1 hora

# 3) Logger
logger = logging.getLogger("kraken_bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 4) Instancia CCXT Kraken (para órdenes)
exchange = ccxt.kraken({
    "apiKey": KRAKEN_API_KEY,
    "secret": KRAKEN_API_SECRET,
    "enableRateLimit": True,
})


def parse_interval(tf: str) -> int:
    unit = tf[-1]
    val  = int(tf[:-1])
    if unit == "m": return val
    if unit == "h": return val * 60
    if unit == "d": return val * 1440
    raise ValueError(f"Intervalo desconocido: {tf}")


def fetch_ohlc(pair: str, timeframe: str = TIMEFRAME) -> pd.DataFrame:
    interval = parse_interval(timeframe)
    url      = "https://api.kraken.com/0/public/OHLC"
    params   = {"pair": pair.replace("/", ""), "interval": interval}
    resp     = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()

    result   = resp.json().get("result", {})
    ohlc_key = next(k for k in result.keys() if k != "last")
    raw      = result[ohlc_key]

    rows = []
    for ts, o, h, l, c, vwap, vol, count in raw:
        rows.append([ts, float(o), float(h), float(l), float(c), float(vol)])
    df = pd.DataFrame(rows, columns=["timestamp","open","high","low","close","volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

    # Indicadores
    df["ema_fast"] = df["close"].ewm(span=12).mean()
    df["ema_slow"] = df["close"].ewm(span=26).mean()
    delta = df["close"].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))
    df["macd"]   = df["ema_fast"] - df["ema_slow"]
    df["signal"] = df["macd"].ewm(span=9).mean()

    return df.dropna()


def check_ema_crossover(df: pd.DataFrame, side: str) -> bool:
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    if side == "buy":
        return (prev["ema_fast"] < prev["ema_slow"]) and (curr["ema_fast"] > curr["ema_slow"])
    else:
        return (prev["ema_fast"] > prev["ema_slow"]) and (curr["ema_fast"] < curr["ema_slow"])


def generate_signal(df: pd.DataFrame) -> str | None:
    last = df.iloc[-1]
    if last["volume"] < MIN_VOLUME:
        return None

    rsi, macd, signal = last["rsi"], last["macd"], last["signal"]

    if rsi < RSI_OVERSOLD and check_ema_crossover(df, "buy") and (macd > signal):
        return "buy"

    if rsi > RSI_OVERBOUGHT and check_ema_crossover(df, "sell") and (macd < signal):
        return "sell"

    return None


def execute_order(pair: str, side: str, price: float):
    amount = round(CAPITAL / price, 8)  # cantidad de BTC a comprar/vender
    if DRY_RUN:
        logger.info(
            "[DRY RUN] %s %f %s @ %f EUR",
            side.upper(), amount, pair, price
        )
    else:
        try:
            order = exchange.create_order(
                symbol=pair, type="market", side=side, amount=amount
            )
            logger.info("ORDER EXECUTED: %s", order)
        except Exception as e:
            logger.error("Error ejecutando orden: %s", e, exc_info=True)


def main():
    pair = "XBT/EUR"
    logger.info("Bot arrancado para %s | DRY_RUN=%s", pair, DRY_RUN)

    while True:
        logging.info("ciclo ejecutado - esperando proxima vela")
        time.sleep(SLEEP_SECONDS)
        try:
            df     = fetch_ohlc(pair)
            signal = generate_signal(df)
            price  = df.iloc[-1]["close"]
            now    = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

            if signal == "buy":
                logger.info("%s → SEÑAL COMPRA a %f EUR", now, price)
                execute_order(pair, "buy", price)

            elif signal == "sell":
                logger.info("%s → SEÑAL VENTA a %f EUR", now, price)
                execute_order(pair, "sell", price)

            else:
                logger.info("%s → ESPERAR (no hay señal)", now)

        except Exception as e:
            logger.error("Error en bucle principal: %s", e, exc_info=True)

        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()