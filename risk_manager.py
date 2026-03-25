"""
Gestión de riesgo y dimensionamiento de posiciones.

Reglas fundamentales:
- Nunca arriesgar más del 2% del capital por operación
- Máximo 6 posiciones simultáneas
- Máximo 20% del capital en un sector
- Pérdida máxima semanal: 5%
"""
import math
from config import AccountConfig


class RiskManager:
    def __init__(self, config: AccountConfig = None):
        self.config = config or AccountConfig()

    def calculate_position_size(
        self, entry_price: float, stop_price: float, account_equity: float
    ) -> dict:
        """Calcula el tamaño de posición basado en riesgo por acción."""
        if entry_price <= 0 or stop_price <= 0 or account_equity <= 0:
            return {"shares": 0, "dollar_risk": 0, "position_value": 0, "pct_of_account": 0}

        risk_per_share = abs(entry_price - stop_price)
        if risk_per_share == 0:
            return {"shares": 0, "dollar_risk": 0, "position_value": 0, "pct_of_account": 0}

        max_dollar_risk = account_equity * self.config.risk_per_trade
        shares = math.floor(max_dollar_risk / risk_per_share)

        if shares == 0:
            return {"shares": 0, "dollar_risk": 0, "position_value": 0, "pct_of_account": 0}

        position_value = shares * entry_price
        dollar_risk = shares * risk_per_share

        return {
            "shares": shares,
            "dollar_risk": round(dollar_risk, 2),
            "position_value": round(position_value, 2),
            "pct_of_account": round(position_value / account_equity * 100, 2),
        }

    def validate_trade(
        self,
        entry_price: float,
        stop_price: float,
        account_equity: float,
        current_positions: list[dict] = None,
        weekly_pnl: float = 0.0,
    ) -> dict:
        """Valida una operación contra todas las reglas de riesgo."""
        reasons = []
        current_positions = current_positions or []

        # Regla 1: Stop loss no debe ser mayor al máximo permitido
        stop_pct = abs(entry_price - stop_price) / entry_price
        if stop_pct > 0.05:
            reasons.append(f"Stop loss demasiado amplio: {stop_pct:.1%} (máx 5%)")

        # Regla 2: Número de posiciones abiertas
        if len(current_positions) >= self.config.max_positions:
            reasons.append(
                f"Máximo de posiciones alcanzado: {len(current_positions)}/{self.config.max_positions}"
            )

        # Regla 3: Pérdida semanal
        weekly_loss_pct = abs(weekly_pnl) / account_equity if weekly_pnl < 0 else 0
        if weekly_loss_pct >= self.config.weekly_max_loss:
            reasons.append(
                f"Límite de pérdida semanal alcanzado: {weekly_loss_pct:.1%} (máx {self.config.weekly_max_loss:.0%})"
            )

        position_size = self.calculate_position_size(entry_price, stop_price, account_equity)

        return {
            "approved": len(reasons) == 0,
            "reasons": reasons,
            "position_size": position_size,
        }

    def calculate_reward_risk_ratio(
        self, entry: float, stop: float, target: float
    ) -> float:
        """Calcula la relación recompensa/riesgo."""
        risk = abs(entry - stop)
        reward = abs(target - entry)
        if risk == 0:
            return 0.0
        return round(reward / risk, 2)

    def kelly_criterion(
        self, win_rate: float, avg_win: float, avg_loss: float
    ) -> float:
        """Calcula la fracción de Kelly (retorna half-Kelly por conservadurismo)."""
        if avg_loss == 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0
        b = avg_win / avg_loss  # odds ratio
        kelly = (win_rate * b - (1 - win_rate)) / b
        half_kelly = max(0, kelly / 2)
        return round(half_kelly, 4)

    def print_position_size(
        self, entry_price: float, stop_price: float, account_equity: float
    ):
        """Imprime un resumen del dimensionamiento de posición."""
        result = self.calculate_position_size(entry_price, stop_price, account_equity)
        target_price = entry_price + 2 * abs(entry_price - stop_price)
        rr = self.calculate_reward_risk_ratio(entry_price, stop_price, target_price)

        print("\n=== DIMENSIONAMIENTO DE POSICIÓN ===")
        print(f"  Capital:            ${account_equity:,.2f}")
        print(f"  Riesgo por trade:   {self.config.risk_per_trade:.0%}")
        print(f"  Precio entrada:     ${entry_price:.2f}")
        print(f"  Stop loss:          ${stop_price:.2f}")
        print(f"  Target (2:1 R/R):   ${target_price:.2f}")
        print(f"  Acciones:           {result['shares']}")
        print(f"  Valor posición:     ${result['position_value']:,.2f}")
        print(f"  Riesgo en dólares:  ${result['dollar_risk']:,.2f}")
        print(f"  % del capital:      {result['pct_of_account']:.1f}%")
        print(f"  Ratio R/R:          {rr}:1")
        print()
