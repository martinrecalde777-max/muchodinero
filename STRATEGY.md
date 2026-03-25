# Estrategia de Trading: $5,000/mes

> **AVISO:** El trading conlleva riesgo significativo de pérdida. Rendimientos pasados no garantizan resultados futuros. Este documento es educativo y no constituye asesoramiento financiero. Opera solo con capital que puedas permitirte perder.

---

## Capital Necesario

| Retorno Mensual | Capital Requerido | Ingreso Mensual |
|:---:|:---:|:---:|
| 2% | $250,000 | $5,000 |
| 3% | $167,000 | $5,000 |
| 4% | $125,000 | $5,000 |
| 5% | $100,000 | $5,000 |

**Recomendación:** Apuntar a 3-4% mensual con $125k-$170k de capital. Retornos superiores al 5% mensual requieren asumir más riesgo y no son sostenibles a largo plazo.

**Crecimiento progresivo:** Si tienes menos capital, empieza con metas proporcionadas:
- $25k -> ~$750/mes (3%)
- $50k -> ~$1,500/mes (3%)
- Reinvierte ganancias hasta alcanzar el capital objetivo

---

## Estrategia #1: Swing Trading Mean Reversion (Principal)

**Concepto:** Comprar acciones en tendencia alcista que han tenido un retroceso temporal.

### Condiciones de Entrada
1. **RSI(14) < 30** - La acción está sobrevendida
2. **Precio > SMA(50)** - La tendencia general sigue alcista
3. **MACD histograma girando positivo** - El momentum está cambiando

### Condiciones de Salida
- **Take profit:** RSI cruza por encima de 55, o se alcanza target de 2:1 R/R
- **Stop loss:** Por debajo del mínimo reciente (últimas 5 barras), máximo 5%
- **Time stop:** Si no se ha movido en 10 días hábiles, cerrar

### Universo
- Acciones del S&P 500
- Volumen promedio diario > 500,000 acciones
- Evitar acciones con earnings en los próximos 5 días

### Expectativa
- Win rate esperado: 55-65%
- Ratio R/R promedio: 2:1
- 4-8 operaciones por mes

---

## Estrategia #2: Momentum Breakout (Secundaria)

**Concepto:** Capturar movimientos explosivos cuando una acción rompe un nivel de resistencia.

### Condiciones de Entrada
1. **Precio rompe máximo de 20 días**
2. **Volumen > 1.5x el promedio de 20 días**

### Condiciones de Salida
- **Trailing stop:** 2x ATR(14) por debajo del precio
- **Stop loss:** Por debajo del mínimo de la barra de ruptura, máximo 5%
- **Time stop:** 10 días hábiles

### Expectativa
- Win rate esperado: 40-50%
- Ratio R/R promedio: 3:1
- 2-4 operaciones por mes

---

## Estrategia #3: Venta de Puts (Ingreso Adicional)

**Concepto:** Vender puts cash-secured en acciones que quieres poseer, cobrando prima.

### Reglas
- Solo en acciones fundamentalmente sólidas que quieras comprar
- Strike 5-10% por debajo del precio actual
- 30-45 DTE (días hasta expiración)
- Si te asignan, aplica la estrategia #1 para gestionar la posición

### Expectativa
- Ingreso mensual: 1-2% del capital asignado
- Win rate: 80%+
- Complementa las estrategias direccionales

---

## Gestión de Riesgo (NO NEGOCIABLE)

### Regla del 2%
**Nunca arriesgar más del 2% del capital en una sola operación.**

```
Posición = (Capital × 0.02) / (Precio_entrada - Stop_loss)

Ejemplo: Capital $100,000, Entry $150, Stop $143
Riesgo por acción = $7
Máximo riesgo = $100,000 × 0.02 = $2,000
Acciones = $2,000 / $7 = 285 acciones
Valor posición = 285 × $150 = $42,750 (42.7% del capital)
```

### Reglas Adicionales
- **Máximo 6 posiciones simultáneas** - Suficiente diversificación sin diluir
- **Máximo 20% en un sector** - Evitar concentración sectorial
- **Pérdida semanal máxima: 5%** - Si llegas al 5%, para de operar esa semana
- **No operar en los primeros 15 minutos** del mercado (alta volatilidad, spreads amplios)

### Kelly Criterion (Dimensionamiento Óptimo)
Después de tener historial de al menos 30 operaciones, usa half-Kelly:
```
Kelly% = (Win_rate × Avg_win/Avg_loss - (1 - Win_rate)) / (Avg_win/Avg_loss)
Usar: Half_Kelly = Kelly% / 2
```

---

## Rutina Diaria

### Pre-Market (8:00-9:30 AM ET)
1. Revisar calendario económico y de earnings
2. Ejecutar scanner: `python main.py scan`
3. Revisar posiciones abiertas: `python main.py journal open`
4. Identificar 2-3 setups potenciales
5. Definir precio de entrada, stop y target ANTES de que abra el mercado

### Durante el Mercado (9:45 AM - 4:00 PM ET)
1. Ejecutar órdenes planificadas (no improvisar)
2. Monitorear stops de posiciones abiertas
3. Registrar operaciones: `python main.py journal log --ticker ...`

### Post-Market (4:00-5:00 PM ET)
1. Actualizar diario con resultados
2. Revisar ejecución vs plan
3. Anotar lecciones aprendidas

### Fin de Semana
1. Revisar rendimiento semanal: `python main.py journal summary`
2. Ejecutar backtests de ideas nuevas
3. Estudiar gráficos y preparar watchlist para la semana
4. Ajustar parámetros si es necesario

---

## Métricas a Monitorear

| Métrica | Objetivo Mínimo |
|:---|:---:|
| Win Rate | > 50% |
| Profit Factor | > 1.5 |
| Ratio R/R promedio | > 2:1 |
| Max Drawdown | < 10% |
| Sharpe Ratio | > 1.5 |
| Operaciones/mes | 6-12 |

---

## Plan de Escalado

### Fase 1: Aprendizaje (Meses 1-3)
- Operar en paper trading (simulación)
- Ejecutar backtests exhaustivos
- Meta: consistencia, no ganancias

### Fase 2: Capital Pequeño (Meses 4-6)
- Operar con 25% del capital destinado
- Validar la estrategia con dinero real
- Meta: $500-$1,000/mes

### Fase 3: Capital Completo (Mes 7+)
- Escalar gradualmente al capital completo
- Meta: $5,000/mes
- Seguir reinvirtiendo para crecer el capital

---

## Errores Comunes a Evitar

1. **Overtrading** - No forzar operaciones. Si no hay setup, no operes.
2. **Mover stops** - NUNCA mover un stop loss más lejos. Es la regla #1.
3. **Revenge trading** - Después de una pérdida, no tomes operaciones impulsivas.
4. **Ignorar el plan** - Si no cumple TODOS los criterios, no entres.
5. **Tamaño excesivo** - El 2% de riesgo por trade es el MÁXIMO, no el mínimo.
6. **Trading emocional** - Si estás frustrado, enojado o eufórico, cierra la pantalla.
