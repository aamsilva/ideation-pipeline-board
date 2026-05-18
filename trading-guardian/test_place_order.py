#!/usr/bin/env python3
import os
import sys

# Set Alpaca credentials
os.environ['ALPACA_API_KEY'] = 'PK63TBHHGVGOO7U4BZHPIPL6FJ'
os.environ['ALPACA_SECRET_KEY'] = '84e9pSN4f8sxpoL5iJFYbJqtsN9eoCQbwPbSMdcdpZqB'
os.environ['ALPACA_BASE_URL'] = 'https://paper-api.alpaca.markets'

# Add project to path
sys.path.insert(0, '/Volumes/disco1tb/projects/trading-guardian/src')
sys.path.insert(0, '/Volumes/disco1tb/projects/trading-guardian')

from guardian_core import TradingGuardian

print("Initializing Trading Guardian...")
guardian = TradingGuardian()

print("\n✅ Guardian initialized")
print(f"Credentials OK: {guardian.credentials_ok}")

# Get paper executor
paper = guardian.alpaca_executor_paper
print(f"Paper executor: {paper}")

# Get account info
account = paper.get_account()
if account:
    print(f"\n💰 Account Cash: ${float(account.get('cash', 0)):.2f}")
    print(f"💰 Buying Power: ${float(account.get('buying_power', 0)):.2f}")

# Get current positions
positions = paper.get_positions()
print(f"\n📊 Current positions: {len(positions)}")
for sym, data in positions.items():
    print(f"  {sym}: {data['qty']} @ ${data['current']:.2f} | PnL: ${data['pnl']:.2f}")

# Run a strategy engine cycle
print("\n🚀 Running strategy engine cycle...")
if hasattr(guardian, 'strategy_engine'):
    engine = guardian.strategy_engine
    print(f"Strategies loaded: {list(engine.strategies.keys())}")
    
    # Prepare prices dict for cycle
    prices = {}
    for sym, data in positions.items():
        prices[sym] = {'qty': data['qty'], 'current': data['current']}
    
    # Add some watch symbols not in positions
    watchlist = ['AMD', 'INTC', 'GOOGL', 'MSFT', 'AAPL']
    for sym in watchlist:
        if sym not in prices:
            price = paper.get_current_price(sym)
            if price:
                prices[sym] = {'qty': 0, 'current': price}
    
    print(f"Analyzing {len(prices)} symbols...")
    executed = engine.run_cycle(prices)
    print(f"\n✅ Executed {executed} trades")
else:
    print("❌ Strategy engine not found")

# Check recent orders
orders = paper.get_orders(status='all', limit=5)
print(f"\n📋 Recent orders ({len(orders)}):")
for order in orders[:5]:
    print(f"  {order.get('side', '?').upper()} {order.get('qty', '?')} {order.get('symbol', '?')} | Status: {order.get('status', '?')} | ID: {order.get('id', '?')[:8]}")