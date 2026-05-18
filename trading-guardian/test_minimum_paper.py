#!/usr/bin/env python3
import alpaca_trade_api as tradeapi
from dotenv import load_dotenv
import os
import time

load_dotenv()

# Paper credentials (precisas de verificar se tens no .env)
PAPER_KEY = os.getenv("ALPACA_PAPER_API_KEY")
PAPER_SECRET = os.getenv("ALPACA_PAPER_SECRET_KEY")
PAPER_BASE = "https://paper-api.alpaca.markets"

def test_paper():
    if not PAPER_KEY or not PAPER_SECRET:
        print("❌ Paper credentials not found in .env")
        return
    
    api = tradeapi.REST(PAPER_KEY, PAPER_SECRET, PAPER_BASE, api_version='v2')
    
    # Check account
    account = api.get_account()
    print(f"📊 Paper Account: Cash=${float(account.cash):.2f}, Buying Power=${float(account.buying_power):.2f}")
    
    # Buy $1 of MSFT (fractional)
    print("\n🛒 Buying $1 MSFT on Paper...")
    try:
        order = api.submit_order(
            symbol="MSFT",
            notional=1.0,  # $1 minimum
            side="buy",
            type="market",
            time_in_force="day"
        )
        print(f"✅ Buy Order: ID={order.id}, Status={order.status}")
        time.sleep(10)
        
        # Check order
        order = api.get_order(order.id)
        print(f"📋 Order Status: {order.status}")
        
        if order.status == "filled":
            # Sell it immediately
            print("\n💸 Selling $1 MSFT on Paper...")
            sell_order = api.submit_order(
                symbol="MSFT",
                notional=1.0,
                side="sell",
                type="market",
                time_in_force="day"
            )
            print(f"✅ Sell Order: ID={sell_order.id}, Status={sell_order.status}")
            time.sleep(10)
            sell_order = api.get_order(sell_order.id)
            print(f"📋 Sell Status: {sell_order.status}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_paper()
