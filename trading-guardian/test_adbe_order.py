#!/usr/bin/env python3
"""Test ADBE sell order to debug failure"""
import os
import sys
sys.path.insert(0, '/Volumes/disco1tb/projects/trading-guardian/src')

os.environ['ALPACA_API_KEY'] = 'AKAHSR7C6XH7OAR7L6EJYVCRRK'
os.environ['ALPACA_SECRET_KEY'] = 'DjM8rMUbwHnGbkUJJoTt5BpAiujuQ39vzpxFosm2YEac'

from alpaca_executor import AlpacaExecutor

executor = AlpacaExecutor(use_live=True)
print("🧪 TESTE ADBE SELL ORDER")
print("=" * 50)

# 1. Check position qty
print("\n1. Checking ADBE position...")
acc = executor.session.get(f"{executor.base_url}/v2/positions/ADBE", timeout=10)
if acc.status_code == 200:
    pos = acc.json()
    qty = float(pos['qty'])
    print(f"   ADBE Position: {qty} shares")
else:
    print(f"   Error: {acc.status_code} - {acc.text}")
    qty = 0.1122  # fallback to expected qty

# 2. Submit sell order with exact qty
print(f"\n2. Submitting SELL {qty} ADBE...")
result = executor.submit_order('ADBE', qty, 'sell', 'market')
if result:
    print(f"   ✅ SUCCESS! Order ID: {result.get('id')}")
    print(f"   Status: {result.get('status')}")
    print(f"   Filled Qty: {result.get('filled_qty')}")
else:
    print(f"   ❌ FAILED (submit_order returned None)")
