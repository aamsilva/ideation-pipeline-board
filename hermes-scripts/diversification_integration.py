#!/usr/bin/env python3
"""
Diversification Integration Layer
==================================

Bridges aggressive_diversification.py with provider_api_proxy.py
for seamless intelligent model selection without disruption.

This module:
1. Hooks into existing proxy
2. Provides intelligent model selection
3. Records performance metrics
4. Enables hot-reload of models

Usage:
    python3 diversification_integration.py [--start-proxy]
"""

import os
import sys
import json
import time
import logging
import threading
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, field
from collections import deque

# Add scripts directory to path
SCRIPT_DIR = Path("/Volumes/disco1tb/projects/hermes-scripts")
sys.path.insert(0, str(SCRIPT_DIR))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(SCRIPT_DIR / "diversification.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DiversificationIntegration")

# Try to import aggressive diversification
try:
    from aggressive_diversification import (
        AggressiveDiversificationEngine,
        IntelligentModelSelector,
        AutonomousProviderDiscovery,
        MODEL_DATABASE,
        EXPANDED_PROVIDERS,
        TaskType,
        ModelCapability
    )
    DIVERSIFICATION_AVAILABLE = True
    logger.info("Aggressive diversification module loaded successfully")
except ImportError as e:
    DIVERSIFICATION_AVAILABLE = False
    logger.warning(f"Aggressive diversification not available: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# PERFORMANCE TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RequestMetrics:
    """Metrics for a single request"""
    model_id: str
    provider: str
    timestamp: float
    latency_ms: float
    success: bool
    tokens_input: int = 0
    tokens_output: int = 0
    error: Optional[str] = None


class PerformanceTracker:
    """Track and analyze request performance"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.model_stats: Dict[str, Dict] = {}
        self.provider_stats: Dict[str, Dict] = {}
        self._lock = threading.Lock()
        
    def record_request(self, model_id: str, provider: str, latency_ms: float,
                      success: bool, tokens_input: int = 0, tokens_output: int = 0,
                      error: Optional[str] = None):
        """Record a request for analytics"""
        with self._lock:
            metrics = RequestMetrics(
                model_id=model_id,
                provider=provider,
                timestamp=time.time(),
                latency_ms=latency_ms,
                success=success,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                error=error
            )
            self.metrics_history.append(metrics)
            
            # Update model stats
            if model_id not in self.model_stats:
                self.model_stats[model_id] = {
                    "total_requests": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_latency": 0,
                    "total_latency": 0
                }
            
            stats = self.model_stats[model_id]
            stats["total_requests"] += 1
            if success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
                
            stats["total_latency"] += latency_ms
            stats["avg_latency"] = stats["total_latency"] / stats["total_requests"]
            
            # Update provider stats
            if provider not in self.provider_stats:
                self.provider_stats[provider] = {
                    "total_requests": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_latency": 0
                }
            
            pstats = self.provider_stats[provider]
            pstats["total_requests"] += 1
            if success:
                pstats["successful"] += 1
            else:
                pstats["failed"] += 1
    
    def get_model_recommendations(self) -> List[Tuple[str, float]]:
        """Get model recommendations based on performance"""
        with self._lock:
            recommendations = []
            
            for model_id, stats in self.model_stats.items():
                if stats["total_requests"] >= 5:
                    success_rate = stats["successful"] / stats["total_requests"]
                    latency_score = max(0, 1 - stats["avg_latency"] / 10000)  # 10s = 0
                    
                    # Composite score
                    score = success_rate * 0.7 + latency_score * 0.3
                    recommendations.append((model_id, score))
            
            # Sort by score descending
            recommendations.sort(key=lambda x: x[1], reverse=True)
            return recommendations
    
    def get_stats_summary(self) -> Dict:
        """Get summary statistics"""
        with self._lock:
            total = len(self.metrics_history)
            if total == 0:
                return {"total_requests": 0}
            
            successful = sum(1 for m in self.metrics_history if m.success)
            avg_latency = sum(m.latency_ms for m in self.metrics_history) / total
            
            return {
                "total_requests": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": successful / total,
                "avg_latency_ms": avg_latency,
                "models": len(self.model_stats),
                "providers": len(self.provider_stats)
            }


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION WITH PROVIDER API PROXY
# ═══════════════════════════════════════════════════════════════════════════════

class DiversificationProxy:
    """
    Integration layer that wraps the existing provider API proxy
    with intelligent model selection.
    """
    
    def __init__(self):
        self.engine: Optional[AggressiveDiversificationEngine] = None
        self.selector: Optional[IntelligentModelSelector] = None
        self.tracker = PerformanceTracker()
        self.enabled = False
        
        # Model selection cache
        self.selection_cache: Dict[str, Tuple[str, float]] = {}  # prompt_hash -> (model_id, timestamp)
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize if diversification available
        if DIVERSIFICATION_AVAILABLE:
            try:
                self.engine = AggressiveDiversificationEngine()
                self.selector = self.engine.selector
                self.enabled = True
                logger.info("Diversification engine initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize diversification engine: {e}")
        else:
            # Use fallback mode with static model list
            logger.warning("Running in fallback mode - using static model list")
            self.enabled = False
    
    def select_model_for_prompt(self, prompt: str, context_length: int = 4000) -> str:
        """
        Intelligently select model based on prompt.
        This is the main entry point for model selection.
        """
        if not self.enabled or not self.selector:
            # Fallback to default model
            return "nvidia/nemotron-3-super-120b-a12b:free"
        
        try:
            # Check cache
            prompt_hash = hash(prompt[:500])  # Use first 500 chars for cache key
            if prompt_hash in self.selection_cache:
                cached_model, cached_time = self.selection_cache[prompt_hash]
                if time.time() - cached_time < self.cache_ttl:
                    return cached_model
            
            # Get model selection from engine
            model_id = self.engine.get_model_for_task(prompt, context_length)
            
            # Update cache
            self.selection_cache[prompt_hash] = (model_id, time.time())
            
            return model_id
            
        except Exception as e:
            logger.warning(f"Model selection failed: {e}, using fallback")
            return "nvidia/nemotron-3-super-120b-a12b:free"
    
    def record_request_performance(self, model_id: str, provider: str,
                                   latency_ms: float, success: bool,
                                   tokens_input: int = 0, tokens_output: int = 0,
                                   error: Optional[str] = None):
        """Record request performance for continuous learning"""
        self.tracker.record_request(
            model_id, provider, latency_ms, success,
            tokens_input, tokens_output, error
        )
        
        # Also update selector performance if available
        if self.enabled and self.selector:
            self.selector.record_performance(model_id, latency_ms, success, 
                                            tokens_input + tokens_output)
    
    def get_optimal_model(self, task_type: Optional[TaskType] = None) -> str:
        """Get optimal model for a specific task type"""
        if not self.enabled:
            return "nvidia/nemotron-3-super-120b-a12b:free"
        
        # Get task-specific prompts
        task_prompts = {
            TaskType.CODING: "Write a Python function to implement binary search with error handling",
            TaskType.REASONING: "Analyze the logical structure of this argument and identify any fallacies",
            TaskType.WRITING: "Write a creative story about artificial intelligence",
            TaskType.GENERAL: "What is the capital of France?",
        }
        
        prompt = task_prompts.get(task_type, task_prompts[TaskType.GENERAL])
        return self.select_model_for_prompt(prompt)
    
    def get_status(self) -> Dict:
        """Get current integration status"""
        stats = self.tracker.get_stats_summary()
        recommendations = self.tracker.get_model_recommendations()
        
        return {
            "enabled": self.enabled,
            "engine_available": DIVERSIFICATION_AVAILABLE,
            "performance": stats,
            "top_models": recommendations[:5],
            "active_models": self.engine.active_models if self.enabled else [],
            "free_models_count": len([m for m in MODEL_DATABASE.values() if m.is_free]) if DIVERSIFICATION_AVAILABLE else 0
        }
    
    def force_model_rotation(self):
        """Force rotation of models based on performance"""
        if self.enabled and self.engine:
            self.engine._rotate_models()
            logger.info("Forced model rotation based on performance")


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_diversification_proxy: Optional[DiversificationProxy] = None
_proxy_lock = threading.Lock()


def get_diversification_proxy() -> DiversificationProxy:
    """Get or create the global diversification proxy instance"""
    global _diversification_proxy
    
    with _proxy_lock:
        if _diversification_proxy is None:
            _diversification_proxy = DiversificationProxy()
        return _diversification_proxy


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Diversification Integration Layer")
    parser.add_argument("--status", action="store_true", help="Show integration status")
    parser.add_argument("--test-select", type=str, help="Test model selection for prompt")
    parser.add_argument("--rotate", action="store_true", help="Force model rotation")
    parser.add_argument("--models", action="store_true", help="List available models")
    parser.add_argument("--performance", action="store_true", help="Show performance stats")
    parser.add_argument("--discover", action="store_true", help="Force provider discovery")
    
    args = parser.parse_args()
    
    proxy = get_diversification_proxy()
    
    if args.status:
        status = proxy.get_status()
        print("\n" + "="*60)
        print("DIVERSIFICATION INTEGRATION STATUS")
        print("="*60)
        print(f"Enabled: {status['enabled']}")
        print(f"Engine Available: {status['engine_available']}")
        print(f"Free Models: {status['free_models_count']}")
        print(f"Active Models: {status['active_models'][:3]}...")
        
        perf = status['performance']
        print(f"\nPerformance:")
        print(f"  Total Requests: {perf.get('total_requests', 0)}")
        print(f"  Success Rate: {perf.get('success_rate', 0):.1%}")
        print(f"  Avg Latency: {perf.get('avg_latency_ms', 0):.0f}ms")
        
        print(f"\nTop Models by Performance:")
        for model, score in status['top_models'][:5]:
            print(f"  • {model}: {score:.3f}")
            
    elif args.test_select:
        model = proxy.select_model_for_prompt(args.test_select)
        print(f"Selected model: {model}")
        
    elif args.rotate:
        proxy.force_model_rotation()
        print("Model rotation complete")
        
    elif args.models:
        if DIVERSIFICATION_AVAILABLE:
            print("\nAvailable Free Models:")
            for model in sorted(MODEL_DATABASE.values(), key=lambda m: m.display_name):
                if model.is_free:
                    print(f"  • {model.display_name}")
                    print(f"    {model.model_id}")
                    print(f"    Context: {model.context_length:,} | Provider: {model.provider}")
                    print()
        else:
            print("Diversification engine not available")
            
    elif args.performance:
        stats = proxy.tracker.get_stats_summary()
        print("\nPerformance Summary:")
        print(json.dumps(stats, indent=2))
        
    elif args.discover:
        if proxy.enabled and proxy.engine:
            import asyncio
            result = asyncio.run(proxy.engine.discovery.discover_models(force=True))
            print(f"Discovery complete. Found {len(result)} new models")
        else:
            print("Diversification engine not enabled")


if __name__ == "__main__":
    main()