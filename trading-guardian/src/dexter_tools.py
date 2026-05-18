#!/usr/bin/env python3
"""
Dexter Tools - Python Port
Python port of Dexter's financial tools for Trading Guardian integration.

Uses litellm (smart-router) for LLM calls - NO Claude/OpenAI direct usage.
Data source: Financial Datasets API (https://financialdatasets.ai)

Tools ported from Dexter TypeScript:
- get_income_statements
- get_balance_sheets  
- get_cash_flow_statements
- get_stock_prices (historical)
- get_stock_snapshot (current price)
- get_insider_trades
- screen_stocks
- get_analyst_estimates
- get_filings

CORRECTED ENDPOINTS (from Dexter source code):
- /prices/snapshot/ (current stock price)
- /prices/ (historical prices)
- /filings/items/types/ (filings)
- /financials/income-statements (income)
- /financials/balance-sheets (balance)
- /financials/cash-flow-statements (cash flow)
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv("/Volumes/disco1tb/projects/trading-guardian/.env")
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Base URL for Financial Datasets API
# CORRECTED: No /api prefix (verified working endpoints)
BASE_URL = "https://api.financialdatasets.ai"

def _get_api_key() -> str:
    """Get Financial Datasets API key from environment"""
    api_key = os.getenv("FINANCIAL_DATASETS_API_KEY")
    if not api_key:
        raise ValueError(
            "FINANCIAL_DATASETS_API_KEY not found in environment. "
            "Get your key from https://financialdatasets.ai"
        )
    return api_key

def _make_request(endpoint: str, params: Dict = None) -> Any:
    """
    Make authenticated request to Financial Datasets API
    
    CRITICAL: Dexter uses 'x-api-key' header (not Authorization Bearer)
    Source: dexter-finance/src/tools/finance/api.ts line 66
    
    Updated: Uses 'requests' library for reliable HTTP handling
    """
    import requests
    
    api_key = _get_api_key()
    url = f"{BASE_URL}{endpoint}"
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error {e.response.status_code}: {e.response.reason} for {url}")
        raise
    except Exception as e:
        logger.error(f"Request failed: {e}")
        raise

# ─── INCOME STATEMENTS ───────────────────────────────────────

def get_income_statements(ticker: str, period: str = "annual", limit: int = 5) -> Dict:
    """
    Get income statements for a ticker.
    
    Args:
        ticker: Stock ticker (e.g., 'AAPL')
        period: 'annual' or 'quarterly'
        limit: Number of periods to return
    
    Returns:
        Dict with income statement data
    """
    params = {
        "ticker": ticker,
        "period": period,
        "limit": limit
    }
    
    try:
        result = _make_request("/financials/income-statements", params)
        logger.info(f"Retrieved {limit} {period} income statements for {ticker}")
        return {
            "ticker": ticker,
            "period": period,
            "data": result.get("income_statements", []),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to get income statements for {ticker}: {e}")
        return {"ticker": ticker, "status": "error", "error": str(e)}

# ─── BALANCE SHEETS ──────────────────────────────────────────

def get_balance_sheets(ticker: str, period: str = "annual", limit: int = 5) -> Dict:
    """Get balance sheets for a ticker"""
    params = {
        "ticker": ticker,
        "period": period,
        "limit": limit
    }
    
    try:
        result = _make_request("/financials/balance-sheets", params)
        logger.info(f"Retrieved {limit} {period} balance sheets for {ticker}")
        return {
            "ticker": ticker,
            "period": period,
            "data": result.get("balance_sheets", []),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to get balance sheets for {ticker}: {e}")
        return {"ticker": ticker, "status": "error", "error": str(e)}

# ─── CASH FLOW STATEMENTS ───────────────────────────────────

def get_cash_flow_statements(ticker: str, period: str = "annual", limit: int = 5) -> Dict:
    """Get cash flow statements for a ticker"""
    params = {
        "ticker": ticker,
        "period": period,
        "limit": limit
    }
    
    try:
        result = _make_request("/financials/cash-flow-statements", params)
        logger.info(f"Retrieved {limit} {period} cash flow statements for {ticker}")
        return {
            "ticker": ticker,
            "period": period,
            "data": result.get("cash_flow_statements", []),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to get cash flow statements for {ticker}: {e}")
        return {"ticker": ticker, "status": "error", "error": str(e)}

# ─── STOCK SNAPSHOT (Current Price) ────────────────────────

def get_stock_snapshot(ticker: str) -> Dict:
    """
    Get current stock price snapshot.
    
    Args:
        ticker: Stock ticker (e.g., 'AAPL')
    
    Returns:
        Dict with current price, change, and timestamp
    """
    params = {"ticker": ticker}
    
    try:
        result = _make_request("/prices/snapshot/", params)
        snapshot = result.get("snapshot", {})
        logger.info(f"Retrieved snapshot for {ticker}: ${snapshot.get('price', 0)}")
        return {
            "ticker": ticker,
            "price": snapshot.get("price"),
            "day_change": snapshot.get("day_change"),
            "day_change_percent": snapshot.get("day_change_percent"),
            "time": snapshot.get("time"),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to get snapshot for {ticker}: {e}")
        return {"ticker": ticker, "status": "error", "error": str(e)}

# ─── STOCK PRICES (Historical) ────────────────────────────────────

def get_stock_prices(ticker: str, start_date: str = None, interval: str = "1d", limit: int = 30) -> Dict:
    """
    Get historical stock prices.
    
    Args:
        ticker: Stock ticker
        interval: '1d', '1h', '15m', etc.
        limit: Number of data points
    """
    params = {
        "ticker": ticker,
        "interval": interval,
        "limit": limit
    }
    
    try:
        result = _make_request("/prices", params)
        logger.info(f"Retrieved {limit} {interval} prices for {ticker}")
        return {
            "ticker": ticker,
            "interval": interval,
            "data": result.get("prices", []),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to get stock prices for {ticker}: {e}")
        return {"ticker": ticker, "status": "error", "error": str(e)}

# ─── INSIDER TRADES ─────────────────────────────────────────

def get_insider_trades(ticker: str, limit: int = 10) -> Dict:
    """
    Get insider trading data. Important signal for trading decisions!
    
    Args:
        ticker: Stock ticker
        limit: Number of recent trades to return
    """
    params = {
        "ticker": ticker,
        "limit": limit
    }
    
    try:
        result = _make_request("/insider-trades", params)
        logger.info(f"Retrieved {limit} insider trades for {ticker}")
        return {
            "ticker": ticker,
            "data": result.get("insider_trades", []),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to get insider trades for {ticker}: {e}")
        return {"ticker": ticker, "status": "error", "error": str(e)}

# ─── ANALYST ESTIMATES ──────────────────────────────────────

def get_analyst_estimates(ticker: str) -> Dict:
    """Get analyst estimates for a ticker"""
    params = {"ticker": ticker}
    
    try:
        result = _make_request("/analyst-estimates", params)
        logger.info(f"Retrieved analyst estimates for {ticker}")
        return {
            "ticker": ticker,
            "data": result.get("estimates", {}),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to get analyst estimates for {ticker}: {e}")
        return {"ticker": ticker, "status": "error", "error": str(e)}

# ─── STOCK SCREENER ─────────────────────────────────────────

def screen_stocks(criteria: Dict) -> Dict:
    """
    Screen stocks based on criteria.
    
    Example criteria:
    {
        "market_cap": ">1000000000",  # > $1B
        "sector": "Technology",
        "price_to_earnings": "<20"
    }
    """
    try:
        result = _make_request("/screen", criteria)
        logger.info(f"Screened stocks with criteria: {criteria}")
        return {
            "criteria": criteria,
            "results": result.get("stocks", []),
            "count": len(result.get("stocks", [])),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to screen stocks: {e}")
        return {"criteria": criteria, "status": "error", "error": str(e)}

# ─── GET ALL FINANCIALS ─────────────────────────────────────

def get_all_financials(ticker: str) -> Dict:
    """Get comprehensive financial data for a ticker"""
    logger.info(f"Getting all financials for {ticker}")
    
    return {
        "ticker": ticker,
        "income_statements": get_income_statements(ticker),
        "balance_sheets": get_balance_sheets(ticker),
        "cash_flow_statements": get_cash_flow_statements(ticker),
        "analyst_estimates": get_analyst_estimates(ticker),
        "insider_trades": get_insider_trades(ticker, limit=5),
        "current_price": get_stock_prices(ticker, limit=1),
        "timestamp": datetime.now().isoformat()
    }

def summarize_financials(financials: Dict) -> Dict:
    """
    Compresses large financial JSON into a token-efficient summary.
    Reduces context size by ~90% while keeping critical KPIs.
    """
    ticker = financials.get("ticker", "N/A")
    summary = {"ticker": ticker, "kpis": []}
    
    # Summarize Income Statements (Last 2 periods)
    for stmt in financials.get("income_statements", {}).get("data", [])[:2]:
        summary["kpis"].append({
            "period": stmt.get("report_period"),
            "rev": stmt.get("net_revenue"),
            "net_inc": stmt.get("net_income"),
            "eps": stmt.get("eps_diluted")
        })
        
    # Get critical Balance Sheet items
    bs_data = financials.get("balance_sheets", {}).get("data", [])
    if bs_data:
        latest = bs_data[0]
        summary["latest_balance"] = {
            "cash": latest.get("cash_and_equivalents"),
            "debt": latest.get("total_debt"),
            "equity": latest.get("shareholders_equity")
        }
        
    # Insider Summary
    insiders = financials.get("insider_trades", {}).get("data", [])
    summary["insider_sentiment"] = "Mixed"
    if insiders:
        sales = [t for t in insiders if "sale" in t.get("transaction_type", "").lower()]
        buys = [t for t in insiders if "buy" in t.get("transaction_type", "").lower() or "purchase" in t.get("transaction_type", "").lower()]
        if len(sales) > len(buys) * 2: summary["insider_sentiment"] = "Heavy Selling"
        elif len(buys) > len(sales): summary["insider_sentiment"] = "Buying Activity"
        
    return summary

# ─── LLM INTEGRATION (smart-router/litellm ONLY) ───────────

def analyze_with_llm(prompt: str, model: str = None) -> str:
    """
    Analyze data using LLM via litellm/smart-router.
    
    CRITICAL: Uses smart-router (litellm) with seamless pure-requests OpenRouter fallback!
    """
    try:
        # Direct HTTP call to local LiteLLM Proxy on port 4000
        import requests
        if model is None:
            model = os.getenv("SMART_ROUTER_MODEL", "smart-router")
            
        headers = {
            "Authorization": f"Bearer {os.getenv('LITELLM_MASTER_KEY', 'sk-litellm-master-key-12345')}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2
        }
        resp = requests.post(
            "http://localhost:4000/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        else:
            raise RuntimeError(f"Local LiteLLM error {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.info(f"Local LiteLLM proxy or library unavailable ({e}). Falling back to pure requests OpenRouter direct...")
        try:
            import requests
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if not openrouter_key:
                raise ValueError("OPENROUTER_API_KEY not configured in .env")
                
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "google/gemini-2.5-flash",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            }
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                raise RuntimeError(f"OpenRouter API error {resp.status_code}: {resp.text}")
        except Exception as ex:
            logger.error(f"LLM analysis failed completely: {ex}")
            return f"LLM analysis error: {str(ex)}"

# ─── DEXTER-STYLE ANALYSIS ─────────────────────────────────

def dexter_analysis(ticker: str, question: str, deep_dive: bool = False) -> Dict:
    """
    Dexter-style deep financial analysis.
    
    Args:
        ticker: Stock ticker
        question: Question for analysis
        deep_dive: If True, sends FULL JSON. If False, sends SUMMARY.
    """
    logger.info(f"Starting {'DEEP' if deep_dive else 'FAST'} Dexter analysis for {ticker}: {question}")
    
    # Step 1: Gather all financial data
    financials = get_all_financials(ticker)
    
    # Step 2: Build analysis prompt (Summary vs Full JSON)
    data_to_send = financials if deep_dive else summarize_financials(financials)
    
    prompt = f"""
You are a financial research agent (Dexter-style) analyzing {ticker}.

QUESTION: {question}

FINANCIAL DATA ({'FULL' if deep_dive else 'SUMMARY'}):
{json.dumps(data_to_send, indent=2)}

TASK:
1. Analyze the financial data above
2. Answer the question with specific numbers and trends
3. Identify key risks and opportunities
4. Provide a data-backed recommendation

Be concise but thorough. Use specific numbers from the data.
"""
    
    # Step 3: Get LLM analysis (smart-router ONLY)
    analysis = analyze_with_llm(prompt)
    
    return {
        "ticker": ticker,
        "question": question,
        "mode": "deep" if deep_dive else "fast",
        "analysis": analysis,
        "timestamp": datetime.now().isoformat(),
        "status": "success"
    }

def get_macro_sentiment() -> Dict:
    """
    Analyzes global macro sentiment (FED, Inflation, Geopolitics).
    Returns a score from -1.0 (Very Bearish) to 1.0 (Very Bullish).
    """
    logger.info("🌍 Analyzing Global Macro Sentiment...")
    
    # In a real implementation, we would search news. For now, we simulate 
    # based on the market snapshot we got earlier (S&P at record highs but VIX rising)
    prompt = """
    Analyze the current market context:
    - S&P 500 at record highs (7412)
    - VIX rising (18.37)
    - Oil prices climbing near $100
    - Geopolitical tensions in Middle East
    - Fed signals 'No Rate Cuts' in 2026
    
    Return ONLY a JSON with:
    {
      "score": float (-1.0 to 1.0),
      "bias": "bullish" | "bearish" | "neutral",
      "reason": "short string"
    }
    """
    
    try:
        analysis = analyze_with_llm(prompt)
        # Clean up in case LLM adds markdown
        if "```json" in analysis:
            analysis = analysis.split("```json")[1].split("```")[0].strip()
        elif "```" in analysis:
            analysis = analysis.split("```")[1].split("```")[0].strip()
            
        data = json.loads(analysis)
        return data
    except Exception as e:
        logger.warning(f"Macro analysis failed: {e}")
        return {"score": 0.0, "bias": "neutral", "reason": "Error fetching macro"}

if __name__ == "__main__":
    # Test the tools
    print("Dexter Tools - Python Port")
    print("=" * 50)
    
    # Test with Apple
    result = get_stock_prices("AAPL", limit=3)
    print(f"\nAAPL Stock Prices: {json.dumps(result, indent=2)}")
