# Mucho Dinero - Trading Income Toolkit

Herramientas para generar $5,000+/mes con swing trading en acciones del S&P 500.

## Setup

```bash
pip install -r requirements.txt
```

## Uso

### Escanear el mercado por señales
```bash
python main.py scan                              # Todas las estrategias
python main.py scan --strategy mean_reversion     # Solo mean reversion
python main.py scan --tickers AAPL MSFT GOOGL     # Tickers específicos
```

### Backtesting
```bash
python main.py backtest --tickers AAPL MSFT NVDA --start 2024-01-01 --end 2025-12-31
python main.py backtest --tickers AAPL --strategy momentum --show-trades
```

### Calcular tamaño de posición
```bash
python main.py size --entry 150 --stop 143 --equity 100000
```

### Diario de trading
```bash
python main.py journal log --ticker AAPL --entry-price 150 --shares 285 --stop 143 --target 164
python main.py journal close --id 1 --exit-price 162 --exit-date 2024-03-15
python main.py journal open       # Ver posiciones abiertas
python main.py journal closed     # Ver historial
python main.py journal summary    # Estadísticas de rendimiento
```

## Estrategias

1. **Mean Reversion** - Comprar pullbacks en tendencias alcistas (RSI oversold + SMA50 + MACD)
2. **Momentum Breakout** - Capturar rupturas de máximos con volumen alto
3. **Venta de Puts** - Ingreso por primas (documentado en STRATEGY.md)

Ver [STRATEGY.md](STRATEGY.md) para la guía completa.

## Aviso Legal

Este proyecto es educativo. El trading conlleva riesgo de pérdida. No es asesoramiento financiero.
