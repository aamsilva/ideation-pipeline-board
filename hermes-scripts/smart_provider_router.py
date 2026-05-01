#!/usr/bin/env python3
"""
Smart Provider Router - Intercepts OpenAI API calls and manages provider failover.

This module wraps OpenAI clients to provide:
- Automatic failure tracking via ProviderHealthMonitor
- Proactive switching to DeepInfra when OpenRouter fails
- Automatic recovery when OpenRouter becomes healthy again
- Budget-aware routing (prefer free, use paid as fallback)
"""

import os
import time
import logging
from typing import Optional, Dict, Any, Callable, Union
from functools import wraps
from pathlib import Path

# Add parent to path
import sys
SCRIPT_DIR = Path("/Volumes/disco1tb/projects/hermes-scripts")
sys.path.insert(0, str(SCRIPT_DIR))

from provider_health_monitor import ProviderHealthMonitor, PROVIDERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SmartProviderRouter:
    """
    Intelligent provider router that manages failover and recovery.
    
    Usage:
        router = SmartProviderRouter()
        client = router.wrap_client(original_client)
        
        # Or use directly for single calls
        response = router.execute_with_fallback(
            lambda: client.chat.completions.create(...)
        )
    """
    
    def __init__(self, budget_limit_eur: float = 40.0):
        self.budget_limit_eur = budget_limit_eur
        self.health_monitor = ProviderHealthMonitor()
        
        # Current active provider - DEFAULT TO WORKING FREE MODEL
        self._current_provider = "openrouter"
        self._current_model = "meta-llama/llama-3.1-8b-instruct:free"  # Fixed: was qwen-2.5-7b (404)
        
        # Track if we manually switched to paid
        self._manual_paid_switch = False
        self._paid_switch_time: Optional[float] = None
        
        # Recovery tracking
        self._openrouter_healthy_again_time: Optional[float] = None
        self._recovery_delay_seconds = 30  # Wait 30s before switching back to free
        
        # Initialize with recommended provider
        self._initialize_provider()
        
    def _initialize_provider(self):
        """Initialize with best available provider."""
        # Default to OpenRouter free models if no health data
        self._current_provider = "openrouter"
        self._current_model = "meta-llama/llama-3.1-8b-instruct:free"  # Fixed: was qwen-2.5-7b (404)
        
        # Check if health data suggests a different provider
        recommendation = self.health_monitor.get_recommended_provider("free")
        if recommendation and recommendation.get("provider") == "deepinfra":
            # OpenRouter is unhealthy, use DeepInfra
            self._current_provider = recommendation["provider"]
            self._current_model = recommendation["model"]
            
        logger.info(f"Initialized with provider: {self._current_provider}/{self._current_model}")
    
    @property
    def current_config(self) -> Dict[str, str]:
        """Get current provider configuration."""
        config = {
            "provider": self._current_provider,
            "model": self._current_model,
        }
        
        if self._current_provider == "deepinfra":
            config["base_url"] = "https://api.deepinfra.com/v1/openai"
            config["api_key"] = os.environ.get("DEEPINFRA_API_KEY", "")
        else:
            config["base_url"] = "https://openrouter.ai/api/v1"
            config["api_key"] = os.environ.get("OPENROUTER_API_KEY", "")
        
        return config
    
    def _should_switch_to_paid(self) -> bool:
        """Determine if we should switch to paid provider."""
        # Check OpenRouter health
        check_result = self.health_monitor.check_and_switch("openrouter", self._current_model)
        
        if check_result and check_result["provider"] == "deepinfra":
            # Check budget
            from circuit_breaker import get_usage_stats
            stats = get_usage_stats()
            
            if stats["budget_remaining_usd"] > 1.0:  # Keep $1 buffer
                return True
                
        return False
    
    def _should_recover_to_free(self) -> bool:
        """Determine if we should switch back to free provider."""
        if self._current_provider != "deepinfra":
            return False
            
        # Check if we've waited long enough
        if self._paid_switch_time:
            elapsed = time.time() - self._paid_switch_time
            if elapsed < self._recovery_delay_seconds:
                return False
        
        # Check if OpenRouter is healthy
        for model in PROVIDERS["openrouter"]["models"]:
            key = f"openrouter:{model}"
            if key in self.health_monitor._health_cache:
                health = self.health_monitor._health_cache[key]
                if not health.should_proactive_switch and health.failure_rate < 0.3:
                    return True
                    
        return False
    
    def _get_client_for_provider(self, provider: str) -> Dict[str, str]:
        """Get client configuration for a specific provider."""
        if provider == "deepinfra":
            return {
                "base_url": "https://api.deepinfra.com/v1/openai",
                "api_key": os.environ.get("DEEPINFRA_API_KEY", ""),
                "model": PROVIDERS["deepinfra"]["models"][0]
            }
        else:
            return {
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": os.environ.get("OPENROUTER_API_KEY", ""),
                "model": self._current_model
            }
    
    def execute_with_fallback(
        self, 
        func: Callable,
        original_provider: str = "openrouter",
        original_model: str = "qwen/qwen-2.5-7b-instruct:free"
    ) -> Any:
        """
        Execute a function with automatic fallback.
        
        Args:
            func: The function to execute (e.g., lambda: client.chat.completions.create(...))
            original_provider: The provider to try first
            original_model: The model to try first
            
        Returns:
            The function result
            
        Raises:
            The last exception if all providers fail
        """
        start_time = time.time()
        last_error = None
        
        # Determine try order based on current state
        providers_to_try = []
        
        if self._current_provider == "deepinfra":
            # We're on paid - try to recover to free first
            if self._should_recover_to_free():
                providers_to_try.append(("openrouter", original_model))
            providers_to_try.append(("deepinfra", PROVIDERS["deepinfra"]["models"][0]))
        else:
            # We're on free - try it first
            providers_to_try.append(("openrouter", original_model))
            # Check if we should proactively switch
            if self._should_switch_to_paid():
                providers_to_try.append(("deepinfra", PROVIDERS["deepinfra"]["models"][0]))
        
        # Add any remaining providers
        for provider, model in providers_to_try:
            if (provider, model) not in providers_to_try:
                providers_to_try.append((provider, model))
        
        for provider, model in providers_to_try:
            try:
                logger.info(f"Trying provider: {provider}/{model}")
                
                # Record attempt
                self.health_monitor.record_request(
                    provider, model, 
                    success=False,  # Will update on success
                    error_type="attempt"
                )
                
                # Execute the function
                result = func()
                
                # Success! Record and update state
                latency_ms = (time.time() - start_time) * 1000
                self.health_monitor.record_request(
                    provider, model,
                    success=True,
                    latency_ms=latency_ms
                )
                
                # Update current provider
                self._current_provider = provider
                self._current_model = model
                
                if provider == "deepinfra":
                    self._paid_switch_time = time.time()
                else:
                    self._openrouter_healthy_again_time = None
                    self._paid_switch_time = None
                
                logger.info(f"Success with {provider}/{model} (latency: {latency_ms:.0f}ms)")
                return result
                
            except Exception as e:
                last_error = e
                error_type = self._classify_error(e)
                status_code = getattr(e, "status_code", None)
                
                # Record failure
                self.health_monitor.record_request(
                    provider, model,
                    success=False,
                    error_type=error_type,
                    error_message=str(e)[:200],
                    status_code=status_code
                )
                
                logger.warning(f"Provider {provider}/{model} failed: {error_type} - {str(e)[:100]}")
                
                # If rate limit, try next provider immediately
                if error_type == "rate_limit":
                    continue
                    
        # All providers failed
        raise last_error
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error type for health monitoring."""
        error_str = str(error).lower()
        
        if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
            return "rate_limit"
        elif "500" in error_str or "502" in error_str or "503" in error_str or "server error" in error_str:
            return "server_error"
        elif "401" in error_str or "403" in error_str or "unauthorized" in error_str or "forbidden" in error_str:
            return "auth"
        elif "timeout" in error_str or "timed out" in error_str:
            return "timeout"
        elif "404" in error_str or "not found" in error_str or "model not found" in error_str:
            return "model_not_found"
        
        return "other"
    
    def get_status(self) -> Dict[str, Any]:
        """Get current router status."""
        return {
            "current_provider": self._current_provider,
            "current_model": self._current_model,
            "config": self.current_config,
            "health": self.health_monitor.get_health_status(),
            "budget": self._get_budget_status()
        }
    
    def _get_budget_status(self) -> Dict[str, Any]:
        """Get budget status."""
        try:
            from circuit_breaker import get_usage_stats
            stats = get_usage_stats()
            return stats
        except:
            return {"error": "Circuit breaker not available"}
    
    def force_switch(self, provider: str):
        """Force switch to a specific provider."""
        if provider == "deepinfra":
            self._current_provider = "deepinfra"
            self._current_model = PROVIDERS["deepinfra"]["models"][0]
            self._paid_switch_time = time.time()
            logger.info(f"Forced switch to DeepInfra")
        else:
            self._current_provider = "openrouter"
            self._current_model = "qwen/qwen-2.5-7b-instruct:free"
            self._paid_switch_time = None
            logger.info(f"Forced switch to OpenRouter")


# Global router instance
_router: Optional[SmartProviderRouter] = None


def get_router() -> SmartProviderRouter:
    """Get or create the global router instance."""
    global _router
    if _router is None:
        _router = SmartProviderRouter()
    return _router


def wrap_openai_client(client, original_provider: str = "openrouter", original_model: str = "qwen/qwen-2.5-7b-instruct:free"):
    """
    Wrap an OpenAI client to automatically handle provider failover.
    
    This wraps the chat.completions.create method to use the smart router.
    """
    router = get_router()
    original_create = client.chat.completions.create
    
    @wraps(original_create)
    def wrapped_create(*args, **kwargs):
        return router.execute_with_fallback(
            lambda: original_create(*args, **kwargs),
            original_provider=original_provider,
            original_model=original_model
        )
    
    client.chat.completions.create = wrapped_create
    return client


def main():
    """CLI for router status and control."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Provider Router")
    parser.add_argument("--status", action="store_true", help="Show router status")
    parser.add_argument("--force", choices=["openrouter", "deepinfra"], help="Force provider switch")
    parser.add_argument("--health", action="store_true", help="Show provider health")
    
    args = parser.parse_args()
    router = get_router()
    
    if args.status:
        status = router.get_status()
        print("\n" + "="*60)
        print("SMART PROVIDER ROUTER STATUS")
        print("="*60)
        print(f"Current Provider: {status['current_provider']}")
        print(f"Current Model: {status['current_model']}")
        print(f"Base URL: {status['config']['base_url']}")
        print()
        
        # Budget status
        budget = status.get('budget', {})
        if 'error' not in budget:
            print(f"Budget Used: {budget.get('budget_used_pct', 0):.1f}%")
            print(f"Remaining: ${budget.get('budget_remaining_usd', 0):.2f}")
        
    elif args.force:
        router.force_switch(args.force)
        print(f"Forced switch to {args.force}")
        
    elif args.health:
        health = router.health_monitor.get_health_status()
        print("\n" + "="*60)
        print("PROVIDER HEALTH")
        print("="*60)
        print(f"Updated: {health['timestamp']}")
        
        for key, data in health.get('providers', {}).items():
            print(f"\n{key}:")
            print(f"  Requests: {data['total_requests']} | Success: {data['successful']} | Failed: {data['failed']}")
            print(f"  Failure Rate: {data['failure_rate']} | Cooldown: {data['in_cooldown']}")


if __name__ == "__main__":
    main()