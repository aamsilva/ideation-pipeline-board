#!/usr/bin/env python3
import os
import sys

# Set credentials
os.environ['ALPACA_API_KEY'] = 'PK63TBHHGVGOO7U4BZHPIPL6FJ'
os.environ['ALPACA_SECRET_KEY'] = '84e9pSN4f8sxpoL5iJFYbJqtsN9eoCQbwPbSMdcdpZqB'
os.environ['ALPACA_BASE_URL'] = 'https://paper-api.alpaca.markets'

# Add path
sys.path.insert(0, '/Volumes/disco1tb/projects/trading-guardian/src')

from alpaca_executor import AlpacaExecutor

print("Testing Alpaca Connection...")
executor = AlpacaExecutor(use_live=False)

# Test account
print("\n1. Testing Account Access:")
account = executor.get_account()
if account:
    print(f"✅ Account ID: {account.get('id', 'N/A')}")
    print(f"   Cash: ${float(account.get('cash', 0)):.2f}")
    print(f"   Buying Power: ${float(account.get('buying_power', 0)):.2f}")
    print(f"   Portfolio Value: ${float(account.get('portfolio_value', 0)):.2f}")
else:
    print("❌ Failed to access account")

# Test positions
print("\n2. Testing Positions:")
positions = executor.get_positions()
print(f"   Positions count: {len(positions)}")
for sym, data in positions.items():
    print(f"   {sym}: {data['qty']} @ ${data['current']:.2f}")

# Test price fetch
print("\n3. Testing Price Fetch (AAPL):")
price = executor.get_current_price('AAPL')
if price:
    print(f"✅ AAPL price: ${price:.2f}")
else:
    print("❌ Failed to fetch price")

# Test bars
print("\n4. Testing Bars (AAPL, 5 days):")
bars = executor.get_bars('AAPL', period=5)
if bars:
    print(f"✅ Got {len(bars)} bars")
    print(f"   Latest close: ${float(bars[-1]['c']):.2f}")
else:
    print("❌ Failed to fetch bars")

# Test Bollinger Bands
print("\n5. Testing Bollinger Bands (AAPL):")
bb = executor.calculate_bollinger_bands('AAPL', period=20)
if bb:
    print(f"✅ BB calculated:")
    print(f"   Upper: ${bb['upper']:.2f}")
    print(f"   Middle: ${bb['middle']:.2f}")
    print(f"   Lower: ${bb['lower']:.2f}")
    print(f"   Current: ${bb['current']:.2f}")
else:
    print("❌ Failed to calculate BB")