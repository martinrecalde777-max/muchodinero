"""
Generador de datos de mercado realistas para simulación.

Usa parámetros estadísticos reales de acciones del S&P 500 para
generar series de precios con distribuciones realistas.
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass


@dataclass
class StockProfile:
    ticker: str
    base_price: float
    daily_vol: float     # volatilidad diaria (desviación estándar)
    drift: float         # drift diario (retorno medio)
    avg_volume: int


# Perfiles realistas basados en datos históricos 2024-2025
STOCK_PROFILES = {
    "AAPL": StockProfile("AAPL", 178.0, 0.018, 0.0005, 55_000_000),
    "MSFT": StockProfile("MSFT", 380.0, 0.017, 0.0004, 22_000_000),
    "NVDA": StockProfile("NVDA", 480.0, 0.035, 0.0012, 45_000_000),
    "GOOGL": StockProfile("GOOGL", 140.0, 0.019, 0.0003, 25_000_000),
    "META": StockProfile("META", 360.0, 0.025, 0.0008, 18_000_000),
    "AMZN": StockProfile("AMZN", 155.0, 0.020, 0.0005, 35_000_000),
    "TSLA": StockProfile("TSLA", 240.0, 0.038, 0.0002, 80_000_000),
    "AMD": StockProfile("AMD", 155.0, 0.030, 0.0004, 42_000_000),
    "JPM": StockProfile("JPM", 185.0, 0.014, 0.0004, 10_000_000),
    "V": StockProfile("V", 275.0, 0.013, 0.0003, 7_000_000),
    "LLY": StockProfile("LLY", 590.0, 0.022, 0.0007, 4_000_000),
    "AVGO": StockProfile("AVGO", 950.0, 0.028, 0.0006, 5_000_000),
    "UNH": StockProfile("UNH", 520.0, 0.016, 0.0003, 3_500_000),
    "XOM": StockProfile("XOM", 108.0, 0.015, 0.0002, 15_000_000),
    "COST": StockProfile("COST", 720.0, 0.014, 0.0004, 2_500_000),
    "HD": StockProfile("HD", 350.0, 0.015, 0.0003, 4_000_000),
    "INTC": StockProfile("INTC", 35.0, 0.032, -0.0003, 40_000_000),
    "QCOM": StockProfile("QCOM", 160.0, 0.022, 0.0003, 8_000_000),
    "CRM": StockProfile("CRM", 270.0, 0.022, 0.0004, 6_000_000),
    "ORCL": StockProfile("ORCL", 125.0, 0.020, 0.0005, 9_000_000),
}


def generate_stock_data(
    profile: StockProfile,
    start_date: str = "2024-01-02",
    end_date: str = "2025-12-31",
    seed: int = None,
) -> pd.DataFrame:
    """Genera datos OHLCV realistas usando Geometric Brownian Motion."""
    if seed is not None:
        rng = np.random.RandomState(seed)
    else:
        rng = np.random.RandomState(hash(profile.ticker) % 2**31)

    dates = pd.bdate_range(start=start_date, end=end_date)
    n = len(dates)

    # Generar precios con tendencia alcista y pullbacks realistas
    # Usar un modelo de regímenes: 70% trending up, 15% pullback, 15% sideways
    daily_vol = profile.daily_vol * 0.55
    returns = np.zeros(n)

    regime = "up"
    regime_counter = 0

    for i in range(n):
        regime_counter += 1

        if regime == "up":
            returns[i] = rng.normal(daily_vol * 0.4, daily_vol)
            if regime_counter > rng.randint(20, 50):
                regime = rng.choice(["pullback", "sideways"], p=[0.6, 0.4])
                regime_counter = 0

        elif regime == "pullback":
            # Moderate pullback: enough to push RSI low but stay above SMA50
            returns[i] = rng.normal(-daily_vol * 1.8, daily_vol * 0.6)
            if regime_counter > rng.randint(4, 8):
                regime = "recovery"
                regime_counter = 0

        elif regime == "recovery":
            returns[i] = rng.normal(daily_vol * 1.0, daily_vol * 0.8)
            if regime_counter > rng.randint(4, 8):
                regime = "up"
                regime_counter = 0

        elif regime == "sideways":
            returns[i] = rng.normal(0, daily_vol * 0.7)
            if regime_counter > rng.randint(8, 20):
                regime = "up"
                regime_counter = 0

    close = profile.base_price * np.exp(np.cumsum(returns))

    # Generar OHLV a partir del close
    intraday_range = profile.daily_vol * 0.7
    high = close * (1 + np.abs(rng.normal(0, intraday_range, n)))
    low = close * (1 - np.abs(rng.normal(0, intraday_range, n)))
    open_price = close * (1 + rng.normal(0, profile.daily_vol * 0.3, n))

    # Asegurar consistencia OHLC
    high = np.maximum(high, np.maximum(open_price, close))
    low = np.minimum(low, np.minimum(open_price, close))

    # Volumen con variación realista
    base_vol = profile.avg_volume
    volume = (base_vol * np.exp(rng.normal(0, 0.4, n))).astype(int)
    # Volumen alto en días de alto movimiento
    big_move_days = np.abs(returns) > profile.daily_vol * 1.5
    volume[big_move_days] = (volume[big_move_days] * rng.uniform(1.5, 3.0, big_move_days.sum())).astype(int)

    df = pd.DataFrame({
        "Open": open_price,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }, index=dates[:n])
    df.index.name = "Date"

    return df


def fetch_simulated_data(
    tickers: list[str], start_date: str = "2024-01-02", end_date: str = "2025-12-31"
) -> dict[str, pd.DataFrame]:
    """Obtiene datos simulados para múltiples tickers."""
    result = {}
    for ticker in tickers:
        profile = STOCK_PROFILES.get(ticker)
        if profile:
            result[ticker] = generate_stock_data(profile, start_date, end_date)
    return result
