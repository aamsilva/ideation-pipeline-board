#!/usr/bin/env python3
"""
Live Execution Test - Submits a real queued order to the live exchange
and immediately cancels it to verify full round-trip buy/sell capabilities.
"""
import sys
import os
import time

sys.path.insert(0, "/Volumes/disco1tb/projects/trading-guardian/src")
from dotenv import load_dotenv
load_dotenv("/Volumes/disco1tb/projects/trading-guardian/.env")

from alpaca_executor import AlpacaExecutor

def test_live_trade():
    print("=" * 60)
    print("🧪 LIVE EXCHANGE ROUND-TRIP TRANSACTION TEST")
    print("=" * 60)
    
    executor = AlpacaExecutor(use_live=True)
    
    # Verify account cash
    account = executor.get_account()
    if not account:
        print("❌ Could not connect to Live account.")
        return
        
    cash = float(account.get('cash', 0))
    print(f"💰 Account Cash: ${cash:.2f}")
    
    # We will place a buy order for 1 share of INTC (or similar) since it is active.
    # Since the market is closed, the order will be successfully accepted and queued.
    # We will print the receipt, proving the broker accepted the order, and then cancel it.
    symbol = "F"
    print(f"\n🛒 Submitting real LIVE BUY order: 1 share of {symbol}...")
    
    try:
        # Submit the order
        order = executor.buy(symbol=symbol, qty=1.0)
        
        if order:
            order_id = order.get("id")
            status = order.get("status")
            print(f"✅ Order Accepted by Live Broker!")
            print(f"   Order ID: {order_id}")
            print(f"   Symbol: {order.get('symbol')}")
            print(f"   Side: {order.get('side').upper()}")
            print(f"   Qty: {order.get('qty')}")
            print(f"   Status: {status.upper()}")
            
            # Immediately cancel the queued order to prevent unintended execution tomorrow
            print(f"\n💸 Canceling the queued order {order_id}...")
            # We delete the order
            resp = executor.session.delete(f"{executor.base_url}/v2/orders/{order_id}")
            if resp.status_code == 204 or resp.status_code == 200:
                print("✅ Order cancelled successfully on Live exchange! Capital is safe.")
            else:
                print(f"⚠️ Cancel failed: {resp.status_code} - {resp.text}")
        else:
            print("❌ Order submission failed.")
    except Exception as e:
        print(f"❌ Exception occurred: {e}")

if __name__ == "__main__":
    test_live_trade()
