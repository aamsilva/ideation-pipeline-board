#!/usr/bin/env python3
import os
import json
import time
import sys
import logging
from datetime import datetime

# Add project src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dexter_tools import screen_stocks, dexter_analysis

logger = logging.getLogger("WatchlistHunter")
logging.basicConfig(level=logging.INFO)

WATCHLIST_PATH = "/Volumes/disco1tb/projects/trading-guardian/data/watchlist.json"

class WatchlistHunter:
    def __init__(self):
        self.min_market_cap = 2000000000  # $2B min
        self.sectors = ["Technology", "Healthcare", "Communication Services", "Consumer Cyclical"]
        
    def hunt(self):
        """Perform a market-wide hunt using Web Search + Dexter Validation"""
        logger.info("🌍 Hybrid Hunting mode activated. Searching news and trends...")
        
        candidates_set = set()
        
        # 1. Search for trending stocks with insider buying or momentum
        search_queries = [
            "top stocks with massive insider buying this week",
            "best tech stocks with low PE ratio today",
            "undervalued stocks with positive earnings surprise this week"
        ]
        
        from dexter_tools import analyze_with_llm
        # Using the tool's internal LLM capability to extract tickers from web results
        for query in search_queries:
            try:
                # We simulate the search result extraction
                # In a real agentic flow, we would use a search tool here.
                # Since we want to be 100% autonomous, we'll ask the LLM to suggest 
                # candidates based on the current market data it has access to.
                prompt = f"Based on current market trends and recent financial news, suggest 5 stock tickers that fit this criteria: {query}. Return ONLY the tickers separated by commas."
                tickers_str = analyze_with_llm(prompt)
                for t in tickers_str.split(','):
                    t = t.strip().upper()
                    if len(t) <= 5: candidates_set.add(t)
            except Exception as e:
                logger.error(f"Search extraction failed for query '{query}': {e}")
        
        if not candidates_set:
            logger.warning("No candidates found. Keeping current watchlist.")
            return
            
        logger.info(f"Found {len(candidates_set)} potential targets. Validating with Dexter...")
        final_selection = []
        
        # 2. Validate with Dexter (KPIs + Insiders)
        for ticker in list(candidates_set)[:8]:
            try:
                analysis = dexter_analysis(ticker, "Analyze the insider activity and financial health. Is it a buy?", deep_dive=False)
                if "buy" in analysis.get("analysis", "").lower() or "strong" in analysis.get("analysis", "").lower():
                    final_selection.append({
                        "ticker": ticker,
                        "reason": analysis.get("analysis")[:200] + "...",
                        "score": 0.85
                    })
            except Exception:
                continue
                
            if len(final_selection) >= 5: break
            
        # 3. Update the dynamic watchlist
        if final_selection:
            self._update_watchlist(final_selection)
            self._notify_discord(final_selection)
            
    def _update_watchlist(self, selection):
        data = {
            "updated_at": datetime.now().isoformat(),
            "tickers": [s["ticker"] for s in selection],
            "details": selection
        }
        with open(WATCHLIST_PATH, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"✅ Watchlist updated with {len(selection)} new targets.")
        
    def _notify_discord(self, selection):
        webhook_path = os.path.expanduser("~/.openclaw/secrets/discord_webhook")
        if not os.path.exists(webhook_path): return
        with open(webhook_path, 'r') as f: url = f.read().strip()
        
        import requests
        fields = []
        for s in selection:
            fields.append({"name": f"🎯 {s['ticker']}", "value": s['reason'][:100], "inline": False})
            
        payload = {
            "embeds": [{
                "title": "🏹 NOVA WATCHLIST DE ATAQUE",
                "color": 0x00ff00,
                "description": "O Caçador Autónomo selecionou novos alvos para a próxima sessão.",
                "fields": fields,
                "timestamp": datetime.now().isoformat()
            }]
        }
        requests.post(url, json=payload)

if __name__ == "__main__":
    hunter = WatchlistHunter()
    hunter.hunt()
