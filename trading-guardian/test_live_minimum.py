#!/usr/bin/env python3
"""
Live Trading Test - Minimum $1 Buy/Sell
Uses same credentials as previous successful live order
"""
import alpaca_trade_api as tradeapi
import time
import os

# Live credentials (from earlier successful test)
LIVE_KEY = "AKAHSR7C6XH7OAR7L6EJYVCRRK"
LIVE_SECRET = "DjM8rMUbwHnGbkUJJoTt5BpAiujuQ39vzpxFosm2YEac"
LIVE_BASE = "https://api.alpaca.markets"

def test_live_minimum():
    print("🔴 LIVE ACCOUNT TEST - MINIMUM $1 TRADE")
    print("=" * 50)
    
    api = tradeapi.REST(LIVE_KEY, LIVE_SECRET, LIVE_BASE, api_version='v2')
    
    # Check account
    account = api.get_account()
    cash = float(account.cash)
    buying_power = float(account.buying_power)
    print(f"💰 Cash: ${cash:.2f}")
    print(f"📈 Buying Power: ${buying_power:.2f}")
    
    if buying_power < 1.0:
        print("❌ Insufficient buying power for $1 trade")
        return
    
    # Buy $1 of MSFT (fractional)
    print("\n🛒 Placing LIVE BUY order: $1 MSFT...")
    try:
        buy_order = api.submit_order(
            symbol="MSFT",
            notional=1.0,  # $1 minimum
            side="buy",
            type="market",
            time_in_force="day"
        )
        print(f"✅ Buy Order ID: {buy_order.id}")
        print(f"   Status: {buy_order.status}")
        
        # Wait for fill
        print("⏳ Waiting 15s for order fill...")
        time.sleep(15)
        
        buy_order = api.get_order(buy_order.id)
        print(f"📋 Buy Order Status: {buy_order.status}")
        
        if buy_order.status == "filled":
            print(f"   Filled at: ${float(buy_order.filled_avg_price):.2f}")
            print(f"   Qty: {buy_order.filled_qty}")
            
            # Now sell it
            print("\n💸 Placing LIVE SELL order: $1 MSFT...")
            sell_order = api.submit_order(
                symbol="MSFT",
                notional=1.0,
                side="sell",
                type="market",
                time_in_force="day"
            )
            print(f"✅ Sell Order ID: {sell_order.id}")
            time.sleep(15)
            
            sell_order = api.get_order(sell_order.id)
            print(f"📋 Sell Order Status: {sell_order.status}")
            if sell_order.status == "filled":
                print(f"   Filled at: ${float(sell_order.filled_avg_price):.2f}")
                print("✅ LIVE BUY+SELL CYCLE COMPLETED SUCCESSFULLY")
            else:
                print(f"⚠️ Sell order not filled: {sell_order.status}")
        else:
            print(f"⚠️ Buy order not filled: {buy_order.status}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_live_minimum()
