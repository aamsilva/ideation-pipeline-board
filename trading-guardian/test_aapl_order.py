#!/usr/bin/env python3
"""Test submit_order for AAPL to debug failure"""
import os
import sys
sys.path.insert(0, '/Volumes/disco1tb/projects/trading-guardian/src')

os.environ['ALPACA_API_KEY'] = 'AKAHSR7C6XH7OAR7L6EJYVCRRK'
os.environ['ALPACA_SECRET_KEY'] = 'DjM8rMUbwHnGbkUJJoTt5BpAiujuQ39vzpxFosm2YEac'

from alpaca_executor import AlpacaExecutor

# Initialize live executor
executor = AlpacaExecutor(use_live=True)
print("🧪 TESTE DE ORDEM AAPL (SELL 0.1253)")
print("=" * 50)

# 1. Get current price for AAPL
price = executor.get_current_price('AAPL')
print(f"1. Current price AAPL: ${price:.2f}" if price else "1. Current price AAPL: FAILED")

# 2. Calculate notional
if price:
    qty = 0.1253
    notional = round(qty * price, 2)
    print(f"2. Notional for {qty} shares: ${notional:.2f}")
else:
    notional = None
    print("2. Notional: Can't calculate (price failed)")

# 3. Submit order with notional
print("\n3. Submitting SELL order for AAPL...")
if notional:
    # Submit with notional
    data = {
        'symbol': 'AAPL',
        'notional': notional,
        'side': 'sell',
        'type': 'market',
        'time_in_force': 'day',
        'extended_hours': False
    }
    resp = executor.session.post(f"{executor.base_url}/v2/orders", json=data, timeout=10)
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.text[:300]}")
else:
    # Fallback to qty
    print("   Falling back to qty (notional failed)...")
    result = executor.submit_order('AAPL', 0.1253, 'sell', 'market')
    print(f"   Result: {result}")
