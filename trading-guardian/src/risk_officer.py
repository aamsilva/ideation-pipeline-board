#!/usr/bin/env python3
"""
Trading Guardian - Risk Officer Agent
Continuous portfolio volatility monitor and absolute circuit breaker.
"""

import os
import json
import logging
from typing import Dict, List, Tuple
from alpaca_executor import AlpacaExecutor

logger = logging.getLogger("RiskOfficer")

class RiskOfficer:
    def __init__(self, max_drawdown_pct: float = 8.0, stop_loss_pct: float = 5.0):
        self.max_drawdown_pct = max_drawdown_pct  # Max portfolio drawdown (8%)
        self.stop_loss_pct = stop_loss_pct        # Stop loss per asset (5%)
        self.alpaca_executor = AlpacaExecutor(use_live=False) # Default to Paper for risk monitoring
        
    def check_portfolio_limits(self, positions: Dict, account_info: Dict) -> Tuple[bool, str, List[str]]:
        """
        Check for position stop-losses or overall portfolio drawdown circuit breaker.
        Returns: (is_healthy, reason, list_of_symbols_to_liquidate)
        """
        if not positions:
            return True, "No active positions", []
            
        symbols_to_liquidate = []
        portfolio_value = float(account_info.get("portfolio_value", 0))
        cash = float(account_info.get("cash", 0))
        
        # Check individual stop-losses
        for sym, data in positions.items():
            qty = float(data.get("qty", 0))
            if qty <= 0:
                continue
            
            pnl_pct = float(data.get("pnl", 0))
            # If a position is down by more than our stop-loss threshold
            if pnl_pct <= -self.stop_loss_pct:
                logger.warning(f"⚠️ STOP-LOSS TRIGGERED: {sym} is down {pnl_pct:.2f}% (Limit: -{self.stop_loss_pct}%)")
                symbols_to_liquidate.append(sym)
                
        if symbols_to_liquidate:
            return False, f"Stop-loss breached for assets: {', '.join(symbols_to_liquidate)}", symbols_to_liquidate
            
        # Check overall portfolio drawdown (unrealized P&L vs total value)
        total_pnl = sum(float(p.get("pnl_usd", 0)) for p in positions.values())
        if portfolio_value > 0:
            drawdown_pct = (total_pnl / portfolio_value) * 100
            if drawdown_pct <= -self.max_drawdown_pct:
                logger.critical(f"🚨 PORTFOLIO CIRCUIT BREAKER: Drawdown is {drawdown_pct:.2f}% (Limit: -{self.max_drawdown_pct}%)")
                # Liquidate all positions
                return False, f"Portfolio drawdown {drawdown_pct:.2f}% breached circuit breaker!", list(positions.keys())
                
        return True, "All risk parameters within safety margins", []

    def execute_emergency_liquidation(self, symbols: List[str]):
        """
        Immediately cancels all pending orders and issues market sell orders for the target symbols.
        """
        if not symbols:
            return
            
        logger.critical(f"🔥 EMERGENCY LIQUIDATION initiated for: {', '.join(symbols)}")
        try:
            # 1. Cancel all active orders first
            self.alpaca_executor.cancel_all_orders()
            logger.info("   ✅ All pending orders cancelled.")
            
            # 2. Market sell each symbol
            positions = self.alpaca_executor.get_positions()
            for sym in symbols:
                pos_data = positions.get(sym)
                if pos_data:
                    qty = float(pos_data.get("qty", 0))
                    if qty > 0:
                        logger.warning(f"   ⚡ Selling {qty} shares of {sym} via emergency Market Order...")
                        self.alpaca_executor.submit_order(sym, qty, "sell", "market")
                        logger.info(f"   ✅ Emergency sell order submitted for {sym}")
        except Exception as e:
            logger.error(f"❌ Failed to complete emergency liquidation: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    officer = RiskOfficer()
    print("Risk Officer initialized successfully.")
