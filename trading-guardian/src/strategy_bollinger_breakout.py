#!/usr/bin/env python3
"""Simple Bollinger Bands breakout strategy for Trading Guardian."""
import logging
from typing import Dict, Optional

class StrategyBollingerBreakout:
    """Bollinger Bands breakout strategy.
    Buys when price closes below lower band (oversold bounce).
    Sells when price closes above upper band (overbought drop).
    """
    def __init__(self, alpaca_executor=None):
        self.client = alpaca_executor
        self.logger = logging.getLogger(__name__)

    def get_signal(self, symbol: str, current_price: float, qty: float = 1.0) -> Optional[Dict]:
        """Generate trading signal based on Bollinger Bands.
        
        Args:
            symbol: Stock ticker
            current_price: Current price (unused, we fetch from BB)
            qty: Position size
        
        Returns:
            {'signal': 'BUY'|'SELL', 'confidence': 0-1} or None
        """
        if self.client is None:
            return None
        
        try:
            bb = self.client.calculate_bollinger_bands(symbol)
            if bb is None:
                return None
            
            price = bb.get('current', current_price)
            upper = bb.get('upper', price)
            lower = bb.get('lower', price)
            
            # Buy signal: price below lower band (oversold)
            if price < lower:
                self.logger.info("BUY signal: %s below lower BB (%.2f < %.2f)", symbol, price, lower)
                return {'signal': 'BUY', 'confidence': 0.75, 'reason': 'bb_oversold'}
            
            # Sell signal: price above upper band (overbought)
            if price > upper:
                self.logger.info("SELL signal: %s above upper BB (%.2f > %.2f)", symbol, price, upper)
                return {'signal': 'SELL', 'confidence': 0.75, 'reason': 'bb_overbought'}
            
            return None
        except Exception as e:
            self.logger.error("get_signal error for %s: %s", symbol, e)
            return None