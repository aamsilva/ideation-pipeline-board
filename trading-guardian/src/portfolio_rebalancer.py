#!/usr/bin/env python3
"""
Sovereign Portfolio Rebalancer
Uses optimal Kelly Criterion, MPT, and Real-Time Sentiment for dynamic asset allocation.
"""

import os
import json
import logging
from typing import Dict, List, Any
import numpy as np

logger = logging.getLogger(__name__)

class PortfolioRebalancer:
    """Dynamically rebalances and calculates optimal sizing using Kelly Criterion and Sentiment"""
    
    def __init__(self, risk_aversion: float = 2.0, max_allocation_pct: float = 0.25):
        self.risk_aversion = risk_aversion
        self.max_allocation_pct = max_allocation_pct
        self.project_path = "/Volumes/disco1tb/projects/trading-guardian"
        
    def calculate_kelly_fraction(self, win_rate: float, win_loss_ratio: float, sentiment_score: float) -> float:
        """
        Calculates the fractional Kelly sizing adjusted by sentiment.
        f* = p - (1-p)/b
        where p is probability of win (win_rate), b is win/loss ratio.
        """
        if win_rate <= 0 or win_loss_ratio <= 0:
            return 0.0
            
        p = win_rate
        q = 1.0 - p
        b = win_loss_ratio
        
        # Standard Kelly
        kelly_f = p - (q / b)
        
        # Sentiment multiplier (scales Kelly up/down by up to 30%)
        # sentiment_score ranges from -1.0 to 1.0
        sentiment_adj = 1.0 + (sentiment_score * 0.3)
        adjusted_kelly = kelly_f * sentiment_adj
        
        # Apply fractional Kelly (half-Kelly) to prevent over-betting and ensure capital preservation
        half_kelly = adjusted_kelly / self.risk_aversion
        
        # Clamp to max allocation percentage
        final_fraction = max(0.0, min(self.max_allocation_pct, half_kelly))
        return final_fraction

    def get_optimal_allocations(self, watchlist: List[str], current_cash: float, sentiment_scores: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """
        Determines optimal cash and share sizing allocations for active watchlist targets.
        """
        allocations = {}
        
        # Retrieve historical strategy performance metrics to inform win rates
        # Defaults to highly conservative estimates if historical backtest stats are missing
        default_win_rate = 0.53
        default_win_loss_ratio = 1.25
        
        try:
            stats_path = f"{self.project_path}/data/backtest_stats.json"
            if os.path.exists(stats_path):
                with open(stats_path, "r") as f:
                    stats = json.load(f)
                    default_win_rate = stats.get("win_rate", default_win_rate)
                    default_win_loss_ratio = stats.get("win_loss_ratio", default_win_loss_ratio)
        except Exception as e:
            logger.warning(f"Failed to load historical stats: {e}")
            
        for symbol in watchlist:
            sentiment = sentiment_scores.get(symbol, 0.0)
            
            # Dynamic Win Rate adjustment based on real-time news sentiment
            # Strong Bullish sentiment (+1.0) boosts win rate by up to 5%
            adjusted_win_rate = default_win_rate + (sentiment * 0.05)
            adjusted_win_rate = max(0.4, min(0.8, adjusted_win_rate))
            
            kelly_fraction = self.calculate_kelly_fraction(adjusted_win_rate, default_win_loss_ratio, sentiment)
            target_cash = current_cash * kelly_fraction
            
            allocations[symbol] = {
                "kelly_fraction": kelly_fraction,
                "target_cash": target_cash,
                "adjusted_win_rate": adjusted_win_rate,
                "sentiment": sentiment
            }
            
        return allocations
