"""
Configuración central del Trading Income Toolkit.
"""
from dataclasses import dataclass, field


@dataclass
class AccountConfig:
    starting_capital: float = 5_000.0
    leverage: int = 200                 # Apalancamiento 1:200
    buying_power: float = 1_000_000.0   # 5,000 × 200
    risk_per_trade: float = 0.01        # 1% máximo por operación ($50 con $5k)
    max_positions: int = 3              # Menos posiciones con cuenta pequeña
    max_sector_exposure: float = 0.30   # 30% máximo por sector
    weekly_max_loss: float = 0.03       # 3% pérdida máxima semanal ($150)


@dataclass
class ScannerConfig:
    universe: str = "sp500"
    custom_tickers: list = field(default_factory=list)
    min_avg_volume: int = 500_000
    rsi_period: int = 14
    rsi_oversold: float = 40.0       # RSI < 40 (más señales realistas)
    rsi_overbought: float = 60.0
    sma_period: int = 50             # SMA50 (tendencia de largo plazo)
    lookback_days: int = 120
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    breakout_period: int = 20
    volume_multiplier: float = 1.5
    atr_period: int = 14
    max_stop_pct: float = 0.05         # stop máximo 5% del precio


@dataclass
class BacktestConfig:
    start_date: str = "2023-01-01"
    end_date: str = "2025-12-31"
    initial_capital: float = 100_000.0
    commission: float = 0.0
    slippage_pct: float = 0.0005       # 5 basis points


JOURNAL_FILE = "trade_journal.csv"

# Top 50 acciones líquidas como fallback
TOP_TICKERS = [
    "AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "TSLA", "BRK-B",
    "UNH", "JNJ", "JPM", "V", "PG", "XOM", "MA", "HD", "CVX", "MRK",
    "ABBV", "LLY", "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO",
    "ACN", "TMO", "ABT", "DHR", "NEE", "LIN", "PM", "TXN", "UNP",
    "AMD", "CRM", "ORCL", "INTC", "QCOM", "AMAT", "ISRG", "BKNG",
    "ADP", "MDLZ", "GILD", "SYK", "CB", "MMC"
]


def get_sp500_tickers() -> list[str]:
    """Obtiene la lista de tickers del S&P 500 desde Wikipedia."""
    try:
        import pandas as pd
        tables = pd.read_html(
            "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        )
        tickers = tables[0]["Symbol"].str.replace(".", "-", regex=False).tolist()
        return tickers
    except Exception:
        return TOP_TICKERS
