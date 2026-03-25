"""
Scanner de mercado para identificar oportunidades de trading.

Estrategias:
1. Mean Reversion: RSI oversold + precio sobre SMA50 + MACD girando
2. Momentum Breakout: ruptura de máximo de 20 días con volumen alto
"""
import warnings
import yfinance as yf
import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD
from ta.volatility import AverageTrueRange

from config import ScannerConfig, get_sp500_tickers

warnings.filterwarnings("ignore")


def fetch_data(tickers: list[str], period: str = "6mo") -> dict[str, pd.DataFrame]:
    """Descarga datos OHLCV para una lista de tickers."""
    result = {}
    # Procesar en lotes de 50 para evitar throttling
    batch_size = 50
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        try:
            data = yf.download(batch, period=period, group_by="ticker", progress=False)
            if len(batch) == 1:
                ticker = batch[0]
                if not data.empty:
                    result[ticker] = data.copy()
            else:
                for ticker in batch:
                    try:
                        df = data[ticker].dropna(how="all")
                        if not df.empty and len(df) > 20:
                            result[ticker] = df.copy()
                    except (KeyError, TypeError):
                        continue
        except Exception:
            continue
    return result


def add_indicators(df: pd.DataFrame, config: ScannerConfig = None) -> pd.DataFrame:
    """Añade indicadores técnicos al DataFrame de precios."""
    config = config or ScannerConfig()
    df = df.copy()

    close = df["Close"].squeeze() if isinstance(df["Close"], pd.DataFrame) else df["Close"]
    high = df["High"].squeeze() if isinstance(df["High"], pd.DataFrame) else df["High"]
    low = df["Low"].squeeze() if isinstance(df["Low"], pd.DataFrame) else df["Low"]
    volume = df["Volume"].squeeze() if isinstance(df["Volume"], pd.DataFrame) else df["Volume"]

    # RSI
    rsi = RSIIndicator(close=close, window=config.rsi_period)
    df["RSI"] = rsi.rsi()

    # SMA
    sma = SMAIndicator(close=close, window=config.sma_period)
    df["SMA50"] = sma.sma_indicator()

    # MACD
    macd = MACD(
        close=close,
        window_slow=config.macd_slow,
        window_fast=config.macd_fast,
        window_sign=config.macd_signal,
    )
    df["MACD_hist"] = macd.macd_diff()

    # ATR
    atr = AverageTrueRange(high=high, low=low, close=close, window=config.atr_period)
    df["ATR"] = atr.average_true_range()

    # Volumen promedio 20 días
    df["Avg_Volume"] = volume.rolling(window=20).mean()

    # Máximo de N días (para breakout)
    df["High_20"] = high.rolling(window=config.breakout_period).max()

    return df


def scan_mean_reversion(
    ticker: str, df: pd.DataFrame, config: ScannerConfig = None
) -> dict | None:
    """
    Señal de mean reversion:
    - RSI < 30 (oversold)
    - Precio por encima de SMA50 (tendencia alcista)
    - MACD histograma girando positivo (momentum cambiando)
    """
    config = config or ScannerConfig()
    if len(df) < 3:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = float(last["Close"])
    rsi = float(last["RSI"]) if pd.notna(last["RSI"]) else None
    sma50 = float(last["SMA50"]) if pd.notna(last["SMA50"]) else None
    macd_hist = float(last["MACD_hist"]) if pd.notna(last["MACD_hist"]) else None
    macd_hist_prev = float(prev["MACD_hist"]) if pd.notna(prev["MACD_hist"]) else None
    avg_vol = float(last["Avg_Volume"]) if pd.notna(last["Avg_Volume"]) else 0

    if None in (rsi, sma50, macd_hist, macd_hist_prev):
        return None

    # Filtro de volumen mínimo
    if avg_vol < config.min_avg_volume:
        return None

    # Condiciones de entrada
    rsi_oversold = rsi < config.rsi_oversold
    above_sma = close > sma50
    macd_turning = macd_hist > macd_hist_prev  # histograma mejorando

    if rsi_oversold and above_sma and macd_turning:
        # Stop: mínimo de las últimas 5 barras
        recent_low = float(df["Low"].iloc[-5:].min())
        stop_price = min(recent_low, close * (1 - config.max_stop_pct))

        # Target: 2:1 ratio
        risk = close - stop_price
        target_price = close + 2 * risk

        return {
            "ticker": ticker,
            "strategy": "Mean Reversion",
            "price": round(close, 2),
            "rsi": round(rsi, 1),
            "stop_price": round(stop_price, 2),
            "target_price": round(target_price, 2),
            "volume_ratio": round(float(last["Volume"]) / avg_vol, 2) if avg_vol > 0 else 0,
        }
    return None


def scan_momentum_breakout(
    ticker: str, df: pd.DataFrame, config: ScannerConfig = None
) -> dict | None:
    """
    Señal de momentum breakout:
    - Precio rompe máximo de 20 días
    - Volumen por encima de 1.5x el promedio
    """
    config = config or ScannerConfig()
    if len(df) < 3:
        return None

    last = df.iloc[-1]

    close = float(last["Close"])
    high_20 = float(last["High_20"]) if pd.notna(last["High_20"]) else None
    avg_vol = float(last["Avg_Volume"]) if pd.notna(last["Avg_Volume"]) else 0
    atr = float(last["ATR"]) if pd.notna(last["ATR"]) else None

    if high_20 is None or atr is None:
        return None

    if avg_vol < config.min_avg_volume:
        return None

    current_volume = float(last["Volume"])
    volume_ratio = current_volume / avg_vol if avg_vol > 0 else 0

    # Condiciones de entrada
    breakout = close >= high_20
    high_volume = volume_ratio >= config.volume_multiplier

    if breakout and high_volume:
        # Stop: mínimo de la barra de ruptura o 2 ATR
        stop_price = max(
            float(last["Low"]),
            close - 2 * atr,
        )
        # Limitar stop al máximo permitido
        stop_price = max(stop_price, close * (1 - config.max_stop_pct))

        risk = close - stop_price
        target_price = close + 2 * risk

        rsi = float(last["RSI"]) if pd.notna(last["RSI"]) else 0

        return {
            "ticker": ticker,
            "strategy": "Momentum Breakout",
            "price": round(close, 2),
            "rsi": round(rsi, 1),
            "stop_price": round(stop_price, 2),
            "target_price": round(target_price, 2),
            "volume_ratio": round(volume_ratio, 2),
        }
    return None


def run_scan(config: ScannerConfig = None) -> pd.DataFrame:
    """Ejecuta el scan completo y retorna señales encontradas."""
    config = config or ScannerConfig()

    # Obtener universo de tickers
    if config.universe == "custom" and config.custom_tickers:
        tickers = config.custom_tickers
    else:
        tickers = get_sp500_tickers()

    print(f"Escaneando {len(tickers)} acciones...")
    data = fetch_data(tickers)
    print(f"Datos obtenidos para {len(data)} acciones")

    signals = []
    for ticker, df in data.items():
        try:
            df_ind = add_indicators(df, config)

            # Mean Reversion
            signal = scan_mean_reversion(ticker, df_ind, config)
            if signal:
                signals.append(signal)

            # Momentum Breakout
            signal = scan_momentum_breakout(ticker, df_ind, config)
            if signal:
                signals.append(signal)
        except Exception:
            continue

    if signals:
        result = pd.DataFrame(signals)
        result = result.sort_values("volume_ratio", ascending=False)
        return result
    return pd.DataFrame()


if __name__ == "__main__":
    from tabulate import tabulate

    results = run_scan()
    if not results.empty:
        print("\n=== SEÑALES DE TRADING ===\n")
        print(tabulate(results, headers="keys", tablefmt="simple", showindex=False))
    else:
        print("\nNo se encontraron señales hoy.")
