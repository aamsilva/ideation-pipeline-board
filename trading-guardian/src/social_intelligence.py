#!/usr/bin/env python3
"""
Social Intelligence Module - Real-Time Sentiment Harvester
Captures real-time stock sentiment from public news RSS feeds and processes it via LLM.
Part of Level 5 Sovereign Agentic Upgrade for Trading Guardian.
"""

import os
import json
import logging
from typing import Dict, List
from dexter_tools import analyze_with_llm

logger = logging.getLogger("SocialIntelligence")


class SocialIntelligence:
    """
    Real-time Social & Media Intelligence harvester.
    Queries public news RSS feeds and computes raw sentiment index using LLM.
    """
    
    def __init__(self):
        self.sentiment_cache = {}

    def fetch_rss_headlines(self, ticker: str) -> List[str]:
        """Fetch latest stock news headlines from Google News RSS feed"""
        import urllib.request
        import xml.etree.ElementTree as ET
        
        url = f"https://news.google.com/rss/search?q={ticker}+stock+sentiment&hl=en-US&gl=US&ceid=US:en"
        headlines = []
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read()
                root = ET.fromstring(xml_data)
                for item in root.findall(".//item"):
                    title = item.find("title")
                    if title is not None:
                        headlines.append(title.text)
        except Exception as e:
            logger.warning(f"⚠️ RSS headline fetch failed for {ticker}: {e}")
        return headlines[:15] # Top 15 headlines

    def harvest_sentiment(self, ticker: str) -> Dict:
        """
        Performs real-time sentiment harvesting for a ticker using RSS feeds.
        Computes score, bias, and panic index.
        """
        logger.info(f"📡 Harvesting real-time social sentiment for {ticker}...")
        
        headlines = self.fetch_rss_headlines(ticker)
        
        if not headlines:
            logger.warning(f"⚠️ No headlines gathered for {ticker}. Returning neutral default.")
            return {
                "ticker": ticker,
                "score": 0.0,
                "bias": "NEUTRAL",
                "panic_level": 3,
                "summary": "No recent sentiment feed available."
            }
            
        logger.info(f"📰 Gathered {len(headlines)} fresh articles/discussions for {ticker}")
        
        prompt = f"""
TASK: Analyze the current SOCIAL AND MEDIA SENTIMENT for the stock ticker: {ticker}.
SOURCES: Recent news headlines and market discussions.

GATHERED HEADLINES:
{chr(10).join(f'- {h}' for h in headlines)}

INSTRUCTIONS:
1. Identify if the general sentiment is: BULLISH, BEARISH, or NEUTRAL.
2. Calculate a precise score from -1.0 (extremely bearish) to 1.0 (extremely bullish).
3. Compute a panic_level index from 0 (extreme euphoria/FOMO) to 10 (extreme panic/sell-off).
4. Summarize the outlook in 1 concise sentence.

RETURN ONLY a JSON object with:
- "ticker": "{ticker}"
- "score": (float between -1.0 and 1.0)
- "bias": (BULLISH/BEARISH/NEUTRAL)
- "top_themes": [list of main discussion points, max 3]
- "panic_level": (integer 0-10)
- "summary": (Short 1-sentence social outlook)
"""
        try:
            analysis_json = analyze_with_llm(prompt)
            # JSON cleaning
            analysis_json = analysis_json.strip().replace("```json", "").replace("```", "")
            sentiment = json.loads(analysis_json)
            
            # Cache the sentiment
            self.sentiment_cache[ticker] = sentiment
            logger.info(f"✅ Real-Time sentiment computed for {ticker}: {sentiment.get('bias')} (Score: {sentiment.get('score')})")
            return sentiment
            
        except Exception as e:
            logger.error(f"❌ Social harvesting analysis failed for {ticker}: {e}")
            return {
                "ticker": ticker,
                "score": 0.0,
                "bias": "NEUTRAL",
                "panic_level": 3,
                "summary": "Failed to compile semantic index due to LLM error"
            }

    def get_global_heat(self) -> List[Dict]:
        """
        Identify top trending macro opportunities.
        """
        prompt = "Identify the top 3 trending stocks in technology/finance right now and why. Return as JSON list."
        try:
            result = analyze_with_llm(prompt)
            return json.loads(result.strip().replace("```json", "").replace("```", ""))
        except Exception as e:
            logger.warning(f"Global heat index failed: {e}")
            return []


if __name__ == "__main__":
    si = SocialIntelligence()
    print(si.harvest_sentiment("NVDA"))
