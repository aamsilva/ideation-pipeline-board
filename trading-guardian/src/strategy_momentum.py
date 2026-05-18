#!/usr/bin/env python3
"""
Momentum Strategy - Plugin for StrategyEngine
Deteta momentum de curto prazo (tendência de preços)
"""

from alpaca_executor import get_executor
from datetime import datetime, timedelta

class MomentumStrategy:
    """Estratégia Momentum"""
    
    def __init__(self, period=10, threshold=0.02):
        self.client = None  # Will be set by StrategyEngine
        self.period = period  # Dias para cálculo de momentum
        self.threshold = threshold  # 2% mudança mínima
        self.name = "Momentum"
    
    def calculate_momentum(self, symbol):
        """Calcula momentum (retorno percentual sobre period dias)"""
        try:
            bars = self.client.get_bars(symbol, period=self.period + 5)
            
            if len(bars) < self.period:
                return None
            
            # Usar closings dos últimos period dias
            closes = [float(b['c']) for b in bars[-self.period:]]
            
            if len(closes) < 2:
                return None
            
            start_price = closes[0]
            end_price = closes[-1]
            
            momentum = (end_price - start_price) / start_price
            
            return momentum
            
        except Exception as e:
            print(f"❌ Error calculating momentum for {symbol}: {e}")
            return None
    
    def get_signal(self, symbol, current_price, qty):
        """Gera sinal baseado em momentum"""
        try:
            momentum = self.calculate_momentum(symbol)
            
            if momentum is None:
                return None
            
            # Momentum positivo forte (COMPRA)
            if momentum > self.threshold:
                if qty == 0:  # Só compra se não tem posição
                    return {
                        'signal': 'BUY',
                        'symbol': symbol,
                        'price': current_price,
                        'qty': 0.01,
                        'confidence': 0.7 + min(momentum * 5, 0.2),  # Confiança baseada no momentum
                        'reason': f"Momentum {momentum*100:.1f}% > {self.threshold*100:.0f}% (upward trend)",
                        'momentum': momentum
                    }
            
            # Momentum negativo forte (VENDA)
            elif momentum < -self.threshold:
                if qty > 0:  # Só vende se tem posição
                    return {
                        'signal': 'SELL',
                        'symbol': symbol,
                        'price': current_price,
                        'qty': qty,
                        'confidence': 0.7 + min(abs(momentum) * 5, 0.2),
                        'reason': f"Momentum {momentum*100:.1f}% < -{self.threshold*100:.0f}% (downward trend)",
                        'momentum': momentum
                    }
            
            # Momentum fraco - HOLD
            return None
            
        except Exception as e:
            print(f"❌ Error in MomentumStrategy for {symbol}: {e}")
            return None
    
    def update_opening_range(self, symbol, current_price):
        """Compatibility method (not used in this strategy)"""
        pass


if __name__ == "__main__":
    # Test
    strategy = MomentumStrategy()
    client = get_executor()
    
    print("Testing MomentumStrategy...")
    positions = client.get_positions()
    
    for symbol, data in positions.items():
        signal = strategy.get_signal(symbol, data['current'], data['qty'])
        momentum = strategy.calculate_momentum(symbol)
        
        if signal:
            print(f"✅ Signal for {symbol}: {signal['signal']}")
            print(f"   Reason: {signal['reason']}")
        else:
            if momentum is not None:
                print(f"• {symbol}: Momentum = {momentum*100:.1f}% (no signal)")
            else:
                print(f"• {symbol}: Momentum calculation failed")
