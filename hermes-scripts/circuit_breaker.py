#!/usr/bin/env python3
"""
Local Budget Circuit Breaker for LLM API Usage
================================================
Tracks token usage locally and blocks calls when approaching budget limit.

Usage:
    python3 circuit_breaker.py --check        # Check if can make API call
    python3 circuit_breaker.py --log <tokens> # Log token usage after API call
    python3 circuit_breaker.py --reset        # Reset monthly usage (run on 1st of month)
    python3 circuit_breaker.py --status       # Show current usage status
"""

import os
import json
import sys
import argparse
from datetime import datetime, date
from pathlib import Path

# Configuration
TRACKER_FILE = Path.home() / ".hermes" / "usage_tracker.json"
BUDGET_EUR = 40
USD_PER_EUR = 1.075  # Approximate exchange rate

# Cost per 1M tokens for various models (USD)
MODEL_COSTS = {
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo": 0.025,
    "Qwen/Qwen3-235B-A22B-Instruct-2507": 0.086,
    "deepseek-ai/DeepSeek-V3.2": 0.32,
    "qwen/qwen-2.5-7b-instruct": 0.07,
    "qwen/qwen3-8b": 0.225,
    "deepseek/deepseek-chat-v3.1": 0.45,
    "deepseek/deepseek-r1": 1.60,
}

# Alert thresholds (percentage of budget)
WARNING_THRESHOLD = 0.80  # 80%
CRITICAL_THRESHOLD = 0.95  # 95%

def load_tracker():
    """Load usage tracker from file."""
    if not TRACKER_FILE.exists():
        return {
            "month": date.today().month,
            "year": date.today().year,
            "total_tokens": 0,
            "total_cost_usd": 0,
            "api_calls": 0,
            "models_used": {}
        }
    
    try:
        with open(TRACKER_FILE, 'r') as f:
            data = json.load(f)
        
        # Check if new month - reset
        current_month = date.today().month
        current_year = date.today().year
        
        if data.get('month') != current_month or data.get('year') != current_year:
            # New month - archive old data and reset
            archive_file = TRACKER_FILE.parent / f"usage_tracker_{data.get('year')}_{data.get('month')}.json"
            with open(archive_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return {
                "month": current_month,
                "year": current_year,
                "total_tokens": 0,
                "total_cost_usd": 0,
                "api_calls": 0,
                "models_used": {}
            }
        
        return data
    except Exception as e:
        print(f"Error loading tracker: {e}")
        return {
            "month": date.today().month,
            "year": date.today().year,
            "total_tokens": 0,
            "total_cost_usd": 0,
            "api_calls": 0,
            "models_used": {}
        }

def save_tracker(data):
    """Save usage tracker to file."""
    TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def calculate_cost(tokens, model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"):
    """Calculate cost for tokens based on model."""
    cost_per_million = MODEL_COSTS.get(model, 0.10)  # Default to $0.10/M if unknown
    return (tokens / 1_000_000) * cost_per_million

def log_usage(input_tokens, output_tokens, model=None):
    """Log token usage after an API call."""
    data = load_tracker()
    
    total_tokens = input_tokens + output_tokens
    cost = calculate_cost(total_tokens, model)
    
    data["total_tokens"] += total_tokens
    data["total_cost_usd"] += cost
    data["api_calls"] += 1
    
    if model:
        if model not in data["models_used"]:
            data["models_used"][model] = {"tokens": 0, "cost": 0, "calls": 0}
        data["models_used"][model]["tokens"] += total_tokens
        data["models_used"][model]["cost"] += cost
        data["models_used"][model]["calls"] += 1
    
    save_tracker(data)
    
    return data

def check_budget(model=None):
    """Check if budget allows making an API call."""
    data = load_tracker()
    
    budget_usd = BUDGET_EUR * USD_PER_EUR
    spent = data["total_cost_usd"]
    remaining = budget_usd - spent
    percentage = (spent / budget_usd) * 100
    
    status = "OK"
    if percentage >= CRITICAL_THRESHOLD * 100:
        status = "BLOCKED"
    elif percentage >= WARNING_THRESHOLD * 100:
        status = "WARNING"
    
    return {
        "status": status,
        "budget_eur": BUDGET_EUR,
        "budget_usd": budget_usd,
        "spent_usd": spent,
        "remaining_usd": remaining,
        "percentage": percentage,
        "can_proceed": status != "BLOCKED",
        "is_warning": status == "WARNING"
    }

def show_status():
    """Display current usage status."""
    data = load_tracker()
    budget_info = check_budget()
    
    print("=" * 60)
    print("LLM USAGE TRACKER - STATUS")
    print("=" * 60)
    print(f"Period: {data['year']}-{data['month']:02d}")
    print(f"Budget: {budget_info['budget_eur']} EUR (~${budget_info['budget_usd']:.2f} USD)")
    print("-" * 60)
    print(f"Total Tokens:     {data['total_tokens']:,}")
    print(f"Total Cost:       ${data['total_cost_usd']:.2f}")
    print(f"API Calls:        {data['api_calls']}")
    print(f"Budget Used:      {budget_info['percentage']:.1f}%")
    print(f"Remaining:        ${budget_info['remaining_usd']:.2f}")
    print("-" * 60)
    
    if budget_info["status"] == "BLOCKED":
        print("⚠️  STATUS: BLOCKED - Budget limit exceeded!")
        print("    Stopping all LLM calls until reset.")
    elif budget_info["status"] == "WARNING":
        print("⚠️  STATUS: WARNING - Approaching budget limit!")
        print("    Consider switching to cheaper models.")
    else:
        print("✅ STATUS: OK - Budget within limits")
    
    if data["models_used"]:
        print("\nPer-Model Breakdown:")
        for model, stats in data["models_used"].items():
            print(f"  {model}")
            print(f"    Tokens: {stats['tokens']:,} | Cost: ${stats['cost']:.2f} | Calls: {stats['calls']}")
    
    print()
    return budget_info

def reset_usage():
    """Reset usage counters (manual reset)."""
    data = load_tracker()
    archive_file = TRACKER_FILE.parent / f"usage_tracker_{data.get('year')}_{data.get('month')}_manual_reset.json"
    with open(archive_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    new_data = {
        "month": date.today().month,
        "year": date.today().year,
        "total_tokens": 0,
        "total_cost_usd": 0,
        "api_calls": 0,
        "models_used": {}
    }
    save_tracker(new_data)
    print("Usage tracker reset. Previous data archived.")

def main():
    parser = argparse.ArgumentParser(description="LLM Budget Circuit Breaker")
    parser.add_argument("--check", action="store_true", help="Check if API call allowed")
    parser.add_argument("--log", type=int, nargs=2, metavar=("INPUT_TOKENS", "OUTPUT_TOKENS"),
                        help="Log token usage (input_tokens output_tokens)")
    parser.add_argument("--model", type=str, help="Model name for cost calculation")
    parser.add_argument("--reset", action="store_true", help="Reset usage counters")
    parser.add_argument("--status", action="store_true", help="Show usage status")
    
    args = parser.parse_args()
    
    if args.reset:
        reset_usage()
    elif args.status:
        show_status()
    elif args.check:
        result = check_budget(args.model) if args.model else check_budget()
        if not result["can_proceed"]:
            print(f"BUDGET BLOCKED: ${result['spent_usd']:.2f}/${result['budget_usd']:.2f} ({result['percentage']:.1f}%)")
            sys.exit(1)
        elif result["is_warning"]:
            print(f"BUDGET WARNING: {result['percentage']:.1f}% used - ${result['remaining_usd']:.2f} remaining")
        else:
            print(f"BUDGET OK: {result['percentage']:.1f}% used")
    elif args.log:
        input_tok, output_tok = args.log
        model = args.model or "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
        data = log_usage(input_tok, output_tok, model)
        print(f"Logged: {input_tok + output_tok} tokens, ${calculate_cost(input_tok + output_tok, model):.4f}")
        print(f"Total spent: ${data['total_cost_usd']:.2f}/{BUDGET_EUR * USD_PER_EUR:.2f} USD")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()