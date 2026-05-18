
import os
os.environ['ALPACA_API_KEY'] = 'AKAHSR7C6XH7OAR7L6EJYVCRRK'
os.environ['ALPACA_SECRET_KEY'] = 'DjM8rMUbwHnGbkUJJoTt5BpAiujuQ39vzpxFosm2YEac'
os.environ['ALPACA_BASE_URL'] = 'https://api.alpaca.markets'

import sys
sys.path.insert(0, '/Volumes/disco1tb/projects/trading-guardian/src')

from alpaca_executor import AlpacaExecutor
from strategy_bollinger import BollingerStrategy
from strategy_momentum import MomentumStrategy
from strategy_rsi import RSIStrategy

executor = AlpacaExecutor(use_live=True)

# Test symbols
symbols = ['AAPL', 'AMD', 'INTC', 'GOOGL', 'MSFT']
for sym in symbols:
    print(f"\n{'='*40}")
    print(f"TESTING {sym}")
    print('='*40)
    
    # Get current price
    price = executor.get_current_price(sym)
    if not price:
        print(f"❌ Failed to get price for {sym}")
        continue
    print(f"Current Price: ${price:.2f}")
    
    # Get position qty
    positions = executor.get_positions()
    qty = positions.get(sym, {}).get('qty', 0)
    print(f"Position Qty: {qty}")
    
    # Test Bollinger
    bb_strategy = BollingerStrategy()
    bb_strategy.client = executor
    bb_signal = bb_strategy.get_signal(sym, price, qty)
    print(f"Bollinger Signal: {bb_signal}")
    
    # Test Momentum
    mom_strategy = MomentumStrategy()
    mom_strategy.client = executor
    mom_signal = mom_strategy.get_signal(sym, price, qty)
    print(f"Momentum Signal: {mom_signal}")
    
    # Test RSI
    rsi_strategy = RSIStrategy()
    rsi_strategy.client = executor
    rsi_signal = rsi_strategy.get_signal(sym, price, qty)
    print(f"RSI Signal: {rsi_signal}")
