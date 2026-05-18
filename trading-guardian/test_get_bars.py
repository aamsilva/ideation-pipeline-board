#!/usr/bin/env python3
"""Test get_bars directly with Live Executor"""
import os
import sys

# Set live credentials
os.environ['ALPACA_API_KEY'] = 'AKAHSR7C6XH7OAR7L6EJYVCRRK'
os.environ['ALPACA_SECRET_KEY'] = 'DjM8rMUbwHnGbkUJJoTt5BpAiujuQ39vzpxFosm2YEac'
os.environ['ALPACA_BASE_URL'] = 'https://api.alpaca.markets'

sys.path.insert(0, '/Volumes/disco1tb/projects/trading-guardian/src')

from alpaca_executor import AlpacaExecutor

print("🧪 TESTING get_bars WITH LIVE EXECUTOR")
print("=" * 50)

# Create live executor
executor = AlpacaExecutor(use_live=True)
print(f"✅ Executor created (live={executor.use_live})")
print(f"   Data URL: {executor.data_url}")

# Test get_bars for MSFT (14 period)
print("\n📈 Fetching 24 bars for MSFT (period=14 + 10)...")
bars = executor.get_bars(symbol="MSFT", period=24, timeframe='1Day')
print(f"   Bars returned: {len(bars)}")

if bars:
    print("\n   Last 5 bars:")
    for bar in bars[-5:]:
        print(f"   {bar.get('t')}: Close=${float(bar.get('c', 0)):.2f}")
else:
    print("   ❌ No bars returned - checking API response...")
    # Let's check the raw response
    import requests
    from datetime import datetime, timedelta
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=24 * 2)
    params = {
        'start': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'end': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'timeframe': '1Day',
        'limit': 24,
        'adjustment': 'all'
    }
    resp = executor.session.get(f"{executor.data_url}/v2/stocks/MSFT/bars", params=params, timeout=10)
    print(f"   API Status: {resp.status_code}")
    print(f"   API Response: {resp.text[:200]}")

# Test RSI calculation with valid bars
print("\n🧮 Testing RSI calculation with valid bars...")
if bars and len(bars) >= 15:
    closes = [float(b['c']) for b in bars[-15:]]
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
    avg_gain = sum(gains)/len(gains) if gains else 0
    avg_loss = sum(losses)/len(losses) if losses else 0
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100/(1+rs))
    print(f"   RSI for MSFT: {rsi:.1f}")
else:
    print("   ❌ Insufficient bars for RSI calculation")
