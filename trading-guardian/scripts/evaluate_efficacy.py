#!/usr/bin/env python3
"""
Trading Guardian - Efficacy Evaluator
Demonstrates the concrete difference between Pure Technical and Sentiment-Enhanced Trading
using today's live market data and real headlines.
"""

import os
import sys
import json
from datetime import datetime

# Setup path imports
sys.path.insert(0, "/Volumes/disco1tb/projects/trading-guardian/src")
from dotenv import load_dotenv
load_dotenv("/Volumes/disco1tb/projects/trading-guardian/.env")

from alpaca_executor import AlpacaExecutor
from social_intelligence import SocialIntelligence
from strategy_rsi import RSIStrategy
from strategy_bollinger import BollingerStrategy


def evaluate_efficacy():
    print("=" * 70)
    print("🛡️  TRADING GUARDIAN: LIVE EFFICACY EVALUATION REPORT")
    print(f"Date/Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    executor = AlpacaExecutor(use_live=False)
    social_intel = SocialIntelligence()
    
    rsi_strategy = RSIStrategy()
    rsi_strategy.client = executor
    
    bb_strategy = BollingerStrategy()
    bb_strategy.client = executor
    
    tickers = ["NVDA", "AAPL", "AMD", "TSLA"]
    
    for ticker in tickers:
        print(f"\n🔍 Analyzing: {ticker}")
        print("-" * 50)
        
        # 1. Fetch current price and bars
        price = executor.get_current_price(ticker)
        if not price:
            print(f"⚠️ Could not fetch price for {ticker}")
            continue
            
        print(f"💵 Current Price: ${price:.2f}")
        
        # 2. Get technical signals
        rsi = rsi_strategy.calculate_rsi(ticker)
        bb = executor.calculate_bollinger_bands(ticker)
        
        technical_signal = "HOLD"
        technical_reason = "No signal"
        
        # Simulate strategy logic
        if rsi and rsi <= rsi_strategy.oversold:
            technical_signal = "BUY"
            technical_reason = f"RSI is oversold ({rsi:.1f} <= {rsi_strategy.oversold})"
        elif rsi and rsi >= rsi_strategy.overbought:
            technical_signal = "SELL"
            technical_reason = f"RSI is overbought ({rsi:.1f} >= {rsi_strategy.overbought})"
        elif bb and price <= bb['lower'] * 1.002:
            technical_signal = "BUY"
            technical_reason = f"Price near Bollinger lower band (${bb['lower']:.2f})"
        elif bb and price >= bb['upper'] * 0.998:
            technical_signal = "SELL"
            technical_reason = f"Price near Bollinger upper band (${bb['upper']:.2f})"
            
        rsi_str = f"{rsi:.1f}" if rsi else "N/A"
        bb_str = f"${bb['upper']:.2f}/${bb['lower']:.2f}" if bb else "N/A"
        print(f"📊 Pure Technical Metric: RSI={rsi_str}, Bollinger Upper/Lower={bb_str}")
        print(f"⚙️  Pure Technical Decision: {technical_signal} ({technical_reason})")
        
        # 3. Fetch live RSS social sentiment
        print("📡 Gathering live news and media headlines...")
        headlines = social_intel.fetch_rss_headlines(ticker)
        for h in headlines[:3]:
            print(f"  - {h}")
            
        sentiment = social_intel.harvest_sentiment(ticker)
        score = sentiment.get("score", 0.0)
        bias = sentiment.get("bias", "NEUTRAL")
        panic = sentiment.get("panic_level", 3)
        summary = sentiment.get("summary", "")
        
        print(f"🧠 Media Sentiment Score: {score:+.2f} ({bias}) | Panic Index: {panic}/10")
        print(f"📝 Sentiment Summary: {summary}")
        
        # 4. Apply Sentiment Modification Logic
        final_decision = technical_signal
        final_confidence = 0.75
        adjustment_reason = "No adjustment needed"
        
        if technical_signal == "BUY":
            if score < -0.4:
                final_decision = "HOLD (VETOED)"
                adjustment_reason = f"Technical BUY vetoed! Social sentiment is in PANIC mode ({score:.2f}) with high panic level ({panic}/10). Saved from buying a falling knife."
            elif score > 0.4:
                final_decision = "BUY (BOOSTED)"
                final_confidence *= 1.15
                adjustment_reason = f"Strong media backing ({score:.2f}). Confidence increased to {final_confidence:.2f}."
        elif technical_signal == "SELL":
            if score > 0.4:
                final_decision = "HOLD (PRESERVED)"
                adjustment_reason = f"Technical SELL vetoed! Stock shows extremely strong positive social momentum ({score:.2f}). Let profits run."
            elif score < -0.4:
                final_decision = "SELL (CONFIRMED)"
                final_confidence *= 1.15
                adjustment_reason = f"Media panic confirms technical breakdown ({score:.2f}). Confidence boosted."
                
        print(f"\n🛡️  SENTINEL DECISION COMPARISON FOR {ticker}:")
        print(f"   [OLD WAY] Pure Technical: {technical_signal} (Confidence: 0.75)")
        conf_str = f"{final_confidence:.2f}" if "HOLD" not in final_decision else "N/A"
        print(f"   [NEW WAY] Sentiment-Enhanced: {final_decision} (Confidence: {conf_str})")
        print(f"   💡 Efficacy Reason: {adjustment_reason}")
        print("=" * 70)


if __name__ == "__main__":
    evaluate_efficacy()
