#!/usr/bin/env python3
"""
Provider Health Monitor - Smart fallback with cooldown tracking and proactive DeepInfra switching.

Tracks OpenRouter failures, implements intelligent cooldowns, and proactively switches
to DeepInfra when free models are experiencing issues.
"""

import json
import os
import sqlite3
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from collections import deque
import threading

# Configuration
SCRIPT_DIR = Path("/Volumes/disco1tb/projects/hermes-scripts")
DB_PATH = SCRIPT_DIR / "provider_health.db"
LOG_PATH = SCRIPT_DIR / "provider_health.log"

# Provider configuration
PROVIDERS = {
    "openrouter": {
        "name": "OpenRouter",
        "type": "free",
        "models": [
            # FIXED: Removed failed qwen-2.5-7b-instruct:free
            "meta-llama/llama-3.1-8b-instruct:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "google/gemma-3-27b-it:free",
            "google/gemma-4-31b-it:free",
            "meta-llama/llama-3.3-70b-instruct:free",
            "anthropic/claude-3-haiku:free",
        ]
    },
    "deepinfra": {
        "name": "DeepInfra",
        "type": "paid",
        "models": [
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
        ],
        "fallback_model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
    },
    "synthetic": {
        "name": "Synthetic.new",
        "type": "free",  # FIXED: Now properly marked as free
        "models": ["hf:MiniMaxAI/MiniMax-M2.5"]
    }
}

# Thresholds
FAILURE_THRESHOLD = 3  # Failures before triggering cooldown
COOLDOWN_SECONDS = 60  # Base cooldown time
RATE_LIMIT_COOLDOWN = 120  # Cooldown for rate limits
SERVER_ERROR_COOLDOWN = 30  # Cooldown for server errors
PROACTIVE_SWITCH_THRESHOLD = 0.4  # 40% failure rate triggers proactive switch
WINDOW_SIZE = 20  # Track last N requests for failure rate calculation

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ProviderHealth:
    """Health metrics for a provider."""
    provider: str
    model: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limits: int = 0
    server_errors: int = 0
    auth_errors: int = 0
    timeout_errors: int = 0
    other_errors: int = 0
    last_failure: Optional[float] = None
    last_success: Optional[float] = None
    cooldown_until: Optional[float] = None
    consecutive_failures: int = 0
    failure_history: List[Dict] = field(default_factory=list)
    
    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests
    
    @property
    def is_healthy(self) -> bool:
        if self.cooldown_until and time.time() < self.cooldown_until:
            return False
        return self.failure_rate < PROACTIVE_SWITCH_THRESHOLD
    
    @property
    def should_proactive_switch(self) -> bool:
        """Check if we should proactively switch to backup."""
        if self.total_requests < 5:
            return False
        # Check recent failure rate in sliding window
        recent_failures = sum(1 for f in self.failure_history[-WINDOW_SIZE:] if f.get("failed", False))
        recent_rate = recent_failures / min(len(self.failure_history[-WINDOW_SIZE:]), WINDOW_SIZE)
        return recent_rate > PROACTIVE_SWITCH_THRESHOLD


class ProviderHealthMonitor:
    """Monitors provider health and manages fallback logic."""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()
        self._lock = threading.Lock()
        self._health_cache: Dict[str, ProviderHealth] = {}
        self._load_cache()
        
    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS provider_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                error_type TEXT,
                error_message TEXT,
                status_code INTEGER,
                latency_ms REAL,
                UNIQUE(provider, model, timestamp, event_type)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS provider_stats (
                provider TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                total_requests INTEGER DEFAULT 0,
                successful_requests INTEGER DEFAULT 0,
                failed_requests INTEGER DEFAULT 0,
                rate_limits INTEGER DEFAULT 0,
                server_errors INTEGER DEFAULT 0,
                auth_errors INTEGER DEFAULT 0,
                timeout_errors INTEGER DEFAULT 0,
                other_errors INTEGER DEFAULT 0,
                last_failure REAL,
                last_success REAL,
                cooldown_until REAL,
                consecutive_failures INTEGER DEFAULT 0,
                failure_history TEXT DEFAULT '[]',
                updated_at REAL DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_provider_timestamp 
            ON provider_health(provider, timestamp)
        """)
        
        conn.commit()
        conn.close()
        
    def _load_cache(self):
        """Load health data into memory cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM provider_stats")
        rows = cursor.fetchall()
        
        for row in rows:
            self._health_cache[f"{row[0]}:{row[1]}"] = ProviderHealth(
                provider=row[0],
                model=row[1],
                total_requests=row[2],
                successful_requests=row[3],
                failed_requests=row[4],
                rate_limits=row[5],
                server_errors=row[6],
                auth_errors=row[7],
                timeout_errors=row[8],
                other_errors=row[9],
                last_failure=row[10],
                last_success=row[11],
                cooldown_until=row[12],
                consecutive_failures=row[13],
                failure_history=json.loads(row[14]) if row[14] else []
            )
        
        conn.close()
        logger.info(f"Loaded {len(self._health_cache)} provider health records")
        
    def _save_to_db(self, health: ProviderHealth):
        """Save health record to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO provider_stats 
            (provider, model, total_requests, successful_requests, failed_requests,
             rate_limits, server_errors, auth_errors, timeout_errors, other_errors,
             last_failure, last_success, cooldown_until, consecutive_failures,
             failure_history, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            health.provider, health.model, health.total_requests,
            health.successful_requests, health.failed_requests,
            health.rate_limits, health.server_errors, health.auth_errors,
            health.timeout_errors, health.other_errors,
            health.last_failure, health.last_success, health.cooldown_until,
            health.consecutive_failures, json.dumps(health.failure_history),
            time.time()
        ))
        
        conn.commit()
        conn.close()
        
    def record_request(self, provider: str, model: str, success: bool,
                      error_type: Optional[str] = None,
                      error_message: Optional[str] = None,
                      status_code: Optional[int] = None,
                      latency_ms: Optional[float] = None):
        """Record a request result."""
        with self._lock:
            key = f"{provider}:{model}"
            timestamp = time.time()
            
            if key not in self._health_cache:
                self._health_cache[key] = ProviderHealth(provider=provider, model=model)
            
            health = self._health_cache[key]
            health.total_requests += 1
            
            # Record event in history
            event = {
                "timestamp": timestamp,
                "success": success,
                "error_type": error_type,
                "status_code": status_code,
                "latency_ms": latency_ms
            }
            health.failure_history.append(event)
            
            # Keep only recent history
            if len(health.failure_history) > WINDOW_SIZE * 2:
                health.failure_history = health.failure_history[-WINDOW_SIZE:]
            
            if success:
                health.successful_requests += 1
                health.last_success = timestamp
                health.consecutive_failures = 0
                health.cooldown_until = None
            else:
                health.failed_requests += 1
                health.last_failure = timestamp
                health.consecutive_failures += 1
                
                # Categorize error
                if error_type == "rate_limit":
                    health.rate_limits += 1
                    health.cooldown_until = timestamp + RATE_LIMIT_COOLDOWN
                elif error_type == "server_error":
                    health.server_errors += 1
                    health.cooldown_until = timestamp + SERVER_ERROR_COOLDOWN
                elif error_type == "auth":
                    health.auth_errors += 1
                elif error_type == "timeout":
                    health.timeout_errors += 1
                    health.cooldown_until = timestamp + COOLDOWN_SECONDS
                else:
                    health.other_errors += 1
                    
                # Apply cooldown after threshold failures
                if health.consecutive_failures >= FAILURE_THRESHOLD:
                    health.cooldown_until = timestamp + COOLDOWN_SECONDS
                    logger.warning(
                        f"Provider {provider}/{model} cooldown triggered "
                        f"({health.consecutive_failures} consecutive failures)"
                    )
            
            # Log the event
            cursor = conn.cursor() if 'conn' in dir() else None
            if cursor:
                cursor.execute("""
                    INSERT INTO provider_health 
                    (provider, model, timestamp, event_type, error_type, 
                     error_message, status_code, latency_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (provider, model, timestamp, "success" if success else "failure",
                      error_type, error_message, status_code, latency_ms))
            
            self._save_to_db(health)
            
    def get_recommended_provider(self, preferred_type: str = "free") -> Dict[str, Any]:
        """
        Get the recommended provider based on health metrics.
        
        Returns dict with provider, model, base_url, and reason.
        """
        with self._lock:
            current_time = time.time()
            recommendations = []
            
            # Default to free provider if no health data
            if preferred_type == "free":
                # Check if we have any health data
                has_any_health = any(
                    h.total_requests > 0 
                    for h in self._health_cache.values()
                    if "openrouter" in h.provider
                )
                
                if not has_any_health:
                    # No data yet - default to first free model
                    return {
                        "provider": "openrouter",
                        "model": PROVIDERS["openrouter"]["models"][0],
                        "base_url": "https://openrouter.ai/api/v1",
                        "reason": "No health data - defaulting to free provider"
                    }
                
                for model in PROVIDERS["openrouter"]["models"]:
                    key = f"openrouter:{model}"
                    if key in self._health_cache:
                        health = self._health_cache[key]
                        
                        # Skip if in cooldown
                        if health.cooldown_until and current_time < health.cooldown_until:
                            continue
                        
                        # Skip if too many failures
                        if health.should_proactive_switch:
                            continue
                        
                        recommendations.append({
                            "provider": "openrouter",
                            "model": model,
                            "health": health,
                            "score": health.successful_requests - (health.failed_requests * 2)
                        })
                
                # Sort by score
                recommendations.sort(key=lambda x: x["score"], reverse=True)
                
                if recommendations:
                    return {
                        "provider": "openrouter",
                        "model": recommendations[0]["model"],
                        "base_url": "https://openrouter.ai/api/v1",
                        "reason": f"Healthy free provider (success rate: {recommendations[0]['health'].successful_requests}/{recommendations[0]['health'].total_requests})"
                    }
                
                # All OpenRouter free providers failed - try Synthetic.new (free) first
                if "synthetic" in PROVIDERS and PROVIDERS["synthetic"]["type"] == "free":
                    return {
                        "provider": "synthetic",
                        "model": PROVIDERS["synthetic"]["models"][0],
                        "base_url": "https://api.synthetic.new/v1",
                        "reason": "OpenRouter free providers exhausted - using Synthetic.new (free)"
                    }
                
                # Last resort: DeepInfra (paid)
                return self._get_deepinfra_recommendation()
            
            return self._get_deepinfra_recommendation()
    
    def _get_deepinfra_recommendation(self) -> Dict[str, Any]:
        """Get DeepInfra as fallback recommendation."""
        return {
            "provider": "deepinfra",
            "model": PROVIDERS["deepinfra"]["models"][0],
            "base_url": "https://api.deepinfra.com/v1/openai",
            "reason": "Free providers exhausted or unhealthy - using DeepInfra"
        }
    
    def check_and_switch(self, current_provider: str, current_model: str) -> Optional[Dict[str, Any]]:
        """
        Check if we should switch from current provider.
        Returns new provider config if switch is recommended.
        """
        key = f"{current_provider}:{current_model}"
        
        if key in self._health_cache:
            health = self._health_cache[key]
            
            # Check if in cooldown
            if health.cooldown_until and time.time() < health.cooldown_until:
                remaining = int(health.cooldown_until - time.time())
                logger.info(f"Provider {current_provider}/{current_model} in cooldown ({remaining}s remaining)")
                return self._get_deepinfra_recommendation()
            
            # Check if proactive switch needed
            if health.should_proactive_switch:
                logger.warning(
                    f"Proactive switch triggered for {current_provider}/{current_model} "
                    f"(failure rate: {health.failure_rate:.1%})"
                )
                return self._get_deepinfra_recommendation()
        
        return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status of all providers."""
        with self._lock:
            status = {
                "timestamp": datetime.now().isoformat(),
                "providers": {}
            }
            
            for provider_name, config in PROVIDERS.items():
                for model in config["models"]:
                    key = f"{provider_name}:{model}"
                    if key in self._health_cache:
                        health = self._health_cache[key]
                        status["providers"][key] = {
                            "total_requests": health.total_requests,
                            "successful": health.successful_requests,
                            "failed": health.failed_requests,
                            "failure_rate": f"{health.failure_rate:.1%}",
                            "in_cooldown": health.cooldown_until and time.time() < health.cooldown_until,
                            "consecutive_failures": health.consecutive_failures,
                            "last_failure": datetime.fromtimestamp(health.last_failure).isoformat() if health.last_failure else None,
                            "last_success": datetime.fromtimestamp(health.last_success).isoformat() if health.last_success else None
                        }
            
            return status
    
    def force_switch_to_deepinfra(self) -> Dict[str, Any]:
        """Force switch to DeepInfra (for manual intervention)."""
        logger.info("Forcing switch to DeepInfra")
        return {
            "provider": "deepinfra",
            "model": PROVIDERS["deepinfra"]["models"][0],
            "base_url": "https://api.deepinfra.com/v1/openai",
            "reason": "Manual forced switch to DeepInfra"
        }
    
    def reset_provider(self, provider: str, model: str):
        """Reset health stats for a provider."""
        with self._lock:
            key = f"{provider}:{model}"
            if key in self._health_cache:
                self._health_cache[key] = ProviderHealth(provider=provider, model=model)
                self._save_to_db(self._health_cache[key])
                logger.info(f"Reset health stats for {provider}/{model}")


def main():
    """CLI interface for the provider health monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Provider Health Monitor")
    parser.add_argument("--status", action="store_true", help="Show provider health status")
    parser.add_argument("--record", nargs=4, metavar=("PROVIDER", "MODEL", "SUCCESS", "ERROR_TYPE"),
                       help="Record a request (SUCCESS=true/false)")
    parser.add_argument("--check", nargs=2, metavar=("PROVIDER", "MODEL"),
                       help="Check if switch is recommended")
    parser.add_argument("--recommend", choices=["free", "paid"], default="free",
                       help="Get recommended provider")
    parser.add_argument("--reset", nargs=2, metavar=("PROVIDER", "MODEL"),
                       help="Reset provider health stats")
    parser.add_argument("--force-deepinfra", action="store_true",
                       help="Force switch to DeepInfra")
    
    args = parser.parse_args()
    monitor = ProviderHealthMonitor()
    
    if args.status:
        status = monitor.get_health_status()
        print("\n" + "="*60)
        print("PROVIDER HEALTH STATUS")
        print("="*60)
        print(f"Updated: {status['timestamp']}\n")
        
        for key, data in status["providers"].items():
            print(f"📊 {key}")
            print(f"   Requests: {data['total_requests']} | Success: {data['successful']} | Failed: {data['failed']}")
            print(f"   Failure Rate: {data['failure_rate']} | Cooldown: {data['in_cooldown']}")
            print(f"   Consecutive Failures: {data['consecutive_failures']}")
            if data['last_failure']:
                print(f"   Last Failure: {data['last_failure']}")
            print()
        
    elif args.record:
        provider, model, success, error_type = args.record
        monitor.record_request(
            provider, model, 
            success=success.lower() == "true",
            error_type=error_type if error_type != "None" else None
        )
        print(f"Recorded: {provider}/{model} - {'SUCCESS' if success.lower() == 'true' else 'FAILURE'}")
        
    elif args.check:
        provider, model = args.check
        result = monitor.check_and_switch(provider, model)
        if result:
            print(f"Switch recommended: {result['provider']}/{result['model']}")
            print(f"Reason: {result['reason']}")
        else:
            print(f"No switch needed for {provider}/{model}")
            
    elif args.recommend:
        result = monitor.get_recommended_provider(args.recommend)
        print(f"Recommended: {result['provider']}/{result['model']}")
        print(f"Base URL: {result['base_url']}")
        print(f"Reason: {result['reason']}")
        
    elif args.reset:
        provider, model = args.reset
        monitor.reset_provider(provider, model)
        print(f"Reset {provider}/{model}")
        
    elif args.force_deepinfra:
        result = monitor.force_switch_to_deepinfra()
        print(f"Forced switch to: {result['provider']}/{result['model']}")
        print(f"Base URL: {result['base_url']}")


if __name__ == "__main__":
    main()