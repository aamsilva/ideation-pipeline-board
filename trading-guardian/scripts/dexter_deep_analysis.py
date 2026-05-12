#!/usr/bin/env python3
"""
Dexter Finance + LLM Analysis via smart-router
Avaliação profunda usando litellm (sem Claude/OpenAI direto)
"""
import os
import json
import urllib.request
from datetime import datetime

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

def _get_api_key():
    return os.getenv("FINANCIAL_DATASETS_API_KEY")

def make_request(endpoint, params=None):
    """Make request with x-api-key header (CRITICAL!)"""
    api_key = _get_api_key()
    url = f"{BASE_URL}{endpoint}"
    if params:
        query = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"{url}?{query}"
    
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())

def get_historical_prices(ticker, days=30):
    """Get historical price data"""
    try:
        result = make_request("/api/prices", {
            "ticker": ticker,
            "interval": "1d",
            "limit": days
        })
        return result.get("prices", [])
    except:
        return []

def analyze_with_llm(prompt):
    """Analyze using smart-router/litellm ONLY (per Dexter skill)"""
    try:
        import litellm
        
        # Use smart-router (configured in Hermes)
        model = os.getenv("SMART_ROUTER_MODEL", "smart-router")
        
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except ImportError:
        return "LLM analysis unavailable (litellm not installed)"
    except Exception as e:
        return f"LLM analysis error: {str(e)}"

def deep_analysis(ticker, position_data, portfolio_type):
    """Perform deep analysis using Dexter tools + LLM"""
    
    # Get historical data
    prices = get_historical_prices(ticker, days=14)
    
    # Calculate metrics
    if len(prices) >= 2:
        latest_price = prices[0].get("price", 0)
        oldest_price = prices[-1].get("price", 0)
        if oldest_price > 0:
            change_pct = ((latest_price - oldest_price) / oldest_price) * 100
        else:
            change_pct = 0
    else:
        change_pct = 0
    
    # Build LLM prompt
    prompt = f"""You are a financial analyst (Dexter-style) evaluating a trading position.

PORTFOLIO TYPE: {portfolio_type}
TICKER: {ticker}
QUANTITY: {position_data['qty']}
CURRENT PRICE: ${position_data['current']:.2f}
P&L: ${position_data['pnl']:.2f}
14-DAY CHANGE: {change_pct:.2f}%

TASK:
1. Rate this position quality (1-10 scale)
2. Identify key risks (be specific)
3. Identify opportunities (be specific)
4. Recommendation: STRONG BUY / BUY / HOLD / SELL / STRONG SELL
5. ONE actionable insight for the trader

Be concise. Use numbers. No fluff.
"""
    
    analysis = analyze_with_llm(prompt)
    
    return {
        "ticker": ticker,
        "portfolio_type": portfolio_type,
        "pnl": position_data['pnl'],
        "change_14d": change_pct,
        "analysis": analysis
    }

def main():
    print("=" * 70)
    print("🏦 DEXTER FINANCE + LLM DEEP ANALYSIS")
    print("=" * 70)
    print()
    
    # Load state
    state_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'guardian_state.json')
    with open(state_path) as f:
        state = json.load(f)
    
    # Analyze LIVE
    print("🔴 LIVE PORTFOLIO - DEEP ANALYSIS")
    print("-" * 70)
    live_results = []
    for pos in state["live"]["positions"]:
        print(f"\n📊 Analyzing {pos['symbol']}...")
        result = deep_analysis(pos["symbol"], pos, "LIVE")
        live_results.append(result)
        print(f"   14-day change: {result['change_14d']:.2f}%")
        print(f"   P&L: ${result['pnl']:.2f}")
        print(f"\n{result['analysis']}\n")
    
    # Analyze PAPER
    print("=" * 70)
    print("📝 PAPER PORTFOLIO - DEEP ANALYSIS")
    print("-" * 70)
    paper_results = []
    for pos in state["paper"]["positions"]:
        print(f"\n📊 Analyzing {pos['symbol']}...")
        result = deep_analysis(pos["symbol"], pos, "PAPER")
        paper_results.append(result)
        print(f"   14-day change: {result['change_14d']:.2f}%")
        print(f"   P&L: ${result['pnl']:.2f}")
        print(f"\n{result['analysis']}\n")
    
    # Summary
    print("=" * 70)
    print("📊 FINAL RECOMMENDATIONS")
    print("-" * 70)
    
    # Find best and worst
    all_results = live_results + paper_results
    if all_results:
        best = max(all_results, key=lambda x: x['pnl'])
        worst = min(all_results, key=lambda x: x['pnl'])
        
        print(f"\n✅ BEST POSITION: {best['ticker']} ({best['portfolio_type']}) - P&L: ${best['pnl']:.2f}")
        print(f"   Analysis: {best['analysis'][:200]}...")
        print(f"\n❌ WORST POSITION: {worst['ticker']} ({worst['portfolio_type']}) - P&L: ${worst['pnl']:.2f}")
        print(f"   Analysis: {worst['analysis'][:200]}...")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
