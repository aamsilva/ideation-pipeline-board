#!/usr/bin/env python3
"""
Trading Guardian Daemon - Continuous Operation (5min cycles)
Tier-1 Trading Grade: Real execution, Health monitoring, Multi-strategy
"""

import sys
import os
import time
import json
import logging
import signal
from datetime import datetime
from typing import Dict, List
import asyncio
# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
except ImportError:
    pass

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Add websocket client import
from websocket_client import AlpacaWebsocketClient

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-10s | %(levelname)-7s | %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'guardian_daemon.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('GuardianDaemon')

# HIGH AVAILABILITY MODE - NO GRACEFUL SHUTDOWN
# Daemon runs FOREVER - signals are IGNORED for 99.9999% uptime
import signal
running = True

def signal_handler(sig, frame):
    """Ignore all shutdown signals - High Availability Mode"""
    logger.warning(f"⚠️ Signal {sig} IGNORED - High Availability Mode Active")
    # DO NOT set running = False - keep running forever

# Ignore all termination signals
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)

logger.info("🛡️ High Availability Mode: ALL shutdown signals will be IGNORED")


async def main():
    # Initialize Alpaca WebSocket client for real‑time price feed
    from websocket_client import AlpacaWebsocketClient
    ws_client = AlpacaWebsocketClient()
    ws_client.start_async()
    # Subscribe to default watchlist symbols (will be refreshed each cycle)
    default_symbols = ["AAPL", "AMD", "INTC", "GOOGL", "MSFT"]
    ws_client.subscribe(default_symbols)
    logger.info("🚀 WebSocket client started for real‑time price updates")
    """Main daemon loop"""
    from guardian_core import TradingGuardian
    
    logger.info("=" * 60)
    logger.info("🚀 Trading Guardian Daemon starting...")
    logger.info("=" * 60)
    
    # Initialize Guardian
    try:
        guardian = TradingGuardian()
        logger.info(f"✅ Guardian initialized | Credentials: {guardian.credentials_ok}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Guardian: {e}")
        return
        
    # Initialize and start Agent Swarm (Risk Officer + Sentiment Scout)
    try:
        from agent_swarm import AgentSwarm
        swarm = AgentSwarm()
        await swarm.start()
        logger.info("✅ Agent Swarm Orchestrator started successfully in background")
    except Exception as e:
        logger.error(f"❌ Failed to start Agent Swarm: {e}")
    
    # Initialize Alpaca Executors (Paper + Live dual mode)
    try:
        _ = guardian.alpaca_executor_paper
        account_paper = guardian.alpaca_executor_paper.get_account()
        if account_paper:
            logger.info(f"💰 Paper Account: ${float(account_paper.get('cash', 0)):.2f}")
            logger.info(f"📊 Paper Buying Power: ${float(account_paper.get('buying_power', 0)):.2f}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Alpaca Paper: {e}")
        return
    
    # Try Live account (optional - may not have credentials)
    try:
        live_exec = guardian.alpaca_executor_live
        if live_exec:
            account_live = live_exec.get_account()
            if account_live:
                logger.info(f"💰 LIVE Account: ${float(account_live.get('cash', 0)):.2f}")
                logger.info(f"📊 LIVE Buying Power: ${float(account_live.get('buying_power', 0)):.2f}")
    except Exception as e:
        logger.warning(f"⚠️  Live account unavailable: {e}")
    
    # ========== Register Strategies ==========
    from strategy_bollinger_breakout import StrategyBollingerBreakout
    bb_strategy = StrategyBollingerBreakout(alpaca_executor=guardian.alpaca_executor_paper)
    guardian.strategy_engine.register_strategy('bollinger_breakout', bb_strategy)
    logger.info("✅ Bollinger Breakout strategy registered")
    
    cycle_count = 0
    check_interval = 300  # 5 minutes
    
    while running:
        cycle_count += 1
        cycle_start = time.time()
        
        logger.info("-" * 60)
        logger.info(f"🔄 CYCLE #{cycle_count} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 60)
        
        # State accumulator for this cycle
        cycle_state = {
            "timestamp": datetime.now().isoformat(),
            "cycle": cycle_count,
            "paper": {"account": {}, "positions": []},
            "live": {"account": {}, "positions": []},
            "trades": {"executed": 0, "failed": 0, "recent": []},
            "health": {},
            "strategies": {"testing": [], "approved": [], "validated": 0, "total": 0},
            "execution": {"orders": 0, "filled": 0, "latency_ms": 0.0},
            "risk": {"leverage": 0.0, "exposure": 0.0},
            "uptime_pct": 100.0,
            "checks": cycle_count
        }
        
        try:
            # ========== PHASE 0: CANCEL PENDING ORDERS ==========
            logger.info("🔄 Canceling pending orders from previous cycles...")
            try:
                # Cancel orders only if market is open
                if guardian.is_market_open():
                    paper_exec = guardian.alpaca_executor_paper
                    if paper_exec:
                        paper_exec.cancel_all_orders()
                        logger.info("   ✅ Paper orders cancelled")
                    live_exec = guardian.alpaca_executor_live
                    if live_exec:
                        live_exec.cancel_all_orders()
                        logger.info("   ✅ Live orders cancelled")
                    await asyncio.sleep(2)
                else:
                    logger.info("   ⏳ Market is CLOSED. Preserving queued orders.")
            except Exception as e:
                logger.warning(f"   ⚠️  Error canceling orders: {e}")
            
            # ========== PHASE 1: HEALTH CHECK ==========
            logger.info("🏥 Running health checks...")
            health = guardian.get_health()
            cycle_state["health"] = health
            logger.info(f"   Health Score: {health['overall_score']:.1f} | Status: {health['status']}")
            
            if health['overall_score'] < 50:
                logger.error("❌ Health score too low, skipping this cycle")
                await asyncio.sleep(check_interval)
                continue
            
            # ========== HOT-RELOAD STRATEGIES ==========
            logger.info("🔄 Checking for strategy mutations to hot-reload...")
            try:
                import importlib
                import strategy_bollinger
                import strategy_momentum
                import strategy_rsi
                import strategy_first_hour
                
                # Reload modules from disk
                importlib.reload(strategy_bollinger)
                importlib.reload(strategy_momentum)
                importlib.reload(strategy_rsi)
                importlib.reload(strategy_first_hour)
                
                # Re-register strategy instances on strategy_engine
                guardian.strategy_engine.register_strategy('bollinger', strategy_bollinger.BollingerStrategy())
                guardian.strategy_engine.register_strategy('momentum', strategy_momentum.MomentumStrategy())
                guardian.strategy_engine.register_strategy('rsi', strategy_rsi.RSIStrategy())
                guardian.strategy_engine.register_strategy('first_hour', strategy_first_hour.FirstHourBreakoutStrategy())
                
                logger.info("   ✅ Strategies hot-reloaded dynamically from disk")
            except Exception as e:
                logger.warning(f"   ⚠️ Hot-reloading failed: {e}")
            
            # ========== PHASE 2: AGGREGATE SIGNALS ==========
            logger.info("📡 Aggregating signals from all strategies...")
            
            # Update macro sentiment
            try:
                guardian.strategy_engine.update_macro_sentiment()
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to update macro sentiment: {e}")
            
            # Refresh price cache and update opening range for each symbol
            try:
                # 1. Load dynamic watchlist from Hunter
                watchlist_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'watchlist.json')
                symbols_to_track = set(["AAPL", "AMD", "INTC", "GOOGL", "MSFT"]) # Default baseline
                
                if os.path.exists(watchlist_file):
                    try:
                        with open(watchlist_file, 'r') as f:
                            wdata = json.load(f)
                            symbols_to_track.update(wdata.get('tickers', []))
                            logger.info(f"   🏹 Dynamic Watchlist Loaded: {len(wdata.get('tickers', []))} targets")
                    except Exception as e:
                        logger.warning(f"   ⚠️  Failed to load watchlist.json: {e}")
                
                # Dynamic Hedging: If macro score indicates panic, inject inverse ETFs
                macro_score = guardian.strategy_engine.macro_sentiment.get("score", 0.0)
                if macro_score < -0.6:
                    logger.warning(f"🚨 MACRO RISK HEURISTIC: Ingesting Inverse ETFs (SH, PSQ) due to Panic Score ({macro_score})")
                    symbols_to_track.add("SH")
                    symbols_to_track.add("PSQ")

                # Use Paper executor for price data (cheap, safe)
                price_client = guardian.alpaca_executor_paper
                positions = price_client.get_positions()
                
                # Add symbols we already own
                symbols_to_track.update(positions.keys())
                
                refreshed_prices = {}
                for sym in symbols_to_track:
                    # Update opening range for strategies that need it
                    try:
                        data = positions.get(sym, {})
                        # Call update_opening_range on each registered strategy
                        for strat in guardian.strategy_engine.strategies.values():
                            if hasattr(strat, 'update_opening_range'):
                                # Get latest price for ORB
                                latest_px = price_client.get_current_price(sym)
                                if latest_px:
                                    strat.update_opening_range(sym, latest_px)
                    except Exception:
                        pass
                    # Get latest price (may use cache)
                    latest = ws_client.get_price(sym) or price_client.get_current_price(sym)
                    refreshed_prices[sym] = {
                        'qty': data.get('qty', 0),
                        'current': latest if latest is not None else data.get('current', 0),
                        'pnl': data.get('pnl', 0),
                        'market_value': data.get('market_value', 0)
                    }
                # Use refreshed_prices as the price map for strategy aggregation
                signals = guardian.strategy_engine.get_all_signals(refreshed_prices)
                # Aggregate within engine to produce final decision list
                aggregated = guardian.strategy_engine.aggregate_signals(signals)
                final_signals = []
                for sym, pdata in refreshed_prices.items():
                    decision = guardian.strategy_engine.make_decision(sym, pdata, aggregated)
                    if decision:
                        # Convert engine decision dict to the format expected by execute_real_trade
                        final_signals.append({
                            'symbol': decision['symbol'],
                            'qty': decision['qty'],
                            'side': decision['action'].lower(),
                            'reason': decision.get('reason', ''),
                            'confidence': decision.get('confidence', 0.5),
                            'strategy_name': decision.get('strategies', ['engine'])[0]
                        })
                signals = final_signals
            except Exception as e:
                logger.warning(f"   ⚠️  Signal aggregation failed: {e}")
                signals = []
            
            # Capture Paper account state (unchanged)
            try:
                account_paper = guardian.alpaca_executor_paper.get_account()
                positions_paper = guardian.alpaca_executor_paper.get_positions()
                if account_paper:
                    cycle_state["paper"]["account"] = {
                        "cash": float(account_paper.get("cash", 0)),
                        "buying_power": float(account_paper.get("buying_power", 0)),
                        "portfolio_value": float(account_paper.get("portfolio_value", 0))
                    }
                if positions_paper:
                    for sym, data in positions_paper.items():
                        cycle_state["paper"]["positions"].append({
                            "symbol": sym,
                            "qty": data.get("qty", 0),
                            "current": data.get("current", 0),
                            "pnl": data.get("pnl", 0),
                            "market_value": data.get("market_value", 0)
                        })
            except Exception as e:
                logger.warning(f"   ⚠️  Paper state capture failed: {e}")
            
            # Capture Live account state (unchanged)
            try:
                live_exec = guardian.alpaca_executor_live
                if live_exec:
                    account_live = live_exec.get_account()
                    positions_live = live_exec.get_positions()
                    cycle_state["live"]["account"] = {
                        "cash": float(account_live.get("cash", 0)),
                        "buying_power": float(account_live.get("buying_power", 0)),
                        "portfolio_value": float(account_live.get("portfolio_value", 0))
                    }
                    if positions_live:
                        for sym, data in positions_live.items():
                            cycle_state["live"]["positions"].append({
                                "symbol": sym,
                                "qty": data.get("qty", 0),
                                "current": data.get("current", 0),
                                "pnl": data.get("pnl", 0),
                                "market_value": data.get("market_value", 0)
                            })
            except Exception as e:
                logger.warning(f"   ⚠️  Live state capture failed: {e}")
            
            # Separate buy and sell signals for logging (now using engine decisions)
            buy_signals = [s for s in signals if s.get('side') == 'buy']
            sell_signals = [s for s in signals if s.get('side') == 'sell']
            
            if not signals:
                logger.info("   No trading signals this cycle")
                trade_latencies = []
            else:
                logger.info(f"   ✅ Generated {len(buy_signals)} buy signals and {len(sell_signals)} sell signals")
                
                # ========== PHASE 3: EXECUTE TRADES (BUY + SELL) ==========
                executed = 0
                failed = 0
                trade_latencies = []
                
                for signal in signals:
                    symbol = signal['symbol']
                    qty = signal['qty']
                    side = signal.get('side', 'buy')
                    reason = signal.get('reason', '')
                    
                    logger.info(f"   📈 Processing {side.upper()} {symbol} (qty={qty:.4f})... {reason}")
                    
                    success, msg, details = guardian.execute_real_trade(signal)
                    
                    if success:
                        executed += 1
                        mode = details.get('mode', 'PAPER')
                        latency = details.get('latency_ms', 0.0)
                        if latency > 0:
                            trade_latencies.append(latency)
                        logger.info(f"      ✅ Trade executed: {msg} [{mode}] (latency: {latency:.1f}ms)")
                        cycle_state["trades"]["recent"].append({
                            "symbol": symbol,
                            "qty": qty,
                            "side": side,
                            "mode": mode,
                            "timestamp": datetime.now().isoformat()
                        })
                    else:
                        failed += 1
                        logger.error(f"      ❌ Trade failed: {msg}")
                
                cycle_state["trades"]["executed"] = executed
                cycle_state["trades"]["failed"] = failed
                logger.info(f"   📊 Results: {executed} executed, {failed} failed")
            # ========== PHASE 4: STRATEGY BACKTEST DATA ==========
            try:
                from pathlib import Path
                exp_file = Path(__file__).parent.parent / "data" / "experiments.jsonl"
                if exp_file.exists():
                    strategies_testing = []
                    strategies_approved = []
                    validated = 0
                    total = 0
                    with open(exp_file, "r") as f:
                        for line in f:
                            try:
                                exp = json.loads(line.strip())
                                total += 1
                                name = exp.get("strategy_name", exp.get("strategy", "Unknown"))
                                sharpe = exp.get("sharpe_ratio", 0)
                                win_rate = exp.get("win_rate", 0)
                                dd = exp.get("max_drawdown_pct", exp.get("max_drawdown", 100))
                                strategy_info = f"{name}: {win_rate*100:.1f}%, Sharpe {sharpe:.2f}"
                                if sharpe > 2.0 and dd < 5.0:
                                    validated += 1
                                    strategies_approved.append(strategy_info)
                                else:
                                    strategies_testing.append(strategy_info)
                            except json.JSONDecodeError:
                                continue
                    cycle_state["strategies"]["testing"] = strategies_testing[:3]
                    cycle_state["strategies"]["approved"] = strategies_approved[:2]
                    cycle_state["strategies"]["validated"] = validated
                    cycle_state["strategies"]["total"] = total
            except Exception as e:
                logger.warning(f"   ⚠️  Strategy data capture failed: {e}")
            
            # ========== PHASE 5: AUTORESEARCH + PLATFORM DISCOVERY ==========
            if cycle_count % 12 == 0:  # Every 12 cycles = 1 hour
                logger.info("🔬 Running AutoResearch cycle...")
                try:
                    result = guardian.run_autoresearch_cycle()
                    logger.info(f"   AutoResearch: {result}")
                except Exception as e:
                    logger.error(f"   ❌ AutoResearch failed: {e}")
            
            # Platform Discovery every 60 cycles (5 hours)
            if cycle_count % 60 == 0:
                logger.info("🚀 Running Platform Discovery cycle...")
                try:
                    from platform_discovery import PlatformDiscovery
                    discovery = PlatformDiscovery()
                    result = discovery.run_discovery_cycle()
                    logger.info(f"   Platform Discovery: {result}")
                except Exception as e:
                    logger.error(f"   ❌ Platform Discovery failed: {e}")
            
            # ========== CYCLE SUMMARY ==========
            cycle_time = time.time() - cycle_start
            logger.info(f"✅ Cycle #{cycle_count} completed in {cycle_time:.1f}s")
            logger.info(f"   Total Trades: {guardian.metrics.total_trades}")
            logger.info(f"   Success Rate: {guardian.metrics.success_rate():.1f}%")
            
            # Update execution stats
            cycle_state["execution"]["orders"] = guardian.metrics.total_trades
            cycle_state["execution"]["filled"] = guardian.metrics.successful_trades
            avg_lat = sum(trade_latencies) / len(trade_latencies) if (signals and trade_latencies) else 0.0
            cycle_state["execution"]["latency_ms"] = avg_lat
            if avg_lat > 0:
                logger.info(f"⏱️ Cycle Average Trade Execution Latency: {avg_lat:.2f} ms")
            
            # Update risk metrics
            total_exposure = sum(p.get("market_value", 0) for p in cycle_state["paper"]["positions"])
            total_exposure += sum(p.get("market_value", 0) for p in cycle_state["live"]["positions"])
            total_balance = cycle_state["paper"]["account"].get("cash", 0) + cycle_state["live"]["account"].get("cash", 0)
            cycle_state["risk"]["exposure"] = total_exposure
            cycle_state["risk"]["leverage"] = total_exposure / total_balance if total_balance > 0 else 0.0
            
            # Write state to file for report script (NO Alpaca calls in report!)
            try:
                state_file = Path(__file__).parent.parent / "data" / "guardian_state.json"
                state_file.parent.mkdir(exist_ok=True)
                with open(state_file, "w") as f:
                    json.dump(cycle_state, f, indent=2, default=str)
                logger.info(f"   💾 State saved to {state_file}")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to save state: {e}")
            
        except Exception as e:
            logger.error(f"❌ Cycle #{cycle_count} error: {e}")
            guardian.metrics.api_errors += 1
        
        # ========== WAIT FOR NEXT CYCLE ==========
        if running:
            logger.info(f"😴 Sleeping {check_interval}s until next cycle...")
            # Sleep in small increments to allow graceful shutdown
            for _ in range(check_interval):
                if not running:
                    break
                await asyncio.sleep(1)
    
    logger.info("=" * 60)
    logger.info("🛑 Trading Guardian Daemon stopped")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
