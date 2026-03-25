#!/usr/bin/env python3
"""
Trading Income Toolkit - CLI principal.

Uso:
    python main.py scan [--strategy mean_reversion|momentum|all] [--tickers AAPL MSFT ...]
    python main.py backtest --tickers AAPL MSFT [--strategy mean_reversion|momentum] [--start 2023-01-01] [--end 2025-12-31]
    python main.py size --entry 150 --stop 143 --equity 100000
    python main.py journal log --ticker AAPL --entry-price 150 --shares 100 --stop 143 --target 164
    python main.py journal close --id 1 --exit-price 162 --exit-date 2024-03-15
    python main.py journal open
    python main.py journal summary
"""
import argparse
import sys
from datetime import datetime

from config import AccountConfig, ScannerConfig, BacktestConfig
from scanner import run_scan
from backtester import Backtester
from risk_manager import RiskManager
from journal import TradeJournal


def cmd_scan(args):
    """Ejecutar scanner de mercado."""
    config = ScannerConfig()
    if args.tickers:
        config.universe = "custom"
        config.custom_tickers = args.tickers

    results = run_scan(config)

    if results.empty:
        print("\nNo se encontraron señales hoy.")
        return

    # Filtrar por estrategia si se especifica
    if args.strategy != "all":
        strategy_map = {
            "mean_reversion": "Mean Reversion",
            "momentum": "Momentum Breakout",
        }
        strategy_name = strategy_map.get(args.strategy, args.strategy)
        results = results[results["strategy"] == strategy_name]

    if results.empty:
        print(f"\nNo se encontraron señales para '{args.strategy}'.")
        return

    from tabulate import tabulate
    print(f"\n=== SEÑALES DE TRADING ({datetime.now().strftime('%Y-%m-%d')}) ===\n")
    print(tabulate(results, headers="keys", tablefmt="simple", showindex=False, floatfmt=".2f"))
    print(f"\nTotal: {len(results)} señales encontradas")


def cmd_backtest(args):
    """Ejecutar backtest."""
    bt_config = BacktestConfig(
        start_date=args.start,
        end_date=args.end,
    )
    bt = Backtester(bt_config=bt_config)

    print(f"Backtesting {len(args.tickers)} acciones ({args.strategy})...")
    print(f"Período: {args.start} a {args.end}")

    trades = bt.run_portfolio(args.tickers, args.strategy)
    report = bt.generate_report(trades)
    bt.print_report(report)

    if trades and args.show_trades:
        print("\n--- Operaciones ---")
        for t in trades:
            sign = "+" if t.pnl > 0 else ""
            print(f"  {t.ticker} | {t.entry_date} -> {t.exit_date} | "
                  f"{sign}${t.pnl:.2f} ({sign}{t.pnl_pct:.1f}%) | {t.hold_days}d")


def cmd_size(args):
    """Calcular tamaño de posición."""
    rm = RiskManager(AccountConfig())
    rm.print_position_size(args.entry, args.stop, args.equity)

    result = rm.validate_trade(args.entry, args.stop, args.equity)
    if not result["approved"]:
        print("ADVERTENCIAS:")
        for reason in result["reasons"]:
            print(f"  - {reason}")


def cmd_journal(args):
    """Gestionar diario de trading."""
    journal = TradeJournal()

    if args.action == "log":
        journal.log_trade(
            ticker=args.ticker,
            strategy=args.strategy or "manual",
            entry_date=args.entry_date or datetime.now().strftime("%Y-%m-%d"),
            entry_price=args.entry_price,
            shares=args.shares,
            stop_price=args.stop,
            target_price=args.target,
            notes=args.notes or "",
        )

    elif args.action == "close":
        journal.close_trade(
            trade_id=args.id,
            exit_date=args.exit_date or datetime.now().strftime("%Y-%m-%d"),
            exit_price=args.exit_price,
            notes=args.notes or "",
        )

    elif args.action == "open":
        positions = journal.get_open_positions()
        if positions.empty:
            print("\nNo hay posiciones abiertas.")
        else:
            from tabulate import tabulate
            cols = ["id", "ticker", "strategy", "entry_date", "entry_price",
                    "shares", "stop_price", "target_price"]
            print("\n=== POSICIONES ABIERTAS ===\n")
            print(tabulate(positions[cols], headers="keys", tablefmt="simple", showindex=False))

    elif args.action == "closed":
        closed = journal.get_closed_trades()
        if closed.empty:
            print("\nNo hay operaciones cerradas.")
        else:
            from tabulate import tabulate
            cols = ["id", "ticker", "entry_date", "exit_date", "pnl", "pnl_pct", "hold_days"]
            print("\n=== OPERACIONES CERRADAS ===\n")
            print(tabulate(closed[cols], headers="keys", tablefmt="simple", showindex=False))

    elif args.action == "summary":
        journal.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description="Trading Income Toolkit - Herramientas para generar $5,000+/mes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # === SCAN ===
    scan_p = subparsers.add_parser("scan", help="Escanear mercado por señales")
    scan_p.add_argument("--strategy", choices=["mean_reversion", "momentum", "all"],
                        default="all", help="Estrategia a buscar")
    scan_p.add_argument("--tickers", nargs="+", help="Lista de tickers específicos")

    # === BACKTEST ===
    bt_p = subparsers.add_parser("backtest", help="Backtesting de estrategias")
    bt_p.add_argument("--tickers", nargs="+", required=True, help="Tickers a testear")
    bt_p.add_argument("--strategy", choices=["mean_reversion", "momentum"],
                       default="mean_reversion")
    bt_p.add_argument("--start", default="2023-01-01", help="Fecha inicio (YYYY-MM-DD)")
    bt_p.add_argument("--end", default="2025-12-31", help="Fecha fin (YYYY-MM-DD)")
    bt_p.add_argument("--show-trades", action="store_true", help="Mostrar operaciones")

    # === SIZE ===
    size_p = subparsers.add_parser("size", help="Calcular tamaño de posición")
    size_p.add_argument("--entry", type=float, required=True, help="Precio de entrada")
    size_p.add_argument("--stop", type=float, required=True, help="Precio de stop loss")
    size_p.add_argument("--equity", type=float, required=True, help="Capital disponible")

    # === JOURNAL ===
    j_p = subparsers.add_parser("journal", help="Diario de trading")
    j_p.add_argument("action", choices=["log", "close", "open", "closed", "summary"])
    j_p.add_argument("--ticker", help="Símbolo de la acción")
    j_p.add_argument("--strategy", help="Estrategia utilizada")
    j_p.add_argument("--entry-date", help="Fecha de entrada (YYYY-MM-DD)")
    j_p.add_argument("--entry-price", type=float, help="Precio de entrada")
    j_p.add_argument("--shares", type=int, help="Número de acciones")
    j_p.add_argument("--stop", type=float, help="Precio de stop loss")
    j_p.add_argument("--target", type=float, help="Precio objetivo")
    j_p.add_argument("--id", type=int, help="ID del trade a cerrar")
    j_p.add_argument("--exit-date", help="Fecha de salida (YYYY-MM-DD)")
    j_p.add_argument("--exit-price", type=float, help="Precio de salida")
    j_p.add_argument("--notes", help="Notas adicionales")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "scan": cmd_scan,
        "backtest": cmd_backtest,
        "size": cmd_size,
        "journal": cmd_journal,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
