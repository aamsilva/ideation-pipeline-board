#!/usr/bin/env python3
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger("SentinelRisk")

class SentinelRiskManager:
    def __init__(self, max_sector_exposure=0.35, max_asset_exposure=0.15):
        self.max_sector_exposure = max_sector_exposure # Max 35% per sector
        self.max_asset_exposure = max_asset_exposure   # Max 15% per asset
        self.sector_map = {
            "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology", "AMD": "Technology",
            "GOOGL": "Technology", "META": "Technology", "INTC": "Technology",
            "COHR": "Technology", "AXTI": "Technology", "WOR": "Industrials",
            "JPM": "Financials", "GS": "Financials", "TSLA": "Consumer Cyclical"
        }

    def audit_trade(self, order: Dict, current_portfolio: List[Dict], macro_score: float) -> Tuple[bool, str]:
        """
        Audita uma ordem proposta.
        Retorna (Aprovado, Razão)
        """
        symbol = order.get('symbol')
        side = order.get('action', order.get('side', 'buy')).upper()
        
        # Só auditamos compras (vendas de emergência/lucro são sempre permitidas)
        if side == 'SELL':
            return True, "Sell orders are always risk-reducing. Approved."

        # 1. Verificar exposição ao ativo
        total_value = sum(p.get('market_value', 0) for p in current_portfolio)
        # Se o portfólio estiver vazio, permitimos a primeira compra
        if total_value == 0:
            return True, "First trade of the session. Approved."

        asset_value = next((p.get('market_value', 0) for p in current_portfolio if p['symbol'] == symbol), 0)
        proposed_value = order.get('qty', 0) * order.get('price', 100)
        
        asset_pct = (asset_value + proposed_value) / total_value
        if asset_pct > self.max_asset_exposure:
            return False, f"VETO: Asset exposure for {symbol} would be {asset_pct:.1%}, exceeding limit of {self.max_asset_exposure:.1%}"

        # 2. Verificar exposição ao setor
        sector = self.sector_map.get(symbol, "Unknown")
        sector_value = sum(p.get('market_value', 0) for p in current_portfolio if self.sector_map.get(p['symbol']) == sector)
        
        sector_pct = (sector_value + proposed_value) / total_value
        if sector_pct > self.max_sector_exposure:
            return False, f"VETO: Sector exposure for {sector} would be {sector_pct:.1%}, exceeding limit of {self.max_sector_exposure:.1%}"

        # 3. Verificar Risco Macro
        if macro_score < -0.6 and side == 'BUY':
            return False, f"VETO: Extreme Macro Risk (Score: {macro_score}). All new buys suspended."

        return True, "Risk limits within safety bounds. Approved."

if __name__ == "__main__":
    # Teste rápido
    manager = SentinelRiskManager()
    mock_order = {"symbol": "AAPL", "side": "buy", "qty": 10, "price": 200}
    mock_portfolio = [{"symbol": "MSFT", "market_value": 5000}, {"symbol": "NVDA", "market_value": 4000}]
    
    approved, reason = manager.audit_trade(mock_order, mock_portfolio, 0.0)
    print(f"Audit Result: {approved} - {reason}")
