#!/usr/bin/env python3
"""
Trading Guardian - Multi-Agent Swarm Orchestrator
Coordinates autonomous micro-agents in parallel without blocking main thread.
"""

import asyncio
import logging
import os
from typing import Dict, List
from risk_officer import RiskOfficer
from social_intelligence import SocialIntelligence
from alpaca_executor import AlpacaExecutor

logger = logging.getLogger("AgentSwarm")

class AgentSwarm:
    def __init__(self, check_interval_sec: int = 5):
        self.check_interval_sec = check_interval_sec
        self.risk_officer = RiskOfficer()
        self.social_intel = SocialIntelligence()
        self.alpaca_executor = AlpacaExecutor(use_live=False)
        self.running = False
        
    async def start(self):
        """Starts the parallel micro-agents in the swarm"""
        self.running = True
        logger.info("🐝 Agent Swarm Orchestrator starting...")
        
        # Spawn micro-agents concurrently
        asyncio.create_task(self.run_risk_officer_loop())
        asyncio.create_task(self.run_sentiment_scout_loop())
        
        logger.info("   ✅ Risk Officer & Sentiment Scout spawned as background tasks.")

    async def stop(self):
        """Stops all running agents"""
        self.running = False
        logger.info("🛑 Stopping Agent Swarm...")

    async def run_risk_officer_loop(self):
        """Micro-agent that monitors risk and stop-losses continuously in real-time"""
        logger.info("🛡️ Risk Officer Agent active")
        while self.running:
            try:
                # Fetch fresh account and positions data
                account_info = self.alpaca_executor.get_account()
                positions = self.alpaca_executor.get_positions()
                
                if account_info and positions:
                    healthy, reason, symbols_to_liquidate = self.risk_officer.check_portfolio_limits(
                        positions, account_info
                    )
                    if not healthy:
                        logger.critical(f"🚨 Risk Officer detected violation: {reason}")
                        self.risk_officer.execute_emergency_liquidation(symbols_to_liquidate)
            except Exception as e:
                logger.error(f"⚠️ Risk Officer loop error: {e}")
                
            await asyncio.sleep(self.check_interval_sec)

    async def run_sentiment_scout_loop(self):
        """Micro-agent that updates social sentiment scores periodically in the background"""
        logger.info("📡 Sentiment Scout Agent active")
        # Watchlist symbols to scan
        symbols = ["AAPL", "AMD", "NVDA", "MSFT", "GOOGL"]
        while self.running:
            for sym in symbols:
                if not self.running:
                    break
                try:
                    logger.info(f"🔍 Sentiment Scout scanning background news for {sym}...")
                    sentiment = self.social_intel.harvest_sentiment(sym)
                    score = sentiment.get("score", 0.0)
                    logger.info(f"   ✅ Scout updated {sym} sentiment score: {score}")
                except Exception as e:
                    logger.warning(f"⚠️ Sentiment Scout failed to scan {sym}: {e}")
                # Rate limit scans to protect API usage
                await asyncio.sleep(60) 
            
            # Rest for 30 minutes between cycles
            await asyncio.sleep(1800)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    async def main():
        swarm = AgentSwarm()
        await swarm.start()
        await asyncio.sleep(15)  # Let it run for 15 seconds in test
        await swarm.stop()
        
    asyncio.run(main())
