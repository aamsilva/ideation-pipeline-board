#!/usr/bin/env python3
"""
Aggressive Provider & Model Diversification Engine
===================================================

Advanced system for maximizing free tier usage with intelligent model selection.
- 20+ free models across 5+ providers
- AI-powered task classification and model selection
- Autonomous provider discovery and addition
- Zero disruption continuous execution

Author: Autonomous AI Infrastructure
Version: 3.0 - Aggressive Diversification
"""

import os
import json
import time
import logging
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import sqlite3
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("AggressiveDiversification")

SCRIPT_DIR = Path("/Volumes/disco1tb/projects/hermes-scripts")
DB_PATH = SCRIPT_DIR / "diversified_providers.db"


class ModelCapability(Enum):
    """Model capability tags"""
    REASONING = "reasoning"
    CODING = "coding"
    GENERAL = "general"
    FAST = "fast"
    LARGE_CONTEXT = "long_context"
    MULTIMODAL = "multimodal"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"


class TaskType(Enum):
    """Task type classification"""
    REASONING = "reasoning"
    CODING = "coding"
    WRITING = "writing"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    CREATIVE = "creative"
    GENERAL = "general"
    FAST_RESPONSE = "fast"
    LONG_CONTEXT = "long_context"


@dataclass
class ModelInfo:
    """Complete model information"""
    model_id: str
    provider: str
    display_name: str
    parameters: Optional[int]
    context_length: int
    capabilities: List[ModelCapability]
    input_cost: float  # per 1M tokens
    output_cost: float
    is_free: bool
    cache_discount: float = 0.0
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    total_requests: int = 0
    last_used: float = 0.0
    score: float = 1.0
    
    def to_dict(self) -> Dict:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "parameters": self.parameters,
            "context_length": self.context_length,
            "capabilities": [c.value for c in self.capabilities],
            "input_cost": self.input_cost,
            "output_cost": self.output_cost,
            "is_free": self.is_free,
            "cache_discount": self.cache_discount,
            "avg_latency_ms": self.avg_latency_ms,
            "success_rate": self.success_rate,
            "total_requests": self.total_requests,
            "score": self.score
        }


@dataclass
class ProviderInfo:
    """Provider information"""
    name: str
    base_url: str
    api_key_env: str
    models: List[str]
    priority: int
    is_free: bool
    rate_limit_rpm: int
    health_status: str = "unknown"
    last_check: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# AGGRESSIVE PROVIDER & MODEL CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

EXPANDED_PROVIDERS: Dict[str, ProviderInfo] = {
    # === TIER 1: OPENROUTER (Best free tier) ===
    "openrouter": ProviderInfo(
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        models=[
            # Top tier - 100B+ parameters
            "nvidia/nemotron-3-super-120b-a12b:free",      # 120B - BEST
            "nvidia/nemotron-3-nano-30b-a3b:free",         # 30B reasoning
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            
            # Google Gemma series
            "google/gemma-4-31b-it:free",                  # 31B - Excellent
            "google/gemma-3-27b-it:free",                  # 27B
            "google/gemma-3-12b-it:free",                  # 12B
            
            # Qwen series  
            "qwen/qwen3-next-80b-a3b-instruct:free",       # 80B - NEW
            "qwen/qwen3-coder:free",                       # Coding specialist
            "qwen/qwen-2.5-7b-instruct:free",              # 7B - Fast
            "qwen/qwen3-plus:free",                        # Plus tier
            
            # Meta Llama
            "meta-llama/llama-3.3-70b-instruct:free",      # 70B
            "meta-llama/llama-3.1-8b-instruct:free",       # 8B
            
            # Others
            "minimax/minimax-m2.5:free",                   # Multimodal
            "anthropic/claude-3-haiku:free",               # Claude Haiku
            "deepseek/deepseek-chat:free",                 # DeepSeek
            "mistralai/mistral-7b-instruct:free",          # Mistral
        ],
        priority=1,
        is_free=True,
        rate_limit_rpm=50
    ),
    
    # === TIER 2: DEEPINFRA (Good fallback) ===
    "deepinfra": ProviderInfo(
        name="DeepInfra",
        base_url="https://api.deepinfra.com/v1/openai",
        api_key_env="DEEPINFRA_API_KEY",
        models=[
            "deepinfra/meta-llama/Meta-Llama-3.1-405B-Instruct",
            "deepinfra/meta-llama/Meta-Llama-3.1-70B-Instruct",
            "deepinfra/meta-llama/Meta-Llama-3.1-8B-Instruct",
            "deepinfra/Qwen/Qwen2-72B-Instruct",
            "deepinfra/Qwen/Qwen2-7B-Instruct",
            "deepinfra/google/gemma-2-27b-it",
        ],
        priority=2,
        is_free=False,
        rate_limit_rpm=30
    ),
    
    # === TIER 3: TOGETHER AI ===
    "together": ProviderInfo(
        name="Together AI",
        base_url="https://api.together.xyz/v1",
        api_key_env="TOGETHER_API_KEY",
        models=[
            "together/mixtral-8x7b-instruct-v0.1",
            "together/llama-3-8b-chat",
            "together/qwen-2-7b-chat",
            "together/llama-3-70b-chat",
        ],
        priority=3,
        is_free=False,
        rate_limit_rpm=30
    ),
    
    # === TIER 4: FIREWORKS AI ===
    "fireworks": ProviderInfo(
        name="Fireworks AI",
        base_url="https://api.fireworks.ai/inference/v1",
        api_key_env="FIREWORKS_API_KEY",
        models=[
            "fireworks/llama-v3-70b-instruct",
            "fireworks/qwen2-72b-instruct",
            "fireworks/mixtral-8x22b-instruct",
        ],
        priority=4,
        is_free=False,
        rate_limit_rpm=30
    ),
    
    # === TIER 5: HF INFERENCE (Free but slow) ===
    "hf_inference": ProviderInfo(
        name="HuggingFace Inference",
        base_url="https://api-inference.huggingface.co",
        api_key_env="HF_TOKEN",
        models=[
            "meta-llama/Llama-3.1-8B-Instruct",
            "Qwen/Qwen2-7B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.2",
        ],
        priority=5,
        is_free=False,
        rate_limit_rpm=10
    ),
    
    # === TIER 6: COHERE (Free trials) ===
    "cohere": ProviderInfo(
        name="Cohere",
        base_url="https://api.cohere.ai/v1",
        api_key_env="COHERE_API_KEY",
        models=[
            "command-r-plus",
            "command-r",
        ],
        priority=6,
        is_free=False,
        rate_limit_rpm=20
    ),
}

# ═══════════════════════════════════════════════════════════════════════════════
# MODEL DATABASE WITH CAPABILITIES
# ═══════════════════════════════════════════════════════════════════════════════

MODEL_DATABASE: Dict[str, ModelInfo] = {}

def _init_model_database():
    """Initialize model database with all known free models"""
    global MODEL_DATABASE
    
    models = [
        # OpenRouter Free Models - Tier 1
        ModelInfo(
            model_id="nvidia/nemotron-3-super-120b-a12b:free",
            provider="openrouter",
            display_name="Nemotron Super 120B",
            parameters=120_000_000_000,
            context_length=262144,
            capabilities=[ModelCapability.REASONING, ModelCapability.GENERAL],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="nvidia/nemotron-3-nano-30b-a3b:free",
            provider="openrouter", 
            display_name="Nemotron Nano 30B",
            parameters=30_000_000_000,
            context_length=262144,
            capabilities=[ModelCapability.REASONING, ModelCapability.FAST],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="google/gemma-4-31b-it:free",
            provider="openrouter",
            display_name="Gemma 4 31B",
            parameters=31_000_000_000,
            context_length=262144,
            capabilities=[ModelCapability.GENERAL, ModelCapability.CODING],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="google/gemma-3-27b-it:free",
            provider="openrouter",
            display_name="Gemma 3 27B",
            parameters=27_000_000_000,
            context_length=131072,
            capabilities=[ModelCapability.GENERAL],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="qwen/qwen3-next-80b-a3b-instruct:free",
            provider="openrouter",
            display_name="Qwen3 Next 80B",
            parameters=80_000_000_000,
            context_length=262144,
            capabilities=[ModelCapability.REASONING, ModelCapability.CODING, ModelCapability.GENERAL],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="qwen/qwen3-coder:free",
            provider="openrouter",
            display_name="Qwen3 Coder",
            parameters=None,
            context_length=262144,
            capabilities=[ModelCapability.CODING],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="meta-llama/llama-3.3-70b-instruct:free",
            provider="openrouter",
            display_name="Llama 3.3 70B",
            parameters=70_000_000_000,
            context_length=131072,
            capabilities=[ModelCapability.GENERAL, ModelCapability.REASONING],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="minimax/minimax-m2.5:free",
            provider="openrouter",
            display_name="MiniMax M2.5",
            parameters=None,
            context_length=196608,
            capabilities=[ModelCapability.MULTIMODAL, ModelCapability.GENERAL],
            input_cost=0, output_cost=0, is_free=True,
            cache_discount=0.45
        ),
        ModelInfo(
            model_id="meta-llama/llama-3.1-8b-instruct:free",
            provider="openrouter",
            display_name="Llama 3.1 8B",
            parameters=8_000_000_000,
            context_length=131072,
            capabilities=[ModelCapability.FAST, ModelCapability.GENERAL],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="qwen/qwen-2.5-7b-instruct:free",
            provider="openrouter",
            display_name="Qwen 2.5 7B [DEPRECATED - 404]",
            parameters=7_000_000_000,
            context_length=131072,
            capabilities=[ModelCapability.FAST, ModelCapability.CODING],
            input_cost=0, output_cost=0, is_free=True,
            success_rate=0.0  # Mark as permanently failed
        ),
        ModelInfo(
            model_id="anthropic/claude-3-haiku:free",
            provider="openrouter",
            display_name="Claude 3 Haiku",
            parameters=None,
            context_length=200000,
            capabilities=[ModelCapability.FAST, ModelCapability.GENERAL],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="deepseek/deepseek-chat:free",
            provider="openrouter",
            display_name="DeepSeek Chat",
            parameters=None,
            context_length=64000,
            capabilities=[ModelCapability.REASONING, ModelCapability.CODING],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="mistralai/mistral-7b-instruct:free",
            provider="openrouter",
            display_name="Mistral 7B",
            parameters=7_000_000_000,
            context_length=131072,
            capabilities=[ModelCapability.GENERAL, ModelCapability.FAST],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="google/gemma-3-12b-it:free",
            provider="openrouter",
            display_name="Gemma 3 12B",
            parameters=12_000_000_000,
            context_length=131072,
            capabilities=[ModelCapability.GENERAL],
            input_cost=0, output_cost=0, is_free=True
        ),
        
        # Additional free models
        ModelInfo(
            model_id="z-ai/glm-4.5-air:free",
            provider="openrouter",
            display_name="GLM-4.5 Air",
            parameters=None,
            context_length=131072,
            capabilities=[ModelCapability.GENERAL],
            input_cost=0, output_cost=0, is_free=True
        ),
        ModelInfo(
            model_id="qwen/qwen3-plus:free",
            provider="openrouter",
            display_name="Qwen3 Plus",
            parameters=None,
            context_length=131072,
            capabilities=[ModelCapability.GENERAL],
            input_cost=0, output_cost=0, is_free=True
        ),
    ]
    
    for model in models:
        MODEL_DATABASE[model.model_id] = model
    
    logger.info(f"Initialized model database with {len(MODEL_DATABASE)} models")


# ═══════════════════════════════════════════════════════════════════════════════
# AI-POWERED MODEL SELECTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class IntelligentModelSelector:
    """
    AI-powered model selection based on:
    - Task type classification
    - Context length requirements
    - Historical performance
    - Cost optimization
    - Load balancing
    """
    
    def __init__(self):
        _init_model_database()
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.task_weights = {
            TaskType.REASONING: {"reasoning": 0.4, "general": 0.3, "context": 0.2, "latency": 0.1},
            TaskType.CODING: {"coding": 0.5, "context": 0.2, "latency": 0.15, "general": 0.15},
            TaskType.WRITING: {"general": 0.4, "creativity": 0.3, "latency": 0.15, "context": 0.15},
            TaskType.ANALYSIS: {"reasoning": 0.4, "general": 0.3, "context": 0.2, "latency": 0.1},
            TaskType.SUMMARIZATION: {"fast": 0.4, "context": 0.3, "general": 0.2, "latency": 0.1},
            TaskType.CREATIVE: {"creativity": 0.4, "general": 0.3, "context": 0.2, "latency": 0.1},
            TaskType.GENERAL: {"general": 0.4, "latency": 0.3, "context": 0.15, "cost": 0.15},
            TaskType.FAST_RESPONSE: {"fast": 0.5, "latency": 0.4, "cost": 0.1},
            TaskType.LONG_CONTEXT: {"context": 0.5, "reasoning": 0.25, "cost": 0.25},
        }
        
    def classify_task(self, prompt: str, history: List[Dict] = None) -> TaskType:
        """
        Classify task type from prompt using keyword analysis + history.
        In production, this could use a small classifier model.
        """
        prompt_lower = prompt.lower()
        
        # Check for reasoning tasks
        reasoning_keywords = ["analyze", "reason", "explain why", "logic", "solve", "think step", 
                            "proof", "derive", "compare", "evaluate", "assess", "critique"]
        if any(kw in prompt_lower for kw in reasoning_keywords):
            return TaskType.REASONING
            
        # Check for coding tasks
        coding_keywords = ["code", "program", "function", "class", "implement", "debug", 
                         "refactor", "algorithm", "sql", "python", "javascript", "api"]
        if any(kw in prompt_lower for kw in coding_keywords):
            return TaskType.CODING
            
        # Check for writing tasks
        writing_keywords = ["write", "create", "draft", "compose", "generate text", "story", "essay"]
        if any(kw in prompt_lower for kw in writing_keywords):
            return TaskType.WRITING
            
        # Check for creative tasks
        creative_keywords = ["creative", "imagine", "story", "poem", "artistic", "fiction", "narrative"]
        if any(kw in prompt_lower for kw in creative_keywords):
            return TaskType.CREATIVE
            
        # Check for summarization
        if "summarize" in prompt_lower or "summary" in prompt_lower or "tl;dr" in prompt_lower:
            return TaskType.SUMMARIZATION
            
        # Check for analysis
        if "analyze" in prompt_lower or "analysis" in prompt_lower:
            return TaskType.ANALYSIS
            
        # Check for long context requirement
        long_context_keywords = ["document", "book", "article", "transcript", "full text", "entire"]
        if any(kw in prompt_lower for kw in long_context_keywords):
            return TaskType.LONG_CONTEXT
            
        return TaskType.GENERAL
    
    def select_model(self, prompt: str, context_length: int = 4000, 
                    history: List[Dict] = None, require_vision: bool = False) -> Tuple[ModelInfo, float]:
        """
        Select optimal model using multi-factor scoring.
        Returns: (ModelInfo, selection_confidence)
        """
        task_type = self.classify_task(prompt, history)
        logger.info(f"Task classified as: {task_type.value}")
        
        # Get available free models
        candidates = [m for m in MODEL_DATABASE.values() if m.is_free]
        
        # Filter by capability requirements
        if require_vision:
            candidates = [m for m in candidates if ModelCapability.VISION in m.capabilities or 
                         ModelCapability.MULTIMODAL in m.capabilities]
        
        # Filter by context length
        candidates = [m for m in candidates if m.context_length >= context_length]
        
        if not candidates:
            # Fallback to any free model
            candidates = [m for m in MODEL_DATABASE.values() if m.is_free]
        
        # Score each candidate
        scored_models = []
        for model in candidates:
            score = self._calculate_model_score(model, task_type, context_length)
            scored_models.append((model, score))
        
        # Sort by score
        scored_models.sort(key=lambda x: x[1], reverse=True)
        
        # Log top 5 for debugging
        logger.info("Top 5 model candidates:")
        for i, (model, score) in enumerate(scored_models[:5]):
            logger.info(f"  {i+1}. {model.display_name}: {score:.3f}")
        
        best_model, best_score = scored_models[0]
        confidence = min(1.0, best_score / 2.0)  # Normalize to 0-1
        
        logger.info(f"Selected: {best_model.display_name} (confidence: {confidence:.2f})")
        return best_model, confidence
    
    def _calculate_model_score(self, model: ModelInfo, task_type: TaskType, 
                                context_length: int) -> float:
        """Calculate composite score for model selection"""
        weights = self.task_weights.get(task_type, self.task_weights[TaskType.GENERAL])
        
        # Base score
        score = 1.0
        
        # Capability match score (0-1)
        capability_score = self._get_capability_match(model, task_type)
        score *= (1 + capability_score * weights.get("general", 0.3))
        
        # Context match (0-1)
        context_ratio = min(1.0, model.context_length / max(context_length, 4000))
        score *= (1 + context_ratio * weights.get("context", 0.2))
        
        # Performance score based on history (0-1)
        perf_score = model.success_rate * (1.0 - model.avg_latency_ms/10000)
        score *= (1 + perf_score * weights.get("latency", 0.2))
        
        # Load balancing - prefer less used models
        usage_penalty = min(0.3, model.total_requests / 10000)
        score *= (1 - usage_penalty)
        
        # Provider diversity bonus - prefer different providers
        # (simplified - in production would track recent selections)
        
        # Apply model-specific boosts
        if task_type == TaskType.CODING and ModelCapability.CODING in model.capabilities:
            score *= 1.5
        if task_type == TaskType.REASONING and ModelCapability.REASONING in model.capabilities:
            score *= 1.5
        if task_type == TaskType.FAST_RESPONSE and ModelCapability.FAST in model.capabilities:
            score *= 1.8
            
        return score
    
    def _get_capability_match(self, model: ModelInfo, task_type: TaskType) -> float:
        """Calculate how well model capabilities match task requirements"""
        capability_map = {
            TaskType.REASONING: [ModelCapability.REASONING],
            TaskType.CODING: [ModelCapability.CODING],
            TaskType.WRITING: [ModelCapability.GENERAL],
            TaskType.ANALYSIS: [ModelCapability.REASONING, ModelCapability.GENERAL],
            TaskType.SUMMARIZATION: [ModelCapability.FAST, ModelCapability.GENERAL],
            TaskType.CREATIVE: [ModelCapability.GENERAL],
            TaskType.GENERAL: [ModelCapability.GENERAL],
            TaskType.FAST_RESPONSE: [ModelCapability.FAST],
            TaskType.LONG_CONTEXT: [ModelCapability.LARGE_CONTEXT],
        }
        
        required = capability_map.get(task_type, [ModelCapability.GENERAL])
        matches = sum(1 for cap in required if cap in model.capabilities)
        return matches / len(required) if required else 0
    
    def record_performance(self, model_id: str, latency_ms: float, success: bool, 
                          tokens_used: int = 0):
        """Record model performance for continuous learning"""
        if model_id in MODEL_DATABASE:
            model = MODEL_DATABASE[model_id]
            model.total_requests += 1
            
            # Update rolling average latency
            if model.avg_latency_ms == 0:
                model.avg_latency_ms = latency_ms
            else:
                model.avg_latency_ms = (model.avg_latency_ms * 0.9 + latency_ms * 0.1)
            
            # Update success rate
            if success:
                model.success_rate = model.success_rate * 0.95 + 0.05
            else:
                model.success_rate = model.success_rate * 0.95
                
            model.last_used = time.time()
            
            # Update score
            model.score = model.success_rate * (1.0 - model.avg_latency_ms/10000) * model.total_requests/100


# ═══════════════════════════════════════════════════════════════════════════════
# AUTONOMOUS PROVIDER DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════════

class AutonomousProviderDiscovery:
    """
    Autonomously discovers and integrates new providers/models.
    Operates without disrupting current execution.
    """
    
    KNOWN_FREE_MODEL_ENDPOINTS = [
        # These endpoints can be queried to discover available models
        ("https://openrouter.ai/api/v1/models", "openrouter"),
        ("https://api.deepinfra.com/v1/models", "deepinfra"),
        ("https://api.together.ai/v1/models", "together"),
    ]
    
    def __init__(self, selector: IntelligentModelSelector):
        self.selector = selector
        self.discovered_models: Dict[str, ModelInfo] = {}
        self.discovery_log: List[Dict] = []
        self.last_discovery = 0
        self.discovery_interval = 3600  # 1 hour
        
    async def discover_models(self, force: bool = False) -> List[ModelInfo]:
        """Discover new models from provider endpoints"""
        current_time = time.time()
        
        if not force and (current_time - self.last_discovery) < self.discovery_interval:
            logger.info("Skipping discovery - too soon since last run")
            return []
            
        logger.info("Starting autonomous provider discovery...")
        new_models = []
        
        for endpoint, provider in self.KNOWN_FREE_MODEL_ENDPOINTS:
            try:
                models = await self._fetch_provider_models(endpoint, provider)
                new_models.extend(models)
            except Exception as e:
                logger.warning(f"Discovery failed for {provider}: {e}")
        
        self.last_discovery = current_time
        self.discovery_log.append({
            "timestamp": current_time,
            "models_found": len(new_models),
            "providers_checked": len(self.KNOWN_FREE_MODEL_ENDPOINTS)
        })
        
        # Filter and add new free models
        for model in new_models:
            if model.is_free and model.model_id not in MODEL_DATABASE:
                MODEL_DATABASE[model.model_id] = model
                self.discovered_models[model.model_id] = model
                logger.info(f"Added new model: {model.model_id} from {model.provider}")
        
        logger.info(f"Discovery complete. Found {len(new_models)} new models")
        return new_models
    
    async def _fetch_provider_models(self, endpoint: str, provider: str) -> List[ModelInfo]:
        """Fetch available models from a provider endpoint"""
        models = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        for item in data.get("data", []):
                            # Check if model is free
                            is_free = self._is_model_free(item)
                            
                            model = ModelInfo(
                                model_id=item.get("id", ""),
                                provider=provider,
                                display_name=item.get("id", "").split("/")[-1] if "/" in item.get("id", "") else item.get("id", ""),
                                parameters=None,
                                context_length=item.get("context_length", 8192) or 8192,
                                capabilities=[ModelCapability.GENERAL],
                                input_cost=0 if is_free else item.get("pricing", {}).get("prompt", 0) or 0,
                                output_cost=0 if is_free else item.get("pricing", {}).get("completion", 0) or 0,
                                is_free=is_free
                            )
                            models.append(model)
                            
        except Exception as e:
            logger.warning(f"Failed to fetch models from {endpoint}: {e}")
            
        return models
    
    def _is_model_free(self, model_data: dict) -> bool:
        """Determine if model is free tier"""
        # Check various indicators of free tier
        model_id = model_data.get("id", "").lower()
        
        # Known free model patterns
        free_patterns = [":free", "free", "gpt-4o-mini", "gpt-4o-free"]
        
        # Check context length - often larger for free models
        context = model_data.get("context_length", 0) or 0
        
        return any(p in model_id for p in free_patterns) or context > 100000


# ═══════════════════════════════════════════════════════════════════════════════
# HOT-RELOAD CONFIGURATION MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class HotReloadConfigManager:
    """
    Manages configuration with hot-reload capability.
    Changes are applied without disrupting execution.
    """
    
    def __init__(self):
        self.config_path = SCRIPT_DIR / "diversified_config.json"
        self.config = self._load_config()
        self._watchdog_running = False
        
    def _load_config(self) -> Dict:
        """Load configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")
                
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            "version": "3.0",
            "budget_eur": 40.0,
            "max_free_models": 20,
            "discovery_interval_seconds": 3600,
            "model_rotation_enabled": True,
            "load_balancing_enabled": True,
            "fallback_chain": ["openrouter", "deepinfra", "together", "fireworks"],
            "provider_health_check_interval": 30,
        }
    
    def save_config(self):
        """Save current configuration"""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def reload_config(self) -> Dict:
        """Reload configuration without restarting"""
        old_config = self.config
        self.config = self._load_config()
        
        # Log changes
        changes = []
        for key in set(list(old_config.keys()) + list(self.config.keys())):
            if old_config.get(key) != self.config.get(key):
                changes.append(f"{key}: {old_config.get(key)} -> {self.config.get(key)}")
        
        if changes:
            logger.info(f"Config reloaded. Changes: {changes}")
        
        return self.config
    
    def update_model_list(self, models: List[str]):
        """Update active model list"""
        self.config["active_models"] = models
        self.save_config()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class AggressiveDiversificationEngine:
    """
    Main orchestrator for aggressive provider diversification.
    Runs continuously, optimizing model selection in real-time.
    """
    
    def __init__(self, budget_eur: float = 40.0):
        self.budget_eur = budget_eur
        self.selector = IntelligentModelSelector()
        self.discovery = AutonomousProviderDiscovery(self.selector)
        self.config = HotReloadConfigManager()
        
        # Performance tracking
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.active_models: List[str] = []
        
        # Initialize active models
        self._init_active_models()
        
        logger.info("="*60)
        logger.info("AGGRESSIVE DIVERSIFICATION ENGINE INITIALIZED")
        logger.info(f"Budget: €{budget_eur}/month")
        logger.info(f"Free models available: {len([m for m in MODEL_DATABASE.values() if m.is_free])}")
        logger.info("="*60)
    
    def _init_active_models(self):
        """Initialize list of active models sorted by priority"""
        free_models = [m for m in MODEL_DATABASE.values() if m.is_free]
        
        # Sort by score (success rate + performance)
        free_models.sort(key=lambda m: m.score, reverse=True)
        
        self.active_models = [m.model_id for m in free_models[:self.config.config.get("max_free_models", 20)]]
        logger.info(f"Active models: {self.active_models}")
    
    def get_model_for_task(self, prompt: str, context_length: int = 4000) -> str:
        """Get optimal model ID for the given task"""
        model, confidence = self.selector.select_model(prompt, context_length)
        
        # Record request
        self.total_requests += 1
        
        # Update active model rotation
        if model.model_id in self.active_models:
            # Move to front (most recently used)
            self.active_models.remove(model.model_id)
            self.active_models.insert(0, model.model_id)
        
        return model.model_id
    
    async def continuous_optimization(self):
        """Run continuous optimization loop"""
        logger.info("Starting continuous optimization...")
        
        while True:
            try:
                # Reload config (hot-reload)
                self.config.reload_config()
                
                # Discover new models
                await self.discovery.discover_models()
                
                # Rotate models if enabled
                if self.config.config.get("model_rotation_enabled"):
                    self._rotate_models()
                
                # Log stats
                logger.info(f"Stats: {self.total_requests} requests, "
                           f"{len(self.active_models)} active models")
                
                # Wait before next cycle
                await asyncio.sleep(300)  # 5 minutes
                
            except KeyboardInterrupt:
                logger.info("Optimization stopped")
                break
            except Exception as e:
                logger.error(f"Optimization error: {e}")
                await asyncio.sleep(60)
    
    def _rotate_models(self):
        """Rotate models based on performance"""
        # Get current scores
        current_models = [MODEL_DATABASE.get(mid) for mid in self.active_models if mid in MODEL_DATABASE]
        current_models = [m for m in current_models if m]
        
        # Sort by score
        current_models.sort(key=lambda m: m.score, reverse=True)
        
        # Update active list
        self.active_models = [m.model_id for m in current_models[:self.config.config.get("max_free_models", 20)]]
    
    def get_status(self) -> Dict:
        """Get current engine status"""
        return {
            "total_requests": self.total_requests,
            "budget_remaining": self.budget_eur - self.total_cost,
            "active_models": self.active_models[:5],
            "free_models_count": len([m for m in MODEL_DATABASE.values() if m.is_free]),
            "discovered_models": len(self.discovery.discovered_models),
            "config": self.config.config
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Aggressive Provider Diversification Engine")
    parser.add_argument("--status", action="store_true", help="Show engine status")
    parser.add_argument("--models", action="store_true", help="List available models")
    parser.add_argument("--select", type=str, help="Select model for task")
    parser.add_argument("--discover", action="store_true", help="Force model discovery")
    parser.add_argument("--run", action="store_true", help="Run continuous optimization")
    
    args = parser.parse_args()
    
    # Initialize engine
    engine = AggressiveDiversificationEngine()
    
    if args.status:
        status = engine.get_status()
        print("\n" + "="*60)
        print("AGGRESSIVE DIVERSIFICATION ENGINE STATUS")
        print("="*60)
        print(f"Total Requests: {status['total_requests']}")
        print(f"Budget Remaining: €{status['budget_remaining']:.2f}")
        print(f"Free Models: {status['free_models_count']}")
        print(f"Discovered Models: {status['discovered_models']}")
        print(f"Active Models: {status['active_models']}")
        
    elif args.models:
        print("\nAvailable Free Models:")
        for model in sorted(MODEL_DATABASE.values(), key=lambda m: m.display_name):
            if model.is_free:
                caps = ", ".join([c.value for c in model.capabilities])
                print(f"  • {model.display_name} ({model.provider})")
                print(f"    ID: {model.model_id}")
                print(f"    Context: {model.context_length:,} | Capabilities: {caps}")
                print(f"    Score: {model.score:.3f} | Success: {model.success_rate:.2%}")
                print()
                
    elif args.select:
        import asyncio
        model_id = engine.get_model_for_task(args.select)
        print(f"Selected model: {model_id}")
        
    elif args.discover:
        import asyncio
        asyncio.run(engine.discovery.discover_models(force=True))
        
    elif args.run:
        import asyncio
        asyncio.run(engine.continuous_optimization())


if __name__ == "__main__":
    main()