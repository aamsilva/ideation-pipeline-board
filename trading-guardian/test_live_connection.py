#!/usr/bin/env python3
"""
Test Live connection using the AlpacaExecutor class
"""
import sys
import os
sys.path.insert(0, "/Volumes/disco1tb/projects/trading-guardian/src")
from dotenv import load_dotenv
load_dotenv("/Volumes/disco1tb/projects/trading-guardian/.env")

from alpaca_executor import AlpacaExecutor

def test_live():
    print("🧪 Testing AlpacaExecutor Live Connection...")
    executor = AlpacaExecutor(use_live=True)
    account = executor.get_account()
    if account:
        print("✅ Live Account connection established successfully!")
        print(f"   Account Number: {account.get('account_number')}")
        print(f"   Cash: ${float(account.get('cash', 0)):.2f}")
        print(f"   Buying Power: ${float(account.get('buying_power', 0)):.2f}")
        print(f"   Portfolio Value: ${float(account.get('portfolio_value', 0)):.2f}")
    else:
        print("❌ Failed to connect to Live Account.")

if __name__ == "__main__":
    test_live()
