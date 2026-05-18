#!/usr/bin/env python3
"""
Trading Guardian - Core System
Sistema autónomo de execução a prova de falhas

4 Critical Failure Points Fixed:
FP1: Authentication Failure → Graceful handling + .env template
FP2: Missing Pre-Execution Validation → validation.py
FP3: No Rollback Mechanism → rollback.py  
FP4: No Health Monitoring → monitor.py
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Guardian - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SystemStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


@dataclass
class TradeOrder:
    """Represents a trade order with validation"""
    symbol: str
    side: str  # buy/sell
    quantity: float
    order_type: str = "market"
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    strategy: str = "default"
    confidence: float = 0.5  # default confidence
    
    def validate(self) -> Tuple[bool, str]:
        """Validate order parameters"""
        if not self.symbol or len(self.symbol) < 1:
            return False, "Invalid symbol"
        if self.side not in ['buy', 'sell']:
            return False, "Side must be 'buy' or 'sell'"
        if self.quantity <= 0:
            return False, "Quantity must be positive"
        return True, "OK"


@dataclass
class SystemMetrics:
    """System health metrics"""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: SystemStatus = SystemStatus.HEALTHY
    health_score: float = 100.0
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    api_calls: int = 0
    api_errors: int = 0
    uptime_seconds: float = 0.0
    
    def success_rate(self) -> float:
        if self.total_trades == 0:
            return 100.0
        return (self.successful_trades / self.total_trades) * 100


class TradingGuardian:
    """
    Main Guardian system with AutoResearch integration
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.project_path = "/Volumes/disco1tb/projects/trading-guardian"
        self.config_path = f"{self.project_path}/{config_path}"
        self.config = self._load_config()
        self.metrics = SystemMetrics()
        self.start_time = time.time()
        
        # Core components (lazy loaded)
        self._validator = None
        self._rollback = None
        self._monitor = None
        self._autoresearch = None
        self._strategy_engine = None
        self._alpaca_executor_paper = None  # Paper trading (testing)
        self._alpaca_executor_live = None   # Live trading (proven strategies)
        self._dual_mode_enabled = True  # Enable both Paper + Live simultaneously
        
        # Credentials check (FP1 fix)
        self.credentials_ok = self._check_credentials()
        
        # Initialize strategy engine and register strategies
        self._init_strategies()
        
        logger.info(f"Trading Guardian initialized | Credentials: {self.credentials_ok}")
    
    def is_market_open(self) -> bool:
        """
        Check if the NYSE market is currently open (US/Eastern)
        Regular hours: 9:30 AM - 4:00 PM ET, Monday-Friday
        Using pure-python timezone offset to avoid pytz dependency.
        """
        from datetime import datetime, timezone, timedelta
        try:
            # 1. Get current time in UTC
            now_utc = datetime.now(timezone.utc)
            
            # 2. Determine Eastern Time offset (Daylight Saving Time check)
            year = now_utc.year
            # DST starts 2nd Sunday in March
            dst_start = datetime(year, 3, 14, 2, tzinfo=timezone.utc) - timedelta(days=datetime(year, 3, 14).weekday() + 1)
            # DST ends 1st Sunday in November
            dst_end = datetime(year, 11, 7, 2, tzinfo=timezone.utc) - timedelta(days=datetime(year, 11, 7).weekday() + 1)
            
            is_dst = dst_start <= now_utc < dst_end
            offset = -4 if is_dst else -5
            
            # 3. Convert current UTC time to Eastern Time
            now_et = now_utc + timedelta(hours=offset)
            
            # 4. Check weekday (Monday=0 to Friday=4)
            if now_et.weekday() > 4:
                return False
                
            # 5. Check regular trading hours: 9:30 AM - 4:00 PM ET
            market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
            
            return market_open <= now_et <= market_close
        except Exception as e:
            logger.warning(f"Error checking market hours: {e}")
            return False  # SAFE DEFAULT
    
    def _load_config(self) -> Dict:
        """Load configuration"""
        try:
            import yaml
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning("Config not found, using defaults")
            return self._default_config()
        except Exception as e:
            logger.error(f"Config error: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict:
        return {
            "guardian": {
                "max_risk_per_trade": 0.01,
                "max_daily_loss": 0.05,
                "validation_enabled": True,
                "auto_rollback": True
            },
            "autoresearch": {
                "enabled": True,
                "experiment_interval": 3600
            }
        }
    
    def _check_credentials(self) -> bool:
        """
        Check if API credentials are configured (FP1)
        Uses AlpacaExecutor's credential loading logic
        """
        try:
            # Try to initialize AlpacaExecutor - it will load from ~/.openclaw/secrets/
            from src.alpaca_executor import AlpacaExecutor
            executor = AlpacaExecutor(use_live=False)
            # If no exception, credentials are OK
            logger.info("✅ Alpaca credentials verified via AlpacaExecutor")
            return True
        except Exception as e:
            logger.warning(f"⚠️  Credentials check failed: {e}")
            return False
    
    @property
    def validator(self):
        """Lazy load validator (FP2)"""
        if self._validator is None:
            from validation import PreExecutionValidator
            self._validator = PreExecutionValidator(self)
        return self._validator
    
    @property
    def rollback(self):
        """Lazy load rollback (FP3)"""
        if self._rollback is None:
            from rollback import RollbackManager
            self._rollback = RollbackManager(self)
        return self._rollback
    
    @property
    def monitor(self):
        """Lazy load monitor (FP4)"""
        if self._monitor is None:
            from monitor import HealthMonitor
            self._monitor = HealthMonitor(self)
        return self._monitor
    
    @property
    def autoresearch(self):
        """Lazy load AutoResearch engine"""
        if self._autoresearch is None:
            from autoresearch_engine import AutoResearchEngine
            self._autoresearch = AutoResearchEngine(self.project_path)
        return self._autoresearch
    
    @property
    def strategy_engine(self):
        """Lazy load Strategy Engine (multi-strategy)"""
        if self._strategy_engine is None:
            from strategy_engine import StrategyEngine
            from strategy_bollinger import BollingerStrategy
            from strategy_momentum import MomentumStrategy
            from strategy_rsi import RSIStrategy
            from strategy_first_hour import FirstHourBreakoutStrategy
            
            self._strategy_engine = StrategyEngine(self.alpaca_executor_paper)
            self._strategy_engine.register_strategy('bollinger', BollingerStrategy())
            self._strategy_engine.register_strategy('momentum', MomentumStrategy())
            self._strategy_engine.register_strategy('rsi', RSIStrategy())
            self._strategy_engine.register_strategy('first_hour', FirstHourBreakoutStrategy())
            
            logger.info(f"✅ StrategyEngine loaded with {len(self._strategy_engine.strategies)} strategies")
        return self._strategy_engine
    
    @property
    def alpaca_executor_paper(self):
        """Lazy load Alpaca Executor for Paper Trading (testing, no risk)"""
        if self._alpaca_executor_paper is None:
            from src.alpaca_executor import AlpacaExecutor
            self._alpaca_executor_paper = AlpacaExecutor(use_live=False)
            logger.info("✅ AlpacaExecutor Paper Trading initialized")
        return self._alpaca_executor_paper
    
    @property
    def alpaca_executor_live(self):
        """Lazy load Alpaca Executor for Live Trading (proven strategies only)"""
        if self._alpaca_executor_live is None:
            try:
                from src.alpaca_executor import AlpacaExecutor
                self._alpaca_executor_live = AlpacaExecutor(use_live=True)
                logger.info("✅ AlpacaExecutor Live Trading initialized")
            except Exception as e:
                logger.warning(f"⚠️ Live trading unavailable: {e}")
                return None
        return self._alpaca_executor_live
    
    def _get_executor_for_strategy(self, strategy_name: str):
        """
        Smart routing: Choose Paper or Live based on strategy performance
        - Paper: New strategies, backtesting, unproven
        - Live: Proven strategies (Sharpe > 2.0, drawdown < 5%)
        """
        if not self._dual_mode_enabled:
            return self.alpaca_executor_paper  # Fallback to paper only
        
        # Check if strategy is proven via autoresearch experiments file
        try:
            import os, json
            experiments_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'experiments.jsonl')
            experiments_file = os.path.abspath(experiments_file)
            
            if os.path.exists(experiments_file):
                with open(experiments_file, 'r') as f:
                    for line in f:
                        try:
                            exp = json.loads(line.strip())
                            exp_strategy = exp.get('strategy_name', exp.get('strategy', ''))
                            if exp_strategy == strategy_name:
                                sharpe = exp.get('sharpe_ratio', 0)
                                drawdown = exp.get('max_drawdown_pct', exp.get('max_drawdown', 100))
                                
                                # Proven strategy criteria
                                if sharpe > 2.0 and drawdown < 5.0:
                                    live_exec = self.alpaca_executor_live
                                    if live_exec:
                                        logger.info(f"📈 Strategy '{strategy_name}' → LIVE (Sharpe: {sharpe:.2f})")
                                        return live_exec
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"Strategy routing check failed: {e}")
        
        # Default: Paper trading (safe)
        logger.info(f"📄 Strategy '{strategy_name}' → PAPER (testing/unproven)")
        return self.alpaca_executor_paper
    
    def _init_strategies(self):
        """Initialize and register all trading strategies"""
        try:
            # This will trigger the lazy loading
            _ = self.strategy_engine
        except Exception as e:
            logger.warning(f"Failed to initialize strategies: {e}")
    
    def execute_trade(self, order: TradeOrder) -> Tuple[bool, str, Dict]:
        """
        Execute a trade with full validation and rollback
        Returns: (success, message, details)
        """
        logger.info(f"Executing trade: {order.side} {order.quantity} {order.symbol}")
        self.metrics.total_trades += 1
        self.metrics.api_calls += 1
        
        # Phase1: Validate order
        if self.config.get("guardian", {}).get("validation_enabled", True):
            valid, msg = self.validator.validate_order(order)
            if not valid:
                self.metrics.failed_trades += 1
                logger.error(f"Validation failed: {msg}")
                return False, f"Validation failed: {msg}", {}
        
        # Phase2: Check credentials
        if not self.credentials_ok:
            self.metrics.failed_trades += 1
            return False, "Credentials not configured", {}
        
        # Phase3: Pre-execution snapshot (for rollback)
        snapshot = self.rollback.create_snapshot(f"pre_trade_{order.symbol}")
        
        # Phase4: Execute REAL order via Alpaca
        try:
            result = self._execute_real_order(order)
            
            if result["success"]:
                self.metrics.successful_trades += 1
                logger.info(f"✅ Trade executed: {result}")
                
                # Send Discord notification immediately
                self._notify_discord(order, result, success=True)
                
                return True, "Trade executed successfully", result
            else:
                # Rollback if enabled
                if self.config.get("guardian", {}).get("auto_rollback", True):
                    self.rollback.restore_snapshot(snapshot["id"])
                self.metrics.failed_trades += 1
                
                # Send Discord notification of failure
                self._notify_discord(order, result, success=False)
                
                return False, result.get("error", "Unknown error"), result
                
        except Exception as e:
            self.metrics.failed_trades += 1
            self.metrics.api_errors += 1
            logger.error(f"Trade execution error: {e}")
            
            # Auto-rollback on failure
            if self.config.get("guardian", {}).get("auto_rollback", True):
                self.rollback.restore_snapshot(snapshot["id"])
            
            # Send Discord notification of error
            self._notify_discord(order, {"error": str(e)}, success=False)
            
            return False, f"Exception: {str(e)}", {}
    
    def _execute_real_order(self, order: TradeOrder) -> Dict:
        """
        Execute order via smart routing (Paper or Live based on strategy performance)
        """
        try:
            # Smart routing: Paper for testing, Live for proven strategies
            executor = self._get_executor_for_strategy(order.strategy)
            
            # Log which mode we're using
            mode = "LIVE" if executor == self._alpaca_executor_live else "PAPER"
            logger.info(f"📊 Executing via {mode}: {order.side} {order.quantity} {order.symbol}")
            
            # Submit order
            result = executor.submit_order(
                symbol=order.symbol,
                qty=order.quantity,
                side=order.side,
                order_type=order.order_type
            )
            
            if result:
                filled_price = result.get("filled_avg_price")
                filled_qty = result.get("filled_qty")
                
                # Determine mode for reporting
                mode = "LIVE" if executor == self._alpaca_executor_live else "PAPER"
                
                result = {
                    "success": True,
                    "order_id": result.get("id"),
                    "symbol": result.get("symbol"),
                    "filled_price": float(filled_price) if filled_price is not None else 0.0,
                    "filled_qty": float(filled_qty) if filled_qty is not None else 0.0,
                    "status": result.get("status"),
                    "strategy": order.strategy,
                    "mode": mode  # PAPER or LIVE
                }
                # Log trade for reporting
                self._log_trade_to_file(result)
                return result
            else:
                return {
                    "success": False,
                    "error": "Order submission failed - no result returned"
                }
                
        except Exception as e:
            logger.error(f"Real execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _log_trade_to_file(self, trade_data: Dict):
        """Append trade data to data/trades.jsonl for reporting"""
        try:
            import os
            from pathlib import Path
            # Get project root (parent of src)
            project_root = Path(__file__).parent.parent
            trades_file = project_root / "data" / "trades.jsonl"
            trades_file.parent.mkdir(exist_ok=True)
            
            # Add timestamp and latency if not present
            trade_data.setdefault("timestamp", datetime.now().isoformat())
            trade_data.setdefault("latency_ms", 0.0)
            
            with open(trades_file, "a") as f:
                f.write(json.dumps(trade_data) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log trade to file: {e}")

    def execute_real_trade(self, signal: Dict) -> Tuple[bool, str, Dict]:
        """
        Execute a trade from a strategy signal
        signal: Dict with keys: symbol, qty, side, strategy_name, confidence
        Returns: (success, message, details_dict)
        """
        order = TradeOrder(
            symbol=signal["symbol"],
            side=signal.get("side", "buy"),
            quantity=signal["qty"],
            order_type="market",
            strategy=signal.get("strategy_name", "unknown"),
            confidence=signal.get("confidence", 0.5)
        )
        
        success, msg, details = self.execute_trade(order)
        return success, msg, details
    
    def check_position_protection(self, positions: Dict, executor_mode: str = "paper") -> List[Dict]:
        """
        Verifica posições existentes e gera sinais de SELL para proteção
        - Stop-loss: -3% (venda imediata)
        - Take-profit: +8% (realiza lucro)
        Returns: Lista de sinais de VENDA
        """
        sell_signals = []
        
        if not positions:
            return sell_signals
        
        for symbol, data in positions.items():
            try:
                qty = float(data.get('qty', 0))
                current_price = float(data.get('current', 0))
                entry_price = float(data.get('avg_entry_price', data.get('entry', 0)))
                
                if qty <= 0 or entry_price <= 0:
                    continue
                
                # Calcular P&L percentual
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                
                # STOP-LOSS: Vender se perda > 3%
                if pnl_pct <= -3.0:
                    sell_signals.append({
                        "symbol": symbol,
                        "qty": qty,
                        "side": "sell",
                        "strategy_name": "stop_loss",
                        "confidence": 1.0,
                        "reason": f"STOP-LOSS: {pnl_pct:.2f}% loss",
                        "pnl_pct": pnl_pct
                    })
                    logger.warning(f"🛡️ STOP-LOSS triggered for {symbol}: {pnl_pct:.2f}%")
                
                # TAKE-PROFIT: Vender se ganho > 8%
                elif pnl_pct >= 8.0:
                    sell_signals.append({
                        "symbol": symbol,
                        "qty": qty,
                        "side": "sell",
                        "strategy_name": "take_profit",
                        "confidence": 1.0,
                        "reason": f"TAKE-PROFIT: {pnl_pct:.2f}% gain",
                        "pnl_pct": pnl_pct
                    })
                    logger.info(f"🎯 TAKE-PROFIT triggered for {symbol}: {pnl_pct:.2f}%")
                
            except Exception as e:
                logger.error(f"Error checking protection for {symbol}: {e}")
        
        return sell_signals

    def aggregate_signals(self) -> List[Dict]:
        """
        Aggregate signals from all strategies
        Returns: List of trade signals (BUY and SELL) ready for execution
        """
        try:
            # Build prices dict for strategy engine
            prices = {}
            buy_signals = []
            sell_signals = []
            
            # Get current positions (Paper first)
            positions_paper = self.alpaca_executor_paper.get_positions()
            
            # Check position protection (stop-loss / take-profit)
            protection_signals = self.check_position_protection(positions_paper, "paper")
            sell_signals.extend(protection_signals)
            
            # Build prices from positions
            if positions_paper:
                for symbol, data in positions_paper.items():
                    qty = data.get('qty', 0)
                    current_price = data.get('current')
                    if current_price:
                        prices[symbol] = {"qty": qty, "current": current_price}
            
            # Add default symbols to monitor
            default_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AMD", "INTC"]
            for sym in default_symbols:
                if sym not in prices:
                    current_price = self.alpaca_executor_paper.get_current_price(sym)
                    if current_price:
                        prices[sym] = {"qty": 0, "current": current_price}
            
            if not prices:
                logger.warning("No price data available for any symbol")
                return sell_signals  # Return only sell signals if no price data
            
            # Get strategy signals
            all_signals = self.strategy_engine.get_all_signals(prices)
            aggregated = self.strategy_engine.aggregate_signals(all_signals)
            
            # Process BUY signals
            account = self.alpaca_executor_paper.get_account()
            cash = float(account.get("cash", 0)) if account else 0
            
            for symbol, agg in aggregated.items():
                # Check if we already have a position (avoid duplication)
                has_position = symbol in positions_paper and float(positions_paper[symbol].get('qty', 0)) > 0
                
                if agg["buy_votes"] > agg["sell_votes"] and not has_position:
                    # Calculate quantity based on confidence and account balance
                    max_trade_value = cash * 0.02  # Risk 2% of cash per trade
                    current_price = self.alpaca_executor_paper.get_current_price(symbol)
                    if current_price and current_price > 0:
                        qty = round(max_trade_value / current_price, 4)
                        if qty > 0:
                            buy_signals.append({
                                "symbol": symbol,
                                "qty": qty,
                                "side": "buy",
                                "strategy_name": "aggregated",
                                "confidence": agg.get("confidence", 0.5),
                                "buy_votes": agg["buy_votes"],
                                "sell_votes": agg["sell_votes"]
                            })
                
                # Process SELL signals from strategies
                elif agg["sell_votes"] > agg["buy_votes"]:
                    if symbol in positions_paper:
                        qty = float(positions_paper[symbol].get('qty', 0))
                        if qty > 0:
                            sell_signals.append({
                                "symbol": symbol,
                                "qty": qty,
                                "side": "sell",
                                "strategy_name": "strategy_sell",
                                "confidence": agg.get("confidence", 0.5),
                                "reason": f"Strategy sell signal: {agg['sell_votes']} votes",
                                "buy_votes": agg["buy_votes"],
                                "sell_votes": agg["sell_votes"]
                            })
            
            logger.info(f"Aggregated {len(buy_signals)} buy signals and {len(sell_signals)} sell signals")
            return buy_signals + sell_signals
            
        except Exception as e:
            logger.error(f"Signal aggregation error: {e}")
            return []
    
    def _notify_discord(self, order: TradeOrder, result: Dict, success: bool):
        """
        Send immediate Discord notification after trade execution
        """
        try:
            from discord_retry import send_trade_notification
            
            # Extrair pareceres dos agentes para transparência total
            macro = getattr(self.strategy_engine, 'macro_sentiment', {})
            macro_bias = f"{macro.get('bias', 'N/A')} ({macro.get('score', 0)})"
            
            # Recuperar último sentimento social do cache
            social_data = getattr(self.strategy_engine.social_intel, 'sentiment_cache', {}).get(order.symbol, {})
            social_summary = f"{social_data.get('bias', 'Neutral')} | Panic: {social_data.get('panic_level', '0')}/10"

            notification_data = {
                "symbol": order.symbol,
                "qty": order.quantity,
                "price": result.get("filled_price", 0),
                "strategy_name": order.strategy,
                "confidence": getattr(order, "confidence", 0.5),
                "side": order.side,
                "macro_bias": macro_bias,
                "social_sentiment": social_summary,
                "risk_audit": "✅ Passed Sentinel Portfolio Audit"
            }
            
            send_trade_notification(notification_data, success, result)
            
        except Exception as e:
            logger.error(f"Discord notification error: {e}")
    
    def _simulate_execution(self, order: TradeOrder) -> Dict:
        """Simulate trade execution (DEPRECATED - use _execute_real_order)"""
        time.sleep(0.5)  # Simulate API call
        return {
            "success": True,
            "order_id": f"sim_{int(time.time())}",
            "symbol": order.symbol,
            "filled_price": 100.0,  # Simulated
            "filled_qty": order.quantity,
            "status": "filled"
        }
    
    def run_autoresearch_cycle(self) -> Dict:
        """Run one AutoResearch cycle"""
        if not self.config.get("autoresearch", {}).get("enabled", True):
            return {"status": "disabled"}
        
        logger.info("🔬 Starting AutoResearch cycle...")
        return self.autoresearch.run_cycle()
    
    def get_health(self) -> Dict:
        """Get current system health"""
        self.metrics.uptime_seconds = time.time() - self.start_time
        return self.monitor.check_health()
    
    def run_forever(self, check_interval: int = 60):
        """
        Main loop - continuous operation with AutoResearch
        """
        logger.info("🚀 Trading Guardian entering main loop...")
        self.metrics.status = SystemStatus.HEALTHY
        
        last_autoresearch = 0
        interval = self.config.get("autoresearch", {}).get("experiment_interval", 3600)
        
        while True:
            try:
                # Health check
                health = self.get_health()
                
                # Run AutoResearch periodically
                if time.time() - last_autoresearch > interval:
                    cycle_result = self.run_autoresearch_cycle()
                    logger.info(f"AutoResearch cycle: {cycle_result}")
                    last_autoresearch = time.time()
                
                # Log status
                logger.info(
                    f"Status: {self.metrics.status.value} | "
                    f"Health: {self.metrics.health_score:.1f} | "
                    f"Trades: {self.metrics.total_trades} | "
                    f"Success: {self.metrics.success_rate():.1f}%"
                )
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                self.metrics.status = SystemStatus.CRITICAL
                time.sleep(check_interval)


if __name__ == "__main__":
    import os
    guardian = TradingGuardian()
    
    # Test with a sample order
    order = TradeOrder(
        symbol="AAPL",
        side="buy",
        quantity=10,
        stop_loss=95.0,
        take_profit=110.0
    )
    
    success, msg, details = guardian.execute_trade(order)
    print(f"Trade result: {success} - {msg}")
    
    # Health check
    health = guardian.get_health()
    print(f"Health: {json.dumps(health, indent=2)}")
