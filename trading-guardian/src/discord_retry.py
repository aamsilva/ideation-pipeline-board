"""
Discord Integration - Rate Limit Handler + Trade Notifications
Sends rich embeds to Discord webhook for immediate trade notifications
"""

import os
import json
import time
import requests
from typing import Dict, Any, Callable, Optional


# ========== RETRY MECHANISM ==========

def discord_retry(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 2.0,
    **kwargs
) -> Any:
    """
    Execute function with exponential backoff retry for Discord 429 errors.
    
    Args:
        func: Function to call (e.g., send_message)
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each retry)
        *args, **kwargs: Arguments to pass to func
    
    Returns:
        Result of successful function call
    
    Raises:
        Exception: If all retries fail
    """
    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "429" in error_str or "rate limit" in error_str
            
            if is_rate_limit and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"⚠️ Discord 429 Rate Limit - Retry {attempt + 1}/{max_retries} in {delay}s")
                time.sleep(delay)
                continue
            else:
                raise
    
    raise Exception(f"Failed after {max_retries} retries")


# ========== WEBHOOK NOTIFICATIONS ==========

def _get_webhook_url() -> Optional[str]:
    """Load Discord webhook URL from secrets file"""
    webhook_path = os.path.expanduser("~/.openclaw/secrets/discord_webhook")
    if os.path.exists(webhook_path):
        with open(webhook_path, 'r') as f:
            return f.read().strip()
    return None


def send_trade_notification(trade_data: Dict, success: bool, result: Dict) -> bool:
    """
    Send immediate Discord notification after trade execution
    
    Args:
        trade_data: Dict with keys: symbol, qty, price, strategy_name, confidence, side
        success: Whether the trade was successful
        result: Result dict from execution (contains order_id, status, etc.)
    
    Returns:
        True if notification sent successfully, False otherwise
    """
    webhook_url = _get_webhook_url()
    if not webhook_url:
        print("⚠️ Discord webhook URL not found")
        return False
    
    # Determine emoji and color based on success
    if success:
        emoji = "✅"
        title = "TRADE EXECUTED"
        color = 0x00ff00  # Green
    else:
        emoji = "❌"
        title = "TRADE FAILED"
        color = 0xff0000  # Red
    
    # Build embed
    embed = {
        "title": f"{emoji} {title}",
        "color": color,
        "fields": [
            {
                "name": "📈 Symbol",
                "value": trade_data.get('symbol', 'N/A'),
                "inline": True
            },
            {
                "name": "🔢 Quantity",
                "value": f"{trade_data.get('qty', 0):.4f}",
                "inline": True
            },
            {
                "name": "💰 Price",
                "value": f"${trade_data.get('price', 0):.2f}" if trade_data.get('price') else "Market",
                "inline": True
            },
            {
                "name": "⚙️ Strategy",
                "value": trade_data.get('strategy_name', 'unknown'),
                "inline": True
            },
            {
                "name": "📊 Confidence",
                "value": f"{trade_data.get('confidence', 0):.2f}" if trade_data.get('confidence') else "N/A",
                "inline": True
            },
            {
                "name": "📋 Side",
                "value": trade_data.get('side', 'buy').upper(),
                "inline": True
            }
        ],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "footer": {
            "text": "Trading Guardian v0.12.0 | Tier-1 Grade"
        }
    }
    
    # Add order ID if available
    if result and result.get('order_id'):
        embed["fields"].append({
            "name": "🆔 Order ID",
            "value": result.get('order_id')[:8] + "...",
            "inline": False
        })
    
    # Add error message if failed
    if not success and result and result.get('error'):
        embed["fields"].append({
            "name": "❌ Error",
            "value": result.get('error', 'Unknown error')[:200],
            "inline": False
        })
    
    payload = {
        "embeds": [embed],
        "username": "Trading Guardian",
        "avatar_url": "https://i.imgur.com/4XnGQvZ.png"  # Optional: Guardian icon
    }
    
    # Send with retry
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 204 or response.status_code == 200:
            print(f"✅ Discord notification sent: {title}")
            return True
        elif response.status_code == 429:
            print(f"⚠️ Discord rate limit (429), retrying...")
            time.sleep(2)
            return send_trade_notification(trade_data, success, result)  # Retry once
        else:
            print(f"❌ Discord notification failed: {response.status_code} - {response.text[:100]}")
            return False
            
    except Exception as e:
        print(f"❌ Discord notification error: {e}")
        return False


def send_health_notification(health_data: Dict) -> bool:
    """
    Send health status notification to Discord
    
    Args:
        health_data: Dict from HealthMonitor.check_health()
    
    Returns:
        True if sent successfully
    """
    webhook_url = _get_webhook_url()
    if not webhook_url:
        return False
    
    score = health_data.get('overall_score', 0)
    
    # Color based on score
    if score >= 80:
        color = 0x00ff00  # Green
        status_emoji = "✅"
    elif score >= 50:
        color = 0xffff00  # Yellow
        status_emoji = "⚠️"
    else:
        color = 0xff0000  # Red
        status_emoji = "❌"
    
    embed = {
        "title": f"{status_emoji} Guardian Health Check",
        "color": color,
        "fields": [
            {
                "name": "🏥 Overall Score",
                "value": f"{score:.1f}/100",
                "inline": True
            },
            {
                "name": "📊 Status",
                "value": health_data.get('status', 'unknown').upper(),
                "inline": True
            },
            {
                "name": "📈 Total Trades",
                "value": str(health_data.get('metrics', {}).get('total_trades', 0)),
                "inline": True
            },
            {
                "name": "✅ Success Rate",
                "value": f"{health_data.get('metrics', {}).get('success_rate', 0):.1f}%",
                "inline": True
            }
        ],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "footer": {
            "text": "Trading Guardian | Health Monitor"
        }
    }
    
    payload = {"embeds": [embed]}
    
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return response.status_code in [200, 204]
    except Exception:
        return False


# ========== USAGE EXAMPLE ==========

if __name__ == "__main__":
    # Test trade notification
    test_trade = {
        "symbol": "AAPL",
        "qty": 10.0,
        "price": 150.50,
        "strategy_name": "bollinger",
        "confidence": 0.85,
        "side": "buy"
    }
    
    test_result = {
        "order_id": "sim_test_12345",
        "status": "filled",
        "filled_price": 150.50
    }
    
    print("Testing Discord trade notification...")
    send_trade_notification(test_trade, success=True, result=test_result)
    
    print("\nTesting health notification...")
    test_health = {
        "overall_score": 95.0,
        "status": "healthy",
        "metrics": {
            "total_trades": 10,
            "success_rate": 90.0
        }
    }
    send_health_notification(test_health)
