#!/usr/bin/env python3
"""
RSI Reversal Strategy - Plugin for StrategyEngine
Compra quando RSI < 30 (sobrevendido), Vende quando RSI > 70 (sobrecomprado)
"""

from alpaca_executor import get_executor

class RSIStrategy:
    """Estratégia RSI Reversal"""
    
    def __init__(self, period=14, oversold=30, overbought=70):
        self.client = None  # Will be set by StrategyEngine
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.name = "RSIReversal"
    
    def calculate_rsi(self, symbol):
        """Calcula RSI (Relative Strength Index)"""
        try:
            bars = self.client.get_bars(symbol, period=self.period + 10)
            
            if len(bars) < self.period + 1:
                return None
            
            # Usar closings dos últimos period+1 dias
            closes = [float(b['c']) for b in bars[-(self.period + 1):]]
            
            # Calcular ganhos e perdas
            gains = []
            losses = []
            
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            # Média de ganhos e perdas
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            
            if avg_loss == 0:
                return 100  # Sem perdas = RSI 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            print(f"❌ Error calculating RSI for {symbol}: {e}")
            return None
    
    def get_signal(self, symbol, current_price, qty):
        """Gera sinal baseado em RSI"""
        try:
            rsi = self.calculate_rsi(symbol)
            
            if rsi is None:
                return None
            
            # RSI sobrevendido (compra)
            if rsi <= self.oversold:
                return {
                    'signal': 'BUY',
                    'symbol': symbol,
                    'price': current_price,
                    'qty': 0.01,
                    'confidence': 0.75,
                    'reason': f"RSI {rsi:.1f} <= {self.oversold} (oversold)",
                    'rsi': rsi
                }
            
            # RSI sobrecomprado (venda)
            elif rsi >= self.overbought:
                if qty > 0:  # Só vende se tem posição
                    return {
                        'signal': 'SELL',
                        'symbol': symbol,
                        'price': current_price,
                        'qty': qty,
                        'confidence': 0.75,
                        'reason': f"RSI {rsi:.1f} >= {self.overbought} (overbought)",
                        'rsi': rsi
                    }
            
            # RSI neutro - HOLD
            return None
            
        except Exception as e:
            print(f"❌ Error in RSIStrategy for {symbol}: {e}")
            return None
    
    def update_opening_range(self, symbol, current_price):
        """Compatibility method (not used in this strategy)"""
        pass


if __name__ == "__main__":
    # Test
    strategy = RSIStrategy()
    client = get_executor()
    
    print("Testing RSIStrategy...")
    positions = client.get_positions()
    
    for symbol, data in positions.items():
        signal = strategy.get_signal(symbol, data['current'], data['qty'])
        if signal:
            print(f"✅ Signal for {symbol}: {signal['signal']}")
            print(f"   Reason: {signal['reason']}")
        else:
            # Mostrar RSI mesmo sem sinal
            rsi = strategy.calculate_rsi(symbol)
            if rsi:
                print(f"• {symbol}: RSI = {rsi:.1f} (no signal)")
            else:
                print(f"• {symbol}: RSI calculation failed")
