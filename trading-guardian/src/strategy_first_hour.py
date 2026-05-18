#!/usr/bin/env python3
"""
First Hour Breakout Strategy with Bollinger Confirmation
Combina breakout dos primeiros 15min com confirmação Bollinger
"""

from alpaca_executor import get_executor
from datetime import datetime, timedelta

class FirstHourBreakoutStrategy:
    """Estratégia que deteta breakout na primeira hora e confirma com Bollinger"""
    
    def __init__(self):
        # self.client = get_executor(use_live=False)
        self.opening_range = {}  # {symbol: {'high': x, 'low': y, 'time': t}}
        
    def update_opening_range(self, symbol, current_price):
        """Atualiza o range de abertura (primeiros 15 min após market open)"""
        now = datetime.now()
        market_open = now.replace(hour=14, minute=30, second=0, microsecond=0)  # 14:30 GMT+1
        
        # Se estamos nos primeiros 15 min após abertura
        if now >= market_open and now <= market_open + timedelta(minutes=15):
            if symbol not in self.opening_range:
                self.opening_range[symbol] = {
                    'high': current_price,
                    'low': current_price,
                    'start_time': now
                }
            else:
                self.opening_range[symbol]['high'] = max(self.opening_range[symbol]['high'], current_price)
                self.opening_range[symbol]['low'] = min(self.opening_range[symbol]['low'], current_price)
    
    def get_signal(self, symbol, current_price, qty):
        """Gera sinal combinado: Breakout + Bollinger"""
        
        # 1. Verificar se temos range de abertura
        if symbol not in self.opening_range:
            return None  # Ainda não temos dados suficientes
        
        range_data = self.opening_range[symbol]
        
        # 2. Detetar breakout (preço rompe high/low do range)
        signal = None
        if current_price > range_data['high'] * 1.001:  # 0.1% acima do high
            signal = 'BUY'
            reason = f"Breakout acima de ${range_data['high']:.2f}"
        elif current_price < range_data['low'] * 0.999:  # 0.1% abaixo do low
            if qty > 0:  # Só vendemos se temos posição
                signal = 'SELL'
                reason = f"Breakdown abaixo de ${range_data['low']:.2f}"
            else:
                return None  # Sem posição para vender
        else:
            return None  # Dentro do range
        
        # 3. Confirmar com Bollinger Bands
        bb = self.client.calculate_bollinger_bands(symbol, period=30, std_dev=2.5)
        if not bb:
            return None  # Não temos dados Bollinger
        
        # Confirmar direção com Bollinger
        if signal == 'BUY' and current_price <= bb['lower'] * 1.002:
            # Compra confirmada: breakout + perto da banda inferior
            confidence = 0.9
            reason += f" + Bollinger lower band (${bb['lower']:.2f})"
        elif signal == 'SELL' and current_price >= bb['upper'] * 0.998:
            # Venda confirmada: breakdown + perto da banda superior
            confidence = 0.9
            reason += f" + Bollinger upper band (${bb['upper']:.2f})"
        else:
            # Sinal não confirmado por Bollinger
            confidence = 0.6
            reason += f" (Bollinger não confirma: ${bb['current']:.2f} in [${bb['lower']:.2f}, ${bb['upper']:.2f}])"
        
        return {
            'signal': signal,
            'symbol': symbol,
            'price': current_price,
            'qty': 0.01,  # Tamanho pequeno para teste
            'confidence': confidence,
            'reason': reason,
            'bb': bb
        }
    
    def reset_daily(self):
        """Reset diário (chamar após fecho do mercado)"""
        self.opening_range = {}


# Exemplo de uso
if __name__ == "__main__":
    strategy = FirstHourBreakoutStrategy()
    
    # Simular atualização de preços
    print("Testing FirstHourBreakoutStrategy...")
    
    # Simular preços
    test_prices = {
        'AAPL': 276.50,
        'AMD': 350.00,
        'META': 613.00
    }
    
    for symbol, price in test_prices.items():
        # Atualizar range de abertura
        strategy.update_opening_range(symbol, price)
        
        # Obter posição atual (se existir)
        positions = strategy.client.get_positions()
        qty = positions.get(symbol, {}).get('qty', 0)
        
        # Obter sinal
        signal = strategy.get_signal(symbol, price, qty)
        if signal:
            print(f"\n✅ Signal for {symbol}:")
            print(f"   Signal: {signal['signal']}")
            print(f"   Price: ${signal['price']:.2f}")
            print(f"   Confidence: {signal['confidence']:.1f}")
            print(f"   Reason: {signal['reason']}")
        else:
            print(f"\n• No signal for {symbol} at ${price:.2f}")
