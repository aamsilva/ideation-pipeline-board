#!/usr/bin/env python3
"""
Test parameter optimization and genetic tuning on the active strategy files
"""
import sys
import os
import json

sys.path.insert(0, "/Volumes/disco1tb/projects/trading-guardian/src")
from dotenv import load_dotenv
load_dotenv("/Volumes/disco1tb/projects/trading-guardian/.env")

from autoresearch_engine import AutoResearchEngine

def test_optimization():
    print("=" * 60)
    print("🧬 WEEKLY PARAMETER OPTIMIZATION & BACKTEST VALIDATION TEST")
    print("=" * 60)
    
    engine = AutoResearchEngine()
    
    # Run parameter optimization for RSI strategy on AAPL
    result = engine.optimize_strategy_parameters("rsi", "AAPL")
    
    print("\n📊 Optimization Result:")
    print(json.dumps(result, indent=2))
    
    if result.get("success"):
        print("\n✅ Efficacious Parameter Tuning and Backtesting completed successfully!")
    else:
        print("\n❌ Parameter Tuning failed.")

if __name__ == "__main__":
    test_optimization()
