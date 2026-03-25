"""
Backtester event-driven para validar estrategias de trading.

Simula la ejecución de operaciones barra por barra con gestión
de riesgo realista y comisiones.
"""
import math
from dataclasses import dataclass
import pandas as pd
import numpy as np
import yfinance as yf

from config import BacktestConfig, AccountConfig
from scanner import add_indicators
from config import ScannerConfig


@dataclass
class Trade:
    ticker: str
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    strategy: str
    hold_days: int


class Backtester:
    def __init__(
        self,
        bt_config: BacktestConfig = None,
        account_config: AccountConfig = None,
        scanner_config: ScannerConfig = None,
    ):
        self.bt_config = bt_config or BacktestConfig()
        self.account_config = account_config or AccountConfig()
        self.scanner_config = scanner_config or ScannerConfig()

    def _fetch_data(self, ticker: str) -> pd.DataFrame:
        """Descarga datos históricos para el backtest."""
        import io, sys

        # Intentar yfinance suprimiendo todo output de error
        try:
            old_stderr = sys.stderr
            sys.stderr = io.StringIO()
            df = yf.download(
                ticker,
                start=self.bt_config.start_date,
                end=self.bt_config.end_date,
                progress=False,
            )
            sys.stderr = old_stderr
            if not df.empty and len(df) > 10:
                return add_indicators(df, self.scanner_config)
        except Exception:
            sys.stderr = old_stderr

        # Fallback: datos simulados
        from market_data import fetch_simulated_data
        data = fetch_simulated_data(
            [ticker], self.bt_config.start_date, self.bt_config.end_date
        )
        if ticker in data:
            return add_indicators(data[ticker], self.scanner_config)
        return pd.DataFrame()

    def _apply_slippage(self, price: float, is_buy: bool) -> float:
        """Aplica slippage al precio de ejecución."""
        if is_buy:
            return price * (1 + self.bt_config.slippage_pct)
        return price * (1 - self.bt_config.slippage_pct)

    def run(self, ticker: str, strategy: str = "mean_reversion") -> list[Trade]:
        """Ejecuta backtest en un ticker con la estrategia especificada."""
        df = self._fetch_data(ticker)
        if df.empty or len(df) < 60:
            return []

        trades = []
        equity = self.bt_config.initial_capital
        in_position = False
        entry_price = 0
        stop_price = 0
        target_price = 0
        shares = 0
        entry_date = ""
        entry_idx = 0
        max_hold_days = 10

        for i in range(2, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            close = float(row["Close"])
            date_str = str(df.index[i].date())

            if in_position:
                # Verificar salida
                low = float(row["Low"])
                high = float(row["High"])
                hold_days = i - entry_idx
                exit_price = None

                # Stop loss hit
                if low <= stop_price:
                    exit_price = self._apply_slippage(stop_price, False)
                # Target hit
                elif high >= target_price:
                    exit_price = self._apply_slippage(target_price, False)
                # Time stop
                elif hold_days >= max_hold_days:
                    exit_price = self._apply_slippage(close, False)
                # RSI overbought exit (mean reversion)
                elif strategy == "mean_reversion":
                    rsi = float(row["RSI"]) if pd.notna(row["RSI"]) else 50
                    if rsi > self.scanner_config.rsi_overbought:
                        exit_price = self._apply_slippage(close, False)

                if exit_price is not None:
                    pnl = (exit_price - entry_price) * shares - self.bt_config.commission * 2
                    pnl_pct = pnl / (entry_price * shares) * 100
                    equity += pnl

                    trades.append(Trade(
                        ticker=ticker,
                        entry_date=entry_date,
                        entry_price=round(entry_price, 2),
                        exit_date=date_str,
                        exit_price=round(exit_price, 2),
                        shares=shares,
                        pnl=round(pnl, 2),
                        pnl_pct=round(pnl_pct, 2),
                        strategy=strategy,
                        hold_days=hold_days,
                    ))
                    in_position = False

            else:
                # Verificar entrada
                signal = False
                rsi = float(row["RSI"]) if pd.notna(row["RSI"]) else None
                sma50 = float(row["SMA50"]) if pd.notna(row["SMA50"]) else None
                macd_hist = float(row["MACD_hist"]) if pd.notna(row["MACD_hist"]) else None
                macd_hist_prev = float(prev["MACD_hist"]) if pd.notna(prev["MACD_hist"]) else None

                if None in (rsi, sma50, macd_hist, macd_hist_prev):
                    continue

                if strategy == "mean_reversion":
                    signal = (
                        rsi < self.scanner_config.rsi_oversold
                        and close > sma50
                        and macd_hist > macd_hist_prev
                    )
                    if signal:
                        recent_low = float(df["Low"].iloc[max(0, i - 5) : i + 1].min())
                        stop_price = min(recent_low, close * 0.95)
                elif strategy == "momentum":
                    high_20 = float(row["High_20"]) if pd.notna(row["High_20"]) else None
                    avg_vol = float(row["Avg_Volume"]) if pd.notna(row["Avg_Volume"]) else 0
                    vol = float(row["Volume"])
                    if high_20 is not None and avg_vol > 0:
                        signal = close >= high_20 and (vol / avg_vol) >= self.scanner_config.volume_multiplier
                        if signal:
                            atr = float(row["ATR"]) if pd.notna(row["ATR"]) else close * 0.02
                            stop_price = max(float(row["Low"]), close - 2 * atr)
                            stop_price = max(stop_price, close * 0.95)

                if signal:
                    entry_price = self._apply_slippage(close, True)
                    risk_per_share = entry_price - stop_price
                    if risk_per_share <= 0:
                        continue

                    max_risk = equity * self.account_config.risk_per_trade
                    shares = math.floor(max_risk / risk_per_share)
                    if shares <= 0:
                        continue

                    target_price = entry_price + 2 * risk_per_share
                    entry_date = date_str
                    entry_idx = i
                    in_position = True

        return trades

    def run_portfolio(
        self, tickers: list[str], strategy: str = "mean_reversion"
    ) -> list[Trade]:
        """Ejecuta backtest en múltiples tickers."""
        all_trades = []
        for ticker in tickers:
            try:
                trades = self.run(ticker, strategy)
                all_trades.extend(trades)
            except Exception:
                continue
        return all_trades

    def generate_report(self, trades: list[Trade]) -> dict:
        """Genera un reporte de rendimiento del backtest."""
        if not trades:
            return {"total_trades": 0, "message": "Sin operaciones"}

        pnls = [t.pnl for t in trades]
        pnl_pcts = [t.pnl_pct for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        total_pnl = sum(pnls)
        win_rate = len(wins) / len(pnls) * 100

        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0
        profit_factor = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else float("inf")

        # Max drawdown
        cumulative = np.cumsum(pnls)
        peak = np.maximum.accumulate(cumulative)
        drawdown = cumulative - peak
        max_drawdown = abs(min(drawdown)) if len(drawdown) > 0 else 0

        # Retorno total
        total_return_pct = total_pnl / self.bt_config.initial_capital * 100

        # Hold time promedio
        avg_hold = np.mean([t.hold_days for t in trades])

        # Sharpe ratio estimado (simplificado)
        if np.std(pnl_pcts) > 0:
            sharpe = np.mean(pnl_pcts) / np.std(pnl_pcts) * np.sqrt(252 / max(avg_hold, 1))
        else:
            sharpe = 0

        return {
            "total_trades": len(trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "total_return_pct": round(total_return_pct, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown": round(max_drawdown, 2),
            "avg_hold_days": round(avg_hold, 1),
            "sharpe_ratio": round(sharpe, 2),
            "best_trade": round(max(pnls), 2),
            "worst_trade": round(min(pnls), 2),
        }

    def print_report(self, report: dict):
        """Imprime el reporte de backtest."""
        if report.get("total_trades", 0) == 0:
            print("\nSin operaciones en el período.")
            return

        print("\n" + "=" * 50)
        print("        REPORTE DE BACKTEST")
        print("=" * 50)
        print(f"  Total operaciones:   {report['total_trades']}")
        print(f"  Ganadoras:           {report['winning_trades']}")
        print(f"  Perdedoras:          {report['losing_trades']}")
        print(f"  Win rate:            {report['win_rate']}%")
        print(f"  P&L total:           ${report['total_pnl']:,.2f}")
        print(f"  Retorno total:       {report['total_return_pct']}%")
        print(f"  Ganancia promedio:   ${report['avg_win']:,.2f}")
        print(f"  Pérdida promedio:    ${report['avg_loss']:,.2f}")
        print(f"  Profit factor:       {report['profit_factor']}")
        print(f"  Max drawdown:        ${report['max_drawdown']:,.2f}")
        print(f"  Días promedio:       {report['avg_hold_days']}")
        print(f"  Sharpe ratio:        {report['sharpe_ratio']}")
        print(f"  Mejor operación:     ${report['best_trade']:,.2f}")
        print(f"  Peor operación:      ${report['worst_trade']:,.2f}")
        print("=" * 50)


if __name__ == "__main__":
    bt = Backtester()
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    print(f"Backtesting {len(tickers)} acciones...")

    trades = bt.run_portfolio(tickers, "mean_reversion")
    report = bt.generate_report(trades)
    bt.print_report(report)

    if trades:
        print("\n--- Últimas 10 operaciones ---")
        for t in trades[-10:]:
            emoji = "+" if t.pnl > 0 else ""
            print(f"  {t.ticker} | {t.entry_date} -> {t.exit_date} | {emoji}${t.pnl:.2f} ({emoji}{t.pnl_pct:.1f}%) | {t.hold_days}d")
