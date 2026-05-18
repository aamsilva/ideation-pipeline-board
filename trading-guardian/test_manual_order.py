#!/usr/bin/env python3
import os
import sys

# Set LIVE credentials
os.environ['ALPACA_API_KEY'] = 'AKAHSR7C6XH7OAR7L6EJYVCRRK'
os.environ['ALPACA_SECRET_KEY'] = 'DjM8rMUbwHnGbkUJJoTt5BpAiujuQ39vzpxFosm2YEac'
os.environ['ALPACA_BASE_URL'] = 'https://api.alpaca.markets'

sys.path.insert(0, '/Volumes/disco1tb/projects/trading-guardian/src')

from alpaca_executor import AlpacaExecutor

print("=" * 60)
print("🚀 MANUAL ORDER TEST - ALPACA LIVE")
print("=" * 60)

executor = AlpacaExecutor(use_live=True)

# Get account info
account = executor.get_account()
if account:
    print(f"\n💰 Account: {account.get('account_number', 'N/A')}")
    print(f"   Cash: ${float(account.get('cash', 0)):.2f}")
    print(f"   Buying Power: ${float(account.get('buying_power', 0)):.2f}")

# Place a small market buy order for MSFT ($10 worth)
symbol = 'MSFT'
current_price = executor.get_current_price(symbol)
if not current_price:
    print(f"❌ Failed to get price for {symbol}")
    sys.exit(1)

qty = round(10.0 / current_price, 4)  # $10 worth
print(f"\n📈 Placing BUY order: {qty} {symbol} @ ~${current_price:.2f} (${10:.2f})")

order = executor.submit_order(
    symbol=symbol,
    qty=qty,
    side='buy',
    order_type='market'
)

if order:
    print(f"✅ ORDER PLACED SUCCESSFULLY!")
    print(f"   Order ID: {order.get('id', 'N/A')}")
    print(f"   Status: {order.get('status', 'N/A')}")
    print(f"   Symbol: {order.get('symbol', 'N/A')}")
    print(f"   Qty: {order.get('qty', 'N/A')}")
    print(f"   Side: {order.get('side', 'N/A')}")
    print(f"   Type: {order.get('type', 'N/A')}")
else:
    print("❌ Failed to place order")

# Check recent orders
print("\n📋 Recent Orders:")
orders = executor.get_orders(status='all', limit=3)
for order in orders:
    print(f"  {order.get('side', '?').upper():5} {order.get('qty', '?'):10} {order.get('symbol', '?'):6} | {order.get('status', '?'):10} | ID: {order.get('id', '?')[:8]}")