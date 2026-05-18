#!/usr/bin/env python3
"""
Strategy Engine - Central Coordinator
Recebe sinais de TODAS as estratégias e decide: BUY / SELL / HOLD
"""

from alpaca_executor import get_executor
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class StrategyEngine:
    """Motor central que coordena todas as estratégias"""
    
    def __init__(self, alpaca_executor, use_live: bool = False):
        self.alpaca_executor = alpaca_executor
        self.client = alpaca_executor  # Use the passed executor as client
        self.strategies = {}  # {name: strategy_instance}
        self.max_position_value = 100  # Max $100 per position (live)
        self.min_confidence = 0.4  # Lowered for more aggressive trading
        self.notify_callback = None  # Callback for notifications
        self.macro_sentiment = {"score": 0.0, "bias": "neutral", "reason": "Initial state"}
        
        # Level 4.7: Social Intelligence & Risk Management
        from social_intelligence import SocialIntelligence
        from risk_manager import SentinelRiskManager
        from portfolio_rebalancer import PortfolioRebalancer
        self.social_intel = SocialIntelligence()
        self.risk_manager = SentinelRiskManager()
        self.rebalancer = PortfolioRebalancer()

    def update_macro_sentiment(self):
        """Update global macro sentiment using Dexter tools"""
        try:
            from dexter_tools import get_macro_sentiment
            self.macro_sentiment = get_macro_sentiment()
            
            # Adjust min_confidence based on macro score
            # Score 1.0 (Bullish) -> min_confidence 0.45 (Aggressive)
            # Score -1.0 (Bearish) -> min_confidence 0.75 (Conservative)
            score = self.macro_sentiment.get("score", 0.0)
            self.min_confidence = 0.55 - (score * 0.15)
            self.min_confidence = max(0.40, min(0.80, self.min_confidence))
            
            print(f"🌍 Macro Sentiment: {self.macro_sentiment['bias'].upper()} (Score: {score})")
            print(f"🛡️ Adjusted Confidence Threshold: {self.min_confidence:.2f}")
        except Exception as e:
            print(f"⚠️ Failed to update macro sentiment: {e}")

    def register_strategy(self, name: str, strategy_instance):
        """Registar uma nova estratégia"""
        strategy_instance.client = self.alpaca_executor
        self.strategies[name] = strategy_instance
        print(f"✅ Strategy registered: {name}")
    
    def get_all_signals(self, prices: Dict) -> List[Dict]:
        """Obter sinais de TODAS as estratégias registadas"""
        all_signals = []
        
        for name, strategy in self.strategies.items():
            try:
                for symbol, data in prices.items():
                    qty = data.get('qty', 0)
                    current = data.get('current', 0)
                    
                    # Chamar método get_signal() se existir
                    if hasattr(strategy, 'get_signal'):
                        signal = strategy.get_signal(symbol, current, qty)
                        if signal:
                            signal['symbol'] = symbol  # Add symbol to signal!
                            signal['strategy'] = name
                            all_signals.append(signal)
                            
            except Exception as e:
                print(f"❌ Error getting signals from {name}: {e}")
        
        return all_signals
    
    def aggregate_signals(self, signals: List[Dict]) -> Dict:
        """Agregar sinais por símbolo (votação)"""
        aggregated = {}
        
        for signal in signals:
            symbol = signal['symbol']
            if symbol not in aggregated:
                aggregated[symbol] = {
                    'buy_votes': 0,
                    'sell_votes': 0,
                    'holding': [],
                    'confidence_sum': 0.0
                }
            
            if signal['signal'] == 'BUY':
                aggregated[symbol]['buy_votes'] += signal.get('confidence', 0.5)
            elif signal['signal'] == 'SELL':
                aggregated[symbol]['sell_votes'] += signal.get('confidence', 0.5)
            
            aggregated[symbol]['holding'].append(signal)
            aggregated[symbol]['confidence_sum'] += signal.get('confidence', 0.5)
        
        return aggregated
    
    def make_decision(self, symbol: str, data: Dict, aggregated: Dict, current_portfolio: List[Dict] = None) -> Optional[Dict]:
        """Decidir: BUY / SELL / HOLD baseado em múltiplas estratégias + Auditoria de Risco"""
        
        if symbol not in aggregated:
            return None
        
        agg = aggregated[symbol]
        qty = data.get('qty', 0)
        current_price = data.get('current', 0)
        
        # 1. SOCIAL INTELLIGENCE (Sentiment Check) - Harvested early to inform Kelly rebalancing
        social_sentiment = self.social_intel.harvest_sentiment(symbol)
        social_score = social_sentiment.get('score', 0.0)
        
        # Calcular força do sinal
        buy_strength = agg['buy_votes']
        sell_strength = agg['sell_votes']
        
        decision = None
        
        # Decisão de COMPRA
        if buy_strength > sell_strength and buy_strength >= self.min_confidence:
            # Verificar se já temos posição (evitar duplicação)
            if qty == 0:
                # Use PortfolioRebalancer for optimal size calculation (Kelly Criterion)
                cash = 1000.0  # Safe default cash for paper/live
                try:
                    account_info = self.alpaca_executor.get_account()
                    if account_info:
                        cash = float(account_info.get("cash", 1000.0))
                except Exception as e:
                    logger.warning(f"Failed to fetch account cash for Kelly calculation: {e}")
                
                # Fetch optimal Kelly allocations adjusted by real-time sentiment
                opt_alloc = self.rebalancer.get_optimal_allocations([symbol], cash, {symbol: social_score})
                symbol_alloc = opt_alloc.get(symbol, {})
                target_spend = symbol_alloc.get("target_cash", min(self.max_position_value, 100))
                
                # Absolute safety clamp to protect capital (limits max position spend to $250)
                max_spend = min(target_spend, self.max_position_value, 250)
                qty_to_buy = max(0.0001, max_spend / current_price)
                
                decision = {
                    'action': 'BUY',
                    'symbol': symbol,
                    'qty': round(qty_to_buy, 4),
                    'price': current_price,
                    'confidence': buy_strength,
                    'reason': f"Buy signal from {len(agg['holding'])} strategies (Kelly-Sentiment sized)",
                    'strategies': [s['strategy'] for s in agg['holding'] if s['signal'] == 'BUY']
                }
        
        # Decisão de VENDA
        elif sell_strength > buy_strength and sell_strength >= self.min_confidence:
            if qty > 0:
                decision = {
                    'action': 'SELL',
                    'symbol': symbol,
                    'qty': qty,  # Vender tudo
                    'price': current_price,
                    'confidence': sell_strength,
                    'reason': f"Sell signal from {len(agg['holding'])} strategies",
                    'strategies': [s['strategy'] for s in agg['holding'] if s['signal'] == 'SELL']
                }
        
        # Ajustar confiança baseado no sentimento social (Factor de 20%)
        if decision:
            if decision['action'] == 'BUY' and social_score < -0.5:
                logger.warning(f"⚠️ CONTRARIAN ALERT: Technical BUY for {symbol} but Social Sentiment is PANIC ({social_score})")
                decision['confidence'] *= 0.8 # Reduzir confiança
            elif decision['action'] == 'BUY' and social_score > 0.5:
                logger.info(f"🔥 SOCIAL BOOST: High Bullish sentiment for {symbol} ({social_score})")
                decision['confidence'] *= 1.1 # Aumentar confiança
        
        # 4. AUDITORIA DE RISCO (Multi-Agent Sentinel)
        if decision and current_portfolio:
            macro_score = self.macro_sentiment.get('score', 0.0)
            approved, reason = self.risk_manager.audit_trade(decision, current_portfolio, macro_score)
            
            if not approved:
                print(f"🛡️  SENTINEL VETO: {symbol} | {reason}")
                return None
            else:
                print(f"✅ SENTINEL APPROVED: {symbol}")
                decision['reason'] += f" | Risk Approved: {reason}"
        
        return decision
    
    def execute_decision(self, decision: Dict) -> bool:
        """Executar decisão via AlpacaClient unificado"""
        if not decision:
            return False
        
        try:
            order = self.client.submit_order(
                symbol=decision['symbol'],
                qty=decision['qty'],
                side=decision['action'].lower(),
                order_type='market'
            )
            
            if order:
                order_id = order.get('id')
                print(f"✅ Order submitted: {decision['action']} {decision['qty']} {decision['symbol']} | ID: {order_id}")
                print(f"   Initial Status: {order.get('status')}")
                
                # WAIT FOR FILL (market orders should fill quickly)
                max_wait = 15  # seconds
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    # Check order status
                    if hasattr(self.client, 'session'):
                        try:
                            check_resp = self.client.session.get(
                                f"{self.client.base_url}/v2/orders/{order_id}", 
                                timeout=10
                            )
                            if check_resp.status_code == 200:
                                order_status = check_resp.json()
                                status = order_status.get('status')
                                
                                if status == 'filled':
                                    filled_price = float(order_status.get('filled_avg_price', 0))
                                    filled_qty = float(order_status.get('filled_qty', 0))
                                    print(f"   ✅ FILLED: {filled_qty} @ ${filled_price:.2f}")
                                    
                                    # Print execution details
                                    print(f"✅ EXECUTED: {decision['action'].upper()} {filled_qty} {decision['symbol']} @ ${filled_price:.2f}")
                                    print(f"   Reason: {decision['reason']}")
                                    print(f"   Strategies: {', '.join(decision['strategies'])}")
                                    
                                    # ENVIAR NOTIFICAÇÃO DISCORD
                                    if self.notify_callback:
                                        msg = f"🚨 **TRADE EXECUTED**\n"
                                        msg += f"**Action:** {decision['action']}\n"
                                        msg += f"**Symbol:** {decision['symbol']}\n"
                                        msg += f"**Qty:** {filled_qty}\n"
                                        msg += f"**Price:** ${filled_price:.2f}\n"
                                        msg += f"**Reason:** {decision['reason']}\n"
                                        msg += f"**Strategies:** {', '.join(decision['strategies'])}"
                                        self.notify_callback(msg)
                                    
                                    return True
                                    
                                elif status in ['canceled', 'expired', 'rejected']:
                                    print(f"   ❌ Order {status}!")
                                    return False
                        except Exception as e:
                            print(f"   ⚠️ Status check error: {e}")
                    
                    time.sleep(2)  # Wait 2 seconds before retrying
                
                # Timeout
                print(f"   ⏳ Order still pending after {max_wait}s")
                return False
            else:
                print(f"❌ FAILED to execute: {decision}")
                return False
                
        except Exception as e:
            print(f"❌ Error executing decision: {e}")
            return False
    
    def run_cycle(self, prices: Dict):
        """Executar um ciclo completo: sinais → agregação → decisão → execução"""
        print(f"\n{'='*60}")
        print(f"STRATEGY ENGINE CYCLE - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*60}")
        
        # 0. Atualizar sentimento macro antes de processar sinais
        self.update_macro_sentiment()
        
        # 1. Obter sinais de todas as estratégias
        signals = self.get_all_signals(prices)
        print(f"✅ Got {len(signals)} signals from {len(self.strategies)} strategies")
        
        if not signals:
            print("No signals generated. Holding positions.")
            return
        
        # 2. Agregar sinais por símbolo
        aggregated = self.aggregate_signals(signals)
        print(f"✅ Aggregated signals for {len(aggregated)} symbols")
        
        # 3. Tomar decisões e executar
        executed = 0
        
        # Build portfolio list for risk auditing
        current_portfolio = []
        for s, d in prices.items():
            if d.get('qty', 0) > 0:
                current_portfolio.append({
                    'symbol': s,
                    'market_value': d.get('qty', 0) * d.get('current', 0)
                })

        for symbol, data in prices.items():
            decision = self.make_decision(symbol, data, aggregated, current_portfolio=current_portfolio)
            if decision:
                if self.execute_decision(decision):
                    executed += 1
        
        print(f"✅ Executed {executed} trades")
        return executed


# Exemplo de uso
if __name__ == "__main__":
    from strategy_first_hour import FirstHourBreakoutStrategy
    from strategy_ema_cross import EMAStrategy
    
    # Criar engine
    engine = StrategyEngine()
    
    # Registar estratégias
    engine.register_strategy("FirstHourBreakout", FirstHourBreakoutStrategy())
    engine.register_strategy("EMACross", EMAStrategy())
    # engine.register_strategy("RSIReversal", RSIStrategy())  # TODO
    
    # Simular ciclo com preços atuais
    print("\nTesting StrategyEngine...")
    positions = engine.client.get_positions()
    
    if positions:
        engine.run_cycle(positions)
    else:
        print("No positions to analyze")
