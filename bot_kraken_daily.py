#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
from datetime import datetime

import ccxt
import pandas as pd
import ta


# -----------------------------------------------------------
# Configuración de logging
# -----------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------
# Carga y validación de variables de entorno
# -----------------------------------------------------------
# Symbol to trade, e.g. "XBT/USD"
PAIR = os.getenv("PAIR")
if not PAIR:
    logger.error("Missing environment variable: PAIR")
    sys.exit(1)

# Dry-run mode
dry_run_env = os.getenv("DRY_RUN", "False")
if dry_run_env.lower() in ("1", "true", "yes"):
    DRY_RUN = True
elif dry_run_env.lower() in ("0", "false", "no"):
    DRY_RUN = False
else:
    logger.error(f"Invalid DRY_RUN value: {dry_run_env}. Use True or False.")
    sys.exit(1)
logger.info(f"Dry run mode: {DRY_RUN}")

# Initial capital
capital_env = os.getenv("CAPITAL_INICIAL")
if capital_env is None:
    logger.error("Missing environment variable: CAPITAL_INICIAL")
    sys.exit(1)

try:
    CAPITAL = float(capital_env)
except ValueError:
    logger.error(f"Invalid CAPITAL_INICIAL value: '{capital_env}' is not a float.")
    sys.exit(1)
logger.info(f"Starting capital: {CAPITAL}")

# Log file for operations
LOG_FILE = os.getenv("LOG_FILE", "logs/trades.log")
logger.info(f"Log file: {LOG_FILE}")


def main():
    logger.info(f"Fetching OHLCV for {PAIR}")
    exchange = ccxt.kraken()
    try:
        ohlcv = exchange.fetch_ohlcv(PAIR, timeframe="1d", limit=100)
    except Exception as e:
        logger.error(f"Failed to fetch OHLCV: {e}")
        sys.exit(1)

    df = pd.DataFrame(ohlcv, columns=[
        "timestamp", "open", "high", "low", "close", "volume"
    ])
    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")

    # === Cálculo de indicadores ===
    logger.info("Calculating RSI, MACD, EMA(9), EMA(21)")
    df["rsi"] = ta.momentum.RSIIndicator(df["close"]).rsi()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["ema_fast"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
    df["ema_slow"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()

    ultima = df.iloc[-1]

    # === Dashboard básico ===
    logger.info("🔎 Señales del día:")
    logger.info(f"Fecha     : {ultima['datetime']}")
    logger.info(f"Cierre    : {ultima['close']}")
    logger.info(f"RSI       : {ultima['rsi']:.2f}")
    logger.info(f"MACD      : {ultima['macd']:.2f}")
    logger.info(f"Signal    : {ultima['macd_signal']:.2f}")
    logger.info(f"EMA 9/21  : {ultima['ema_fast']:.2f}/{ultima['ema_slow']:.2f}")
    logger.info(f"Volumen   : {int(ultima['volume'])}")

    # === Lógica de señal ===
    if (
        ultima["rsi"] > 70
        and ultima["macd"] < ultima["macd_signal"]
        and ultima["ema_fast"] < ultima["ema_slow"]
    ):
        accion = "VENDER"
    elif (
        ultima["rsi"] < 30
        and ultima["macd"] > ultima["macd_signal"]
        and ultima["ema_fast"] > ultima["ema_slow"]
    ):
        accion = "COMPRAR"
    else:
        accion = "ESPERAR"

    logger.info(f"✅ Acción recomendada: {accion}")

    # === Logging de la operación (solo dry-run) ===
    if DRY_RUN:
        operacion = {
            "fecha"     : str(ultima["datetime"]),
            "pair"      : PAIR,
            "accion"    : accion,
            "precio"    : ultima["close"],
            "rsi"       : float(ultima["rsi"]),
            "macd"      : float(ultima["macd"]),
            "macd_signal": float(ultima["macd_signal"]),
            "ema_fast"  : float(ultima["ema_fast"]),
            "ema_slow"  : float(ultima["ema_slow"]),
            "volumen"   : float(ultima["volume"]),
            "capital"   : CAPITAL
        }

        # Asegurarse de que exista el directorio
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

        try:
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(operacion) + "\n")
            logger.info(f"Operation logged to {LOG_FILE}")
        except Exception as e:
            logger.error(f"Failed to write log: {e}")


if __name__ == "__main__":
    main()