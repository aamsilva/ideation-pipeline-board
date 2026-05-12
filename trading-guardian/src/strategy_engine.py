#!/usr/bin/env python3
"""
Strategy Engine - Central Coordinator
Recebe sinais de TODAS as estratégias e decide: BUY / SELL / HOLD
"""

from alpaca_executor import get_executor
from typing import Dict, List, Optional
from datetime import datetime

class StrategyEngine:
    """Motor central que coordena todas as estratégias"""
    
    def __init__(self, use_live: bool = False):
        self.client = get_executor(use_live=use_live)
        self.strategies = {}  # {name: strategy_instance}
        self.max_position_value = 500  # Max $500 per position (live)
        self.min_confidence = 0.55  # Lowered from 0.7 for higher trade frequency
        self.notify_callback = None  # Callback for notifications
        self.macro_sentiment = {"score": 0.0, "bias": "neutral", "reason": "Initial state"}
        
        # Level 4.5: Multi-Agent Risk Management
        from risk_manager import SentinelRiskManager
        self.risk_manager = SentinelRiskManager()

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
        
        # Calcular força do sinal
        buy_strength = agg['buy_votes']
        sell_strength = agg['sell_votes']
        
        decision = None
        
        # Decisão de COMPRA
        if buy_strength > sell_strength and buy_strength >= self.min_confidence:
            # Verificar se já temos posição (evitar duplicação)
            if qty == 0:
                # Calcular quantidade baseada em risco
                max_spend = min(self.max_position_value, 100)  # Cap at $100 for safety
                qty_to_buy = max(0.01, max_spend / current_price)
                
                decision = {
                    'action': 'BUY',
                    'symbol': symbol,
                    'qty': round(qty_to_buy, 4),
                    'price': current_price,
                    'confidence': buy_strength,
                    'reason': f"Buy signal from {len(agg['holding'])} strategies",
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
                print(f"✅ EXECUTED: {decision['action']} {decision['qty']} {decision['symbol']} @ ${decision['price']:.2f}")
                print(f"   Reason: {decision['reason']}")
                print(f"   Strategies: {', '.join(decision['strategies'])}")
                
                # ENVIAR NOTIFICAÇÃO DISCORD
                if self.notify_callback:
                    msg = f"🚨 **TRADE EXECUTED**\n"
                    msg += f"**Action:** {decision['action']}\n"
                    msg += f"**Symbol:** {decision['symbol']}\n"
                    msg += f"**Qty:** {decision['qty']}\n"
                    msg += f"**Price:** ${decision['price']:.2f}\n"
                    msg += f"**Reason:** {decision['reason']}\n"
                    msg += f"**Strategies:** {', '.join(decision['strategies'])}"
                    self.notify_callback(msg)
                
                return True
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
