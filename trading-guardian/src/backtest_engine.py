#!/usr/bin/env python3
"""
Trading Guardian - Historical Backtest Engine
Simulates trading strategies on historical market data to calculate Sharpe Ratio,
Max Drawdown, Win Rate, and Total Returns.
"""

import logging
import numpy as np
from typing import Dict, List, Type, Any

logger = logging.getLogger("BacktestEngine")


class MockAlpacaClient:
    """Mock Alpaca Client for Backtester that supplies rolling historical bars"""
    
    def __init__(self, historical_bars: List[Dict]):
        self.all_bars = historical_bars
        self.current_idx = 0
        
    def get_bars(self, symbol: str, period: int = 14, timeframe: str = '1Day') -> List[Dict]:
        # Return the sliding window of bars up to the current index
        start = max(0, self.current_idx - period)
        return self.all_bars[start:self.current_idx + 1]

    def get_current_price(self, symbol: str) -> float:
        if self.current_idx < len(self.all_bars):
            return float(self.all_bars[self.current_idx]['c'])
        return 0.0


class BacktestEngine:
    """
    Historical Backtester for Trading Guardian strategies.
    Verifies and validates parameter changes using real historical data.
    """
    
    def __init__(self, executor_client: Any):
        self.executor = executor_client

    def run_backtest(self, strategy_class: Type, ticker: str, parameters: Dict[str, Any], backtest_days: int = 60) -> Dict:
        """
        Runs a simulation of a strategy on a ticker over the last backtest_days.
        Returns detailed performance metrics.
        """
        logger.info(f"📊 Starting Backtest for {ticker} | Strategy: {strategy_class.__name__} | Params: {parameters}")
        
        # 1. Fetch historical bars for backtesting
        # We need extra bars for the indicators' initial warmup period (e.g. 30 days)
        warmup_period = 35
        total_bars_needed = backtest_days + warmup_period
        
        bars = self.executor.get_bars(ticker, period=total_bars_needed)
        if not bars or len(bars) < warmup_period + 5:
            logger.warning(f"⚠️ Insufficient historical data for {ticker}. Found {len(bars)} bars, need at least {warmup_period + 5}.")
            return {
                "success": False,
                "sharpe_ratio": 0.0,
                "total_return_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "win_rate_pct": 0.0,
                "trades_count": 0,
                "error": "Insufficient historical data"
            }
            
        # 2. Setup simulation environment
        mock_client = MockAlpacaClient(bars)
        strategy = strategy_class(**parameters)
        strategy.client = mock_client
        
        initial_cash = 10000.0
        cash = initial_cash
        position_qty = 0.0
        portfolio_history = []
        trades = []
        
        # 3. Simulate day-by-day
        start_idx = warmup_period
        for idx in range(start_idx, len(bars)):
            mock_client.current_idx = idx
            current_bar = bars[idx]
            current_price = float(current_bar['c'])
            
            # Check strategy signals
            signal = strategy.get_signal(ticker, current_price, position_qty)
            
            # Process signals
            if signal and signal['signal'] == 'BUY' and cash >= current_price:
                # Buy 1 share for simulation simplicity
                qty_to_buy = 1.0
                cost = qty_to_buy * current_price
                cash -= cost
                position_qty += qty_to_buy
                trades.append({
                    "type": "BUY",
                    "price": current_price,
                    "qty": qty_to_buy,
                    "time": current_bar.get('t', idx)
                })
            elif signal and signal['signal'] == 'SELL' and position_qty > 0:
                # Sell all accumulated position
                revenue = position_qty * current_price
                cash += revenue
                trades.append({
                    "type": "SELL",
                    "price": current_price,
                    "qty": position_qty,
                    "time": current_bar.get('t', idx)
                })
                position_qty = 0.0
                
            # Track portfolio value
            equity = cash + (position_qty * current_price)
            portfolio_history.append(equity)
            
        # 4. Compute performance metrics
        portfolio_history = np.array(portfolio_history)
        if len(portfolio_history) < 2:
            return {"success": False, "error": "Insufficient simulation steps"}
            
        # Cumulative Return
        final_value = portfolio_history[-1]
        total_return_pct = ((final_value - initial_cash) / initial_cash) * 100.0
        
        # Daily Returns & Sharpe Ratio
        daily_returns = np.diff(portfolio_history) / portfolio_history[:-1]
        avg_daily_return = np.mean(daily_returns) if len(daily_returns) > 0 else 0.0
        std_daily_return = np.std(daily_returns) if len(daily_returns) > 0 else 0.0
        
        # Annualized Sharpe (assuming 252 trading days)
        if std_daily_return > 0:
            sharpe_ratio = (avg_daily_return / std_daily_return) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0
            
        # Max Drawdown
        peak = np.maximum.accumulate(portfolio_history)
        drawdowns = (portfolio_history - peak) / peak
        max_drawdown_pct = np.min(drawdowns) * 100.0 if len(drawdowns) > 0 else 0.0
        
        # Win Rate
        wins = 0
        losses = 0
        # A win is defined as selling at a price higher than the average buy price
        # For simplicity, calculate win rate of transactions
        for i in range(1, len(trades)):
            if trades[i]["type"] == "SELL" and trades[i-1]["type"] == "BUY":
                if trades[i]["price"] > trades[i-1]["price"]:
                    wins += 1
                else:
                    losses += 1
                    
        total_complete_trades = wins + losses
        win_rate_pct = (wins / total_complete_trades * 100.0) if total_complete_trades > 0 else 0.0
        
        logger.info(f"📊 Backtest Complete | Return: {total_return_pct:+.2f}% | Sharpe: {sharpe_ratio:.2f} | Drawdown: {max_drawdown_pct:.2f}% | Trades: {len(trades)}")
        
        return {
            "success": True,
            "sharpe_ratio": float(sharpe_ratio),
            "total_return_pct": float(total_return_pct),
            "max_drawdown_pct": float(max_drawdown_pct),
            "win_rate_pct": float(win_rate_pct),
            "trades_count": len(trades)
        }
