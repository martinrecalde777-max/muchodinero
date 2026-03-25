"""
Scanner de mercado para identificar oportunidades de trading.

Estrategias:
1. Mean Reversion: RSI oversold + precio sobre SMA50 + MACD girando
2. Momentum Breakout: ruptura de máximo de 20 días con volumen alto

Indicadores calculados manualmente con pandas/numpy (sin dependencia de 'ta').
"""
import warnings
import yfinance as yf
import pandas as pd
import numpy as np

from config import ScannerConfig, get_sp500_tickers

warnings.filterwarnings("ignore")


# ── Indicadores técnicos ─────────────────────────────────────────────

def calc_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()


def calc_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return histogram


def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


# ── Descarga de datos ─────────────────────────────────────────────────

def fetch_data(tickers: list[str], period: str = "6mo") -> dict[str, pd.DataFrame]:
    """Descarga datos OHLCV. Usa yfinance si disponible, sino datos simulados."""
    result = {}

    # Intentar yfinance primero
    try:
        import io, sys
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        test = yf.download(tickers[0], period="5d", progress=False)
        sys.stderr = old_stderr
        if not test.empty:
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
            if result:
                return result
    except Exception:
        sys.stderr = old_stderr

    # Fallback: datos simulados realistas
    print("  [Usando datos simulados - yfinance no disponible]")
    from market_data import fetch_simulated_data
    return fetch_simulated_data(tickers)



def add_indicators(df: pd.DataFrame, config: ScannerConfig = None) -> pd.DataFrame:
    """Añade indicadores técnicos al DataFrame de precios."""
    config = config or ScannerConfig()
    df = df.copy()

    close = df["Close"].squeeze() if isinstance(df["Close"], pd.DataFrame) else df["Close"]
    high = df["High"].squeeze() if isinstance(df["High"], pd.DataFrame) else df["High"]
    low = df["Low"].squeeze() if isinstance(df["Low"], pd.DataFrame) else df["Low"]
    volume = df["Volume"].squeeze() if isinstance(df["Volume"], pd.DataFrame) else df["Volume"]

    df["RSI"] = calc_rsi(close, config.rsi_period)
    df["SMA50"] = calc_sma(close, config.sma_period)
    df["MACD_hist"] = calc_macd(close, config.macd_fast, config.macd_slow, config.macd_signal)
    df["ATR"] = calc_atr(high, low, close, config.atr_period)
    df["Avg_Volume"] = volume.rolling(window=20).mean()
    df["High_20"] = high.rolling(window=config.breakout_period).max()

    return df


# ── Estrategias de scan ───────────────────────────────────────────────

def scan_mean_reversion(
    ticker: str, df: pd.DataFrame, config: ScannerConfig = None
) -> dict | None:
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
    if avg_vol < config.min_avg_volume:
        return None

    rsi_oversold = rsi < config.rsi_oversold
    above_sma = close > sma50
    macd_turning = macd_hist > macd_hist_prev

    if rsi_oversold and above_sma and macd_turning:
        recent_low = float(df["Low"].iloc[-5:].min())
        stop_price = min(recent_low, close * (1 - config.max_stop_pct))
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

    breakout = close >= high_20
    high_volume = volume_ratio >= config.volume_multiplier

    if breakout and high_volume:
        stop_price = max(float(last["Low"]), close - 2 * atr)
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

            signal = scan_mean_reversion(ticker, df_ind, config)
            if signal:
                signals.append(signal)

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
