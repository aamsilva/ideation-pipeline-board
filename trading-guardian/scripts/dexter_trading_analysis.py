#!/usr/bin/env python3
"""
Dexter Finance Trading Quality Analysis
Avalia qualidade de trading LIVE vs PAPER usando Financial Datasets API
"""
import os
import json
import urllib.request
from datetime import datetime
from typing import Dict, List, Any

# Load .env
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

BASE_URL = "https://api.financialdatasets.ai"

def _get_api_key() -> str:
    api_key = os.getenv("FINANCIAL_DATASETS_API_KEY")
    if not api_key:
        raise ValueError("FINANCIAL_DATASETS_API_KEY not found in .env")
    return api_key

def make_request(endpoint: str, params: Dict = None) -> Dict:
    """Make authenticated request using x-api-key header (CRITICAL!)"""
    api_key = _get_api_key()
    url = f"{BASE_URL}{endpoint}"
    
    if params:
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query}"
    
    headers = {
        "x-api-key": api_key,  # CRITICAL: NOT Authorization: Bearer!
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())

def get_stock_snapshot(ticker: str) -> Dict:
    """Get current snapshot of stock"""
    try:
        result = make_request("/api/snapshot", {"ticker": ticker})
        return {
            "ticker": ticker,
            "price": result.get("snapshot", {}).get("price", 0),
            "change_pct": result.get("snapshot", {}).get("change_pct", 0),
            "volume": result.get("snapshot", {}).get("volume", 0),
            "status": "success"
        }
    except Exception as e:
        return {"ticker": ticker, "status": "error", "error": str(e)}

def get_insider_trades(ticker: str, limit: int = 10) -> Dict:
    """Get insider trading data - GOLD signal according to Dexter"""
    try:
        result = make_request("/api/insider-trades", {"ticker": ticker, "limit": limit})
        trades = result.get("insider_trades", [])
        return {
            "ticker": ticker,
            "trades": trades,
            "count": len(trades),
            "status": "success"
        }
    except Exception as e:
        return {"ticker": ticker, "status": "error", "error": str(e)}

def get_analyst_estimates(ticker: str) -> Dict:
    """Get analyst estimates"""
    try:
        result = make_request("/api/analyst-estimates", {"ticker": ticker})
        return {
            "ticker": ticker,
            "estimates": result.get("estimates", {}),
            "status": "success"
        }
    except Exception as e:
        return {"ticker": ticker, "status": "error", "error": str(e)}

def analyze_position_quality(position: Dict, snapshot: Dict, insider: Dict, estimates: Dict) -> Dict:
    """Analyze if a position is high quality"""
    ticker = position["symbol"]
    qty = position["qty"]
    entry_price = position.get("current", 0)  # This is actually current, not entry
    current_price = snapshot.get("price", entry_price)
    
    # Calculate P&L
    pnl = position.get("pnl", 0)
    pnl_pct = (pnl / (entry_price * qty)) * 100 if entry_price > 0 else 0
    
    # Insider sentiment
    insider_buy_count = 0
    insider_sell_count = 0
    if insider.get("status") == "success":
        for trade in insider.get("trades", []):
            if trade.get("transaction_type") == "BUY":
                insider_buy_count += 1
            elif trade.get("transaction_type") == "SELL":
                insider_sell_count += 1
    
    insider_sentiment = "NEUTRAL"
    if insider_buy_count > insider_sell_count:
        insider_sentiment = "BULLISH"
    elif insider_sell_count > insider_buy_count:
        insider_sentiment = "BEARISH"
    
    # Analyst sentiment
    analyst_sentiment = "NEUTRAL"
    if estimates.get("status") == "success":
        est = estimates.get("estimates", {})
        if est.get("strong_buy") or est.get("buy"):
            analyst_sentiment = "BULLISH"
        elif est.get("sell") or est.get("strong_sell"):
            analyst_sentiment = "BEARISH"
    
    # Overall quality score
    score = 50  # Base score
    
    if pnl > 0:
        score += 20
    else:
        score -= 20
    
    if insider_sentiment == "BULLISH":
        score += 15
    elif insider_sentiment == "BEARISH":
        score -= 15
    
    if analyst_sentiment == "BULLISH":
        score += 15
    elif analyst_sentiment == "BEARISH":
        score -= 15
    
    if snapshot.get("change_pct", 0) > 0:
        score += 10
    
    return {
        "ticker": ticker,
        "qty": qty,
        "entry_price": entry_price,
        "current_price": current_price,
        "pnl": pnl,
        "pnl_pct": round(pnl_pct, 2),
        "insider_sentiment": insider_sentiment,
        "analyst_sentiment": analyst_sentiment,
        "quality_score": min(max(score, 0), 100),
        "recommendation": "HOLD"
    }

def main():
    print("=" * 70)
    print("🏦 DEXTER FINANCE - TRADING QUALITY ANALYSIS")
    print("=" * 70)
    print()
    
    # Load guardian state
    state_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'guardian_state.json')
    with open(state_path) as f:
        state = json.load(f)
    
    # Analyze LIVE positions
    print("🔴 LIVE PORTFOLIO ANALYSIS")
    print("-" * 70)
    live_positions = state["live"]["positions"]
    live_analyses = []
    
    for pos in live_positions:
        ticker = pos["symbol"]
        print(f"\n📊 Analyzing {ticker}...")
        
        # Fetch data from Dexter/Financial Datasets
        snapshot = get_stock_snapshot(ticker)
        insider = get_insider_trades(ticker, limit=5)
        estimates = get_analyst_estimates(ticker)
        
        analysis = analyze_position_quality(pos, snapshot, insider, estimates)
        live_analyses.append(analysis)
        
        print(f"   P&L: ${analysis['pnl']:.2f} ({analysis['pnl_pct']:.2f}%)")
        print(f"   Insider: {analysis['insider_sentiment']}")
        print(f"   Analyst: {analysis['analyst_sentiment']}")
        print(f"   Quality Score: {analysis['quality_score']}/100")
    
    # Analyze PAPER positions
    print("\n" + "=" * 70)
    print("📝 PAPER PORTFOLIO ANALYSIS")
    print("-" * 70)
    paper_positions = state["paper"]["positions"]
    paper_analyses = []
    
    for pos in paper_positions:
        ticker = pos["symbol"]
        print(f"\n📊 Analyzing {ticker}...")
        
        # Fetch data from Dexter/Financial Datasets
        snapshot = get_stock_snapshot(ticker)
        insider = get_insider_trades(ticker, limit=5)
        estimates = get_analyst_estimates(ticker)
        
        analysis = analyze_position_quality(pos, snapshot, insider, estimates)
        paper_analyses.append(analysis)
        
        print(f"   P&L: ${analysis['pnl']:.2f} ({analysis['pnl_pct']:.2f}%)")
        print(f"   Insider: {analysis['insider_sentiment']}")
        print(f"   Analyst: {analysis['analyst_sentiment']}")
        print(f"   Quality Score: {analysis['quality_score']}/100")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 QUALITY SUMMARY")
    print("-" * 70)
    
    live_avg_score = sum(a["quality_score"] for a in live_analyses) / len(live_analyses) if live_analyses else 0
    paper_avg_score = sum(a["quality_score"] for a in paper_analyses) / len(paper_analyses) if paper_analyses else 0
    
    live_total_pnl = sum(a["pnl"] for a in live_analyses)
    paper_total_pnl = sum(a["pnl"] for a in paper_analyses)
    
    print(f"\n🔴 LIVE:")
    print(f"   Avg Quality Score: {live_avg_score:.1f}/100")
    print(f"   Total P&L: ${live_total_pnl:.2f}")
    print(f"   Positions: {len(live_analyses)}")
    
    print(f"\n📝 PAPER:")
    print(f"   Avg Quality Score: {paper_avg_score:.1f}/100")
    print(f"   Total P&L: ${paper_total_pnl:.2f}")
    print(f"   Positions: {len(paper_analyses)}")
    
    print("\n" + "=" * 70)
    print("🎯 RECOMMENDATION")
    print("-" * 70)
    
    if live_avg_score > paper_avg_score:
        print("✅ LIVE portfolio has HIGHER quality picks")
    elif paper_avg_score > live_avg_score:
        print("✅ PAPER portfolio has HIGHER quality picks")
    else:
        print("➡️ Both portfolios have SIMILAR quality")
    
    print(f"\n📈 Best LIVE position: {max(live_analyses, key=lambda x: x['quality_score'])['ticker'] if live_analyses else 'N/A'}")
    print(f"📈 Best PAPER position: {max(paper_analyses, key=lambda x: x['quality_score'])['ticker'] if paper_analyses else 'N/A'}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
