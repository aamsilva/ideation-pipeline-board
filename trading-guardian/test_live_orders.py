#!/usr/bin/env python3
import os
import sys

# Set LIVE Alpaca credentials (these work!)
os.environ['ALPACA_API_KEY'] = 'AKAHSR7C6XH7OAR7L6EJYVCRRK'
os.environ['ALPACA_SECRET_KEY'] = 'DjM8rMUbwHnGbkUJJoTt5BpAiujuQ39vzpxFosm2YEac'
os.environ['ALPACA_BASE_URL'] = 'https://api.alpaca.markets'

# Add project to path
sys.path.insert(0, '/Volumes/disco1tb/projects/trading-guardian/src')
sys.path.insert(0, '/Volumes/disco1tb/projects/trading-guardian')

from guardian_core import TradingGuardian

print("=" * 60)
print("🚀 TRADING GUARDIAN - LIVE ACCOUNT TEST")
print("=" * 60)

# Initialize Guardian
print("\nInitializing Trading Guardian...")
guardian = TradingGuardian()

# Use LIVE executor
print("\n✅ Using LIVE Alpaca Account")
live_exec = guardian.alpaca_executor_live
if not live_exec:
    print("❌ Live executor not available")
    sys.exit(1)

# Get account info
account = live_exec.get_account()
if account:
    print(f"\n💰 Account Status: {account.get('status', 'N/A')}")
    print(f"💰 Cash: ${float(account.get('cash', 0)):.2f}")
    print(f"💰 Buying Power: ${float(account.get('buying_power', 0)):.2f}")
    print(f"💰 Portfolio Value: ${float(account.get('portfolio_value', 0)):.2f}")

# Get current positions
positions = live_exec.get_positions()
print(f"\n📊 Current Positions: {len(positions)}")
for sym, data in positions.items():
    print(f"  {sym}: {data['qty']} @ ${data['current']:.2f} | PnL: ${data['pnl']:.2f}")

# Run strategy engine cycle with live executor
print("\n🚀 Running Strategy Engine Cycle (LIVE)...")
# Create StrategyEngine with LIVE executor (not paper)
from strategy_engine import StrategyEngine
from strategy_bollinger import BollingerStrategy
from strategy_momentum import MomentumStrategy
from strategy_rsi import RSIStrategy
from strategy_first_hour import FirstHourBreakoutStrategy

# Use live executor for strategies
engine = StrategyEngine(live_exec)
# Register all strategies (CRITICAL STEP!)
engine.register_strategy('bollinger', BollingerStrategy())
engine.register_strategy('momentum', MomentumStrategy())
engine.register_strategy('rsi', RSIStrategy())
engine.register_strategy('first_hour', FirstHourBreakoutStrategy())
print(f"Strategies loaded: {list(engine.strategies.keys())}")

# Prepare prices for symbols we want to trade
watchlist = ['AMD', 'INTC', 'GOOGL', 'MSFT', 'AAPL']
prices = {}

# Add current positions
for sym, data in positions.items():
    prices[sym] = {'qty': data['qty'], 'current': data['current']}

# Add watchlist symbols (get current prices)
print(f"\n📈 Fetching prices for watchlist: {watchlist}")
for sym in watchlist:
    if sym not in prices:
        price = live_exec.get_current_price(sym)
        if price:
            prices[sym] = {'qty': 0, 'current': price}
            print(f"  {sym}: ${price:.2f}")
        else:
            print(f"  {sym}: Failed to fetch price")

print(f"\n🔍 Analyzing {len(prices)} symbols...")
executed = engine.run_cycle(prices)

print(f"\n✅ Executed {executed} trades")

# Check recent orders
orders = live_exec.get_orders(status='all', limit=5)
print(f"\n📋 Recent Orders ({len(orders)}):")
for order in orders[:5]:
    side = order.get('side', '?').upper()
    sym = order.get('symbol', '?')
    qty = order.get('qty', '?')
    status = order.get('status', '?')
    order_id = order.get('id', '?')[:8]
    print(f"  {side} {qty} {sym} | Status: {status} | ID: {order_id}")

print("\n" + "=" * 60)
print("✅ CYCLE COMPLETE")
print("=" * 60)