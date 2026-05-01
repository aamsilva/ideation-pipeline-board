#!/usr/bin/env python3
"""
Provider Benchmark Script - Measures latency and throughput for LLM API providers.
Usage: 
    export TEST_KEY_DEEPINFRA="your_deepinfra_key"
    export TEST_KEY_OPENROUTER="your_openrouter_key"
    python3 benchmark_providers.py
"""

import os
import time
import json
import statistics
from datetime import datetime
from openai import OpenAI

# Configuration
TEST_PROVIDERS = {
    "deepinfra": {
        "base_url": "https://api.deepinfra.com/v1/openai",
        "key_env": "TEST_KEY_DEEPINFRA",
        "models": [
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "Qwen/Qwen3-235B-A22B-Instruct-2507",
            "deepseek-ai/DeepSeek-V3.2"
        ]
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "key_env": "TEST_KEY_OPENROUTER",
        "models": [
            "qwen/qwen-2.5-7b-instruct",
            "deepseek/deepseek-chat-v3.1",
            "meta-llama/llama-3.1-8b-instruct"
        ]
    }
}

# Test prompt - standardized for fair comparison
TEST_PROMPT = """You are a helpful assistant. Write a short Python function that calculates 
the factorial of a number using recursion. Include type hints and a docstring."""

def measure_latency(client, model, prompt, num_runs=5):
    """Measure TTFT (Time to First Token), total latency, and success rate."""
    results = {
        "ttft_samples": [],
        "total_latency_samples": [],
        "success_count": 0,
        "error_count": 0,
        "errors": []
    }
    
    for i in range(num_runs):
        try:
            start_time = time.time()
            
            # Use streaming to measure TTFT
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                max_tokens=200,
                temperature=0.7
            )
            
            first_token_time = None
            full_response = ""
            
            for chunk in stream:
                if first_token_time is None and chunk.choices[0].delta.content:
                    first_token_time = time.time() - start_time
                
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
            
            total_latency = time.time() - start_time
            
            if first_token_time is not None:
                results["ttft_samples"].append(first_token_time)
                results["total_latency_samples"].append(total_latency)
                results["success_count"] += 1
            else:
                results["error_count"] += 1
                
        except Exception as e:
            results["error_count"] += 1
            results["errors"].append(str(e))
        
        # Small delay between runs
        time.sleep(0.5)
    
    return results

def calculate_stats(samples):
    """Calculate mean, median, p95 statistics."""
    if not samples:
        return {"mean": 0, "median": 0, "p95": 0}
    
    sorted_samples = sorted(samples)
    p95_idx = int(len(sorted_samples) * 0.95)
    
    return {
        "mean": statistics.mean(samples),
        "median": statistics.median(samples),
        "p95": sorted_samples[p95_idx] if p95_idx < len(sorted_samples) else sorted_samples[-1],
        "min": min(samples),
        "max": max(samples)
    }

def run_benchmark():
    """Execute full benchmark across all configured providers."""
    print("=" * 70)
    print("LLM PROVIDER BENCHMARK")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Test runs per model: 5")
    print()
    
    all_results = {}
    
    for provider_name, provider_config in TEST_PROVIDERS.items():
        api_key = os.environ.get(provider_config["key_env"])
        
        if not api_key:
            print(f"[SKIP] {provider_name}: No API key found (set {provider_config['key_env']})")
            print()
            continue
        
        print(f"Testing: {provider_name.upper()}")
        print("-" * 50)
        
        client = OpenAI(
            base_url=provider_config["base_url"],
            api_key=api_key,
            timeout=60.0
        )
        
        provider_results = {}
        
        for model in provider_config["models"]:
            print(f"  Model: {model}")
            
            # Check if model exists/available
            try:
                results = measure_latency(client, model, TEST_PROMPT, num_runs=5)
            except Exception as e:
                print(f"    [ERROR] {e}")
                results = {"error": str(e)}
            
            if "ttft_samples" in results and results["ttft_samples"]:
                stats = {
                    "ttft": calculate_stats(results["ttft_samples"]),
                    "total_latency": calculate_stats(results["total_latency_samples"]),
                    "success_rate": results["success_count"] / (results["success_count"] + results["error_count"]) * 100,
                    "errors": results["errors"]
                }
                
                print(f"    TTFT: {stats['ttft']['mean']:.3f}s (median)")
                print(f"    Total Latency: {stats['total_latency']['mean']:.3f}s (median)")
                print(f"    Success Rate: {stats['success_rate']:.0f}%")
                
                provider_results[model] = stats
            else:
                print(f"    [FAILED] {results.get('error', 'Unknown error')}")
                provider_results[model] = {"error": results.get("error", "Unknown")}
            
            print()
        
        all_results[provider_name] = provider_results
    
    # Summary Table
    print("=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"{'Provider':<20} {'Model':<45} {'TTFT (s)':<12} {'Latency (s)':<12} {'Success %'}")
    print("-" * 100)
    
    for provider, models in all_results.items():
        for model, stats in models.items():
            if "error" not in stats:
                print(f"{provider:<20} {model:<45} {stats['ttft']['median']:<12.3f} {stats['total_latency']['median']:<12.3f} {stats['success_rate']:.0f}%")
    
    print()
    
    # Save results
    output_file = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"Results saved to: {output_file}")
    
    return all_results

if __name__ == "__main__":
    run_benchmark()