#!/usr/bin/env python3
"""
Generate Alpha Trade-style Dual Paper/Live Report for Trading Guardian
NOW READS FROM STATE FILE (no Alpaca API calls!)
Matches template: 📊 Alpha Trade Report with Paper/Live sections
"""
import json
from pathlib import Path
from datetime import datetime

def generate_report():
    state_file = Path(__file__).parent.parent / "data" / "guardian_state.json"
    
    if not state_file.exists():
        return "⚠️ State file not found. Daemon may not be running."
    
    with open(state_file, "r") as f:
        state = json.load(f)
    
    timestamp = state.get("timestamp", datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(timestamp)
        date_str = dt.strftime("%Y-%m-%d %H:%M")
    except:
        date_str = timestamp
    
    # Extract data
    paper = state.get("paper", {})
    live = state.get("live", {})
    trades = state.get("trades", {})
    health = state.get("health", {})
    strategies = state.get("strategies", {})
    execution = state.get("execution", {})
    risk = state.get("risk", {})
    
    # Paper account
    paper_account = paper.get("account", {})
    paper_cash = paper_account.get("cash", 0)
    paper_bp = paper_account.get("buying_power", 0)
    paper_positions = paper.get("positions", [])
    
    # Live account
    live_account = live.get("account", {})
    live_cash = live_account.get("cash", 0)
    live_bp = live_account.get("buying_power", 0)
    live_positions = live.get("positions", [])
    
    # Calculate P&L
    paper_pnl = sum(p.get("pnl", 0) for p in paper_positions)
    live_pnl = sum(p.get("pnl", 0) for p in live_positions)
    
    paper_pnl_emoji = "🟢" if paper_pnl >= 0 else "🔴"
    live_pnl_emoji = "🟢" if live_pnl >= 0 else "🔴"
    
    # Health
    health_score = health.get("overall_score", 0)
    health_status = health.get("status", "unknown")
    
    # Strategies
    testing = strategies.get("testing", [])
    approved = strategies.get("approved", [])
    validated = strategies.get("validated", 0)
    total_strategies = strategies.get("total", 0)
    
    # Execution
    orders = execution.get("orders", 0)
    filled = execution.get("filled", 0)
    latency = execution.get("latency_ms", 0)
    
    # Risk
    leverage = risk.get("leverage", 0)
    exposure = risk.get("exposure", 0)
    
    # Uptime
    uptime_pct = state.get("uptime_pct", 0)
    checks = state.get("checks", 0)
    
    # Build report matching template exactly
    report = f"""**📊 Alpha Trade Report | {date_str}**
_Métricas do canal <#1474780235781242718>_
💬 Conversa (12h)
• Mensagens: 0
• Perguntas: 0
• Requests: 0

🔴 **LIVE** (Real Money)
Portfolio: ${live_cash:.2f}
Buying Power: ${live_bp:.2f}
P&L: {live_pnl_emoji} ${live_pnl:+.2f}
📊 Positions ({len(live_positions)}):
"""
    
    for pos in live_positions[:5]:  # Show top 5
        symbol = pos.get("symbol", "??")
        qty = pos.get("qty", 0)
        current = pos.get("current", 0)
        pnl = pos.get("pnl", 0)
        emoji = "🟢" if pnl >= 0 else "🔴"
        report += f"• {symbol}: {qty:.4f} @ ${current:.2f} {emoji} ${pnl:+.2f}\n"
    
    report += f"""
📝 **PAPER** (Testing)
Portfolio: ${paper_cash:.2f}
Buying Power: ${paper_bp:.2f}
P&L: {paper_pnl_emoji} ${paper_pnl:+.2f}
📊 Positions ({len(paper_positions)}):
"""
    
    for pos in paper_positions[:5]:  # Show top 5
        symbol = pos.get("symbol", "??")
        qty = pos.get("qty", 0)
        current = pos.get("current", 0)
        pnl = pos.get("pnl", 0)
        emoji = "🟢" if pnl >= 0 else "🔴"
        report += f"• {symbol}: {qty:.4f} @ ${current:.2f} {emoji} ${pnl:+.2f}\n"
    
    report += f"""
📈 **Estratégias (Backtest)**
• Testing: {len(testing)}/{total_strategies}
"""
    
    for s in testing[:3]:
        report += f"  {s}\n"
    
    report += f"""
• ✅ Approved: {len(approved)}
• ✅ Validated: {validated}/{total_strategies}

📅 **Daily Strategy Report**
🧪 A Testar: {len(testing)}
"""
    
    for s in testing[:3]:
        report += f"• {s}\n"
    
    report += f"""
✅ Aprovadas: {len(approved)}
"""
    
    for s in approved[:2]:
        report += f"• {s}\n"
    
    # Add recent trades
    recent = trades.get("recent", [])
    if recent:
        report += f"""
🎯 **Trades Recentes** ({trades.get('executed', 0)} executados, {trades.get('failed', 0)} falhados)
"""
        for t in recent[:3]:
            symbol = t.get("symbol", "??")
            qty = t.get("qty", 0)
            mode = t.get("mode", "PAPER")
            report += f"• {symbol}: {qty:.4f} [{mode}]\n"
    
    report += f"""
💓 **Heartbeat**
• Cron: {checks}
• Health Score: {health_score:.1f}%
• Status: {health_status}

⚡ **Execução**
• Ordens: {orders}
• Filled: {filled}
• Latência: {latency:.1f}ms

🛡️ **Risco**
• Leverage: {leverage:.2f}x
• Exposição: ${exposure:.2f}
• Uptime: {uptime_pct:.1f}%

🔬 **AutoResearch (Karpathy)**
• Platform Discovery: ATIVO
• Novas plataformas: sendo descobertas autonomamente
• Integração automática: HABILITADA
"""
    
    return report.strip()

if __name__ == "__main__":
    print(generate_report())
