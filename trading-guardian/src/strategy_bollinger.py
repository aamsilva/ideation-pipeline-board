#!/usr/bin/env python3
"""
Bollinger Bands Strategy - Plugin for StrategyEngine
Gera sinais baseados em Bollinger Bands
"""

from alpaca_executor import get_executor

class BollingerStrategy:
    """Estratégia Bollinger Bands"""
    
    def __init__(self, period=30, std_dev=2.5, touch_threshold=0.002):
        self.client = get_executor(use_live=False)
        self.period = period
        self.std_dev = std_dev
        self.touch_threshold = touch_threshold  # 0.2% tolerance
        self.name = "BollingerBands"
    
    def get_signal(self, symbol, current_price, qty):
        """Gera sinal baseado em Bollinger Bands"""
        try:
            bb = self.client.calculate_bollinger_bands(
                symbol, 
                period=self.period, 
                std_dev=self.std_dev
            )
            
            if not bb:
                return None
            
            # Verificar se toca banda inferior (BUY)
            if current_price <= bb['lower'] * (1 + self.touch_threshold):
                return {
                    'signal': 'BUY',
                    'symbol': symbol,
                    'price': current_price,
                    'qty': 0.01,  # Small size for safety
                    'confidence': 0.8,
                    'reason': f"Price ${current_price:.2f} near Bollinger lower ${bb['lower']:.2f}",
                    'bb': bb
                }
            
            # Verificar se toca banda superior (SELL)
            elif current_price >= bb['upper'] * (1 - self.touch_threshold):
                if qty > 0:  # Only sell if we have position
                    return {
                        'signal': 'SELL',
                        'symbol': symbol,
                        'price': current_price,
                        'qty': qty,
                        'confidence': 0.8,
                        'reason': f"Price ${current_price:.2f} near Bollinger upper ${bb['upper']:.2f}",
                        'bb': bb
                    }
            
            # Dentro das bandas - HOLD
            return None
            
        except Exception as e:
            print(f"❌ Error in BollingerStrategy for {symbol}: {e}")
            return None
    
    def update_opening_range(self, symbol, current_price):
        """Compatibility method (not used in this strategy)"""
        pass


if __name__ == "__main__":
    # Test
    strategy = BollingerStrategy()
    client = get_executor()
    
    print("Testing BollingerStrategy...")
    positions = client.get_positions()
    
    for symbol, data in positions.items():
        signal = strategy.get_signal(symbol, data['current'], data['qty'])
        if signal:
            print(f"✅ Signal for {symbol}: {signal['signal']}")
            print(f"   Reason: {signal['reason']}")
        else:
            print(f"• No signal for {symbol} at ${data['current']:.2f}")
