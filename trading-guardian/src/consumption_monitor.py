#!/usr/bin/env python3
import os
import json
import time
import subprocess
from datetime import datetime
import sys

# Add project src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from discord_retry import send_trade_notification # We'll reuse the logic or create a generic one

def send_alert(agent_name: str, spend: float, session_id: str):
    """Sends a consumption alert to Discord"""
    # Reuse the discord_retry logic but with alert format
    webhook_path = os.path.expanduser("~/.openclaw/secrets/discord_webhook")
    if not os.path.exists(webhook_path): return
    with open(webhook_path, 'r') as f: url = f.read().strip()
    
    import requests
    payload = {
        "embeds": [{
            "title": "🚨 ALERTA DE CONSUMO IA",
            "color": 0xff9900, # Orange
            "fields": [
                {"name": "🤖 Agente", "value": agent_name, "inline": True},
                {"name": "💰 Gasto Atual", "value": f"${spend:.4f}", "inline": True},
                {"name": "🆔 Sessão", "value": session_id[:12] + "...", "inline": False}
            ],
            "description": "Uma sessão está a consumir tokens acima do esperado. Verifica o OpenClaw.",
            "timestamp": datetime.now().isoformat()
        }]
    }
    requests.post(url, json=payload)

def check_consumption():
    """Queries Postgres for high-spend sessions"""
    query = """
    SELECT end_user, SUM(spend) as total_spend 
    FROM "LiteLLM_SpendLogs" 
    WHERE "startTime" >= NOW() - INTERVAL '1 hour' 
    GROUP BY end_user 
    HAVING SUM(spend) > 0.15;
    """
    try:
        cmd = ["docker", "exec", "litellm-proxy-db-1", "psql", "-U", "llmproxy", "-d", "litellm", "-t", "-c", query]
        result = subprocess.run(cmd, capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            if '|' in line:
                user_json, spend = line.split('|')
                spend = float(spend.strip())
                user_data = json.loads(user_json.strip())
                session_id = user_data.get("session_id", "Unknown")
                
                print(f"⚠️ High spend detected: {session_id} - ${spend}")
                send_alert("OpenClaw/Hermes", spend, session_id)
                
    except Exception as e:
        print(f"Error checking consumption: {e}")

if __name__ == "__main__":
    print("🚀 Sentinela de Consumo Ativado...")
    check_consumption()
