"""
Diario de trading para registrar y analizar operaciones.
"""
import os
import csv
from datetime import datetime
import pandas as pd

from config import JOURNAL_FILE


COLUMNS = [
    "id", "ticker", "strategy", "entry_date", "entry_price", "shares",
    "stop_price", "target_price", "exit_date", "exit_price", "pnl",
    "pnl_pct", "hold_days", "notes", "status",
]


class TradeJournal:
    def __init__(self, filepath: str = JOURNAL_FILE):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        """Crea el archivo CSV si no existe."""
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(COLUMNS)

    def _read_all(self) -> pd.DataFrame:
        """Lee todas las operaciones."""
        try:
            df = pd.read_csv(self.filepath)
            if df.empty:
                return pd.DataFrame(columns=COLUMNS)
            return df
        except Exception:
            return pd.DataFrame(columns=COLUMNS)

    def _next_id(self) -> int:
        df = self._read_all()
        if df.empty:
            return 1
        return int(df["id"].max()) + 1

    def log_trade(
        self,
        ticker: str,
        strategy: str,
        entry_date: str,
        entry_price: float,
        shares: int,
        stop_price: float,
        target_price: float,
        notes: str = "",
    ) -> int:
        """Registra una nueva operación. Retorna el ID asignado."""
        trade_id = self._next_id()
        row = {
            "id": trade_id,
            "ticker": ticker.upper(),
            "strategy": strategy,
            "entry_date": entry_date or datetime.now().strftime("%Y-%m-%d"),
            "entry_price": entry_price,
            "shares": shares,
            "stop_price": stop_price,
            "target_price": target_price,
            "exit_date": "",
            "exit_price": "",
            "pnl": "",
            "pnl_pct": "",
            "hold_days": "",
            "notes": notes,
            "status": "OPEN",
        }
        with open(self.filepath, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writerow(row)
        print(f"Trade #{trade_id} registrado: {ticker} @ ${entry_price}")
        return trade_id

    def close_trade(
        self,
        trade_id: int,
        exit_date: str,
        exit_price: float,
        notes: str = "",
    ):
        """Cierra una operación existente."""
        df = self._read_all()
        idx = df.index[df["id"] == trade_id]
        if len(idx) == 0:
            print(f"Trade #{trade_id} no encontrado.")
            return

        i = idx[0]
        entry_price = float(df.loc[i, "entry_price"])
        shares = int(df.loc[i, "shares"])
        entry_date = str(df.loc[i, "entry_date"])

        pnl = (exit_price - entry_price) * shares
        pnl_pct = (exit_price - entry_price) / entry_price * 100

        try:
            d1 = datetime.strptime(entry_date, "%Y-%m-%d")
            d2 = datetime.strptime(exit_date, "%Y-%m-%d")
            hold_days = (d2 - d1).days
        except ValueError:
            hold_days = 0

        df.loc[i, "exit_date"] = exit_date
        df.loc[i, "exit_price"] = exit_price
        df.loc[i, "pnl"] = round(pnl, 2)
        df.loc[i, "pnl_pct"] = round(pnl_pct, 2)
        df.loc[i, "hold_days"] = hold_days
        df.loc[i, "status"] = "CLOSED"
        if notes:
            existing = str(df.loc[i, "notes"])
            df.loc[i, "notes"] = f"{existing}; {notes}" if existing else notes

        df.to_csv(self.filepath, index=False)
        result = "GANANCIA" if pnl > 0 else "PÉRDIDA"
        print(f"Trade #{trade_id} cerrado: ${pnl:+,.2f} ({pnl_pct:+.1f}%) - {result}")

    def get_open_positions(self) -> pd.DataFrame:
        """Retorna las posiciones abiertas."""
        df = self._read_all()
        return df[df["status"] == "OPEN"]

    def get_closed_trades(self) -> pd.DataFrame:
        """Retorna las operaciones cerradas."""
        df = self._read_all()
        return df[df["status"] == "CLOSED"]

    def performance_summary(self) -> dict:
        """Calcula estadísticas de rendimiento."""
        closed = self.get_closed_trades()
        if closed.empty:
            return {"total_trades": 0}

        pnls = closed["pnl"].astype(float)
        wins = pnls[pnls > 0]
        losses = pnls[pnls <= 0]

        return {
            "total_trades": len(closed),
            "open_positions": len(self.get_open_positions()),
            "total_pnl": round(pnls.sum(), 2),
            "win_rate": round(len(wins) / len(closed) * 100, 1),
            "avg_win": round(wins.mean(), 2) if len(wins) > 0 else 0,
            "avg_loss": round(losses.mean(), 2) if len(losses) > 0 else 0,
            "best_trade": round(pnls.max(), 2),
            "worst_trade": round(pnls.min(), 2),
            "avg_hold_days": round(closed["hold_days"].astype(float).mean(), 1),
        }

    def print_summary(self):
        """Imprime resumen de rendimiento."""
        stats = self.performance_summary()
        if stats["total_trades"] == 0:
            print("\nNo hay operaciones cerradas.")
            return

        print("\n=== RESUMEN DE TRADING ===")
        print(f"  Operaciones cerradas:  {stats['total_trades']}")
        print(f"  Posiciones abiertas:   {stats['open_positions']}")
        print(f"  P&L total:             ${stats['total_pnl']:,.2f}")
        print(f"  Win rate:              {stats['win_rate']}%")
        print(f"  Ganancia promedio:     ${stats['avg_win']:,.2f}")
        print(f"  Pérdida promedio:      ${stats['avg_loss']:,.2f}")
        print(f"  Mejor operación:       ${stats['best_trade']:,.2f}")
        print(f"  Peor operación:        ${stats['worst_trade']:,.2f}")
        print(f"  Días promedio:         {stats['avg_hold_days']}")
        print()
