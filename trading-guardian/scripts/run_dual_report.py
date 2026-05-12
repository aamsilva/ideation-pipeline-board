#!/usr/bin/env python3
"""
Cron job wrapper: Generate and send Alpha Trade Dual Report
Reads from guardian_state.json (NO Alpaca API calls)
"""
import sys
import os
import json
from pathlib import Path

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# Import the report generator
try:
    from generate_dual_report import generate_report
    
    # Generate the report
    report = generate_report()
    
    # Output for cron job to capture and send
    print(report)
    
except Exception as e:
    error_msg = f"⚠️ Report generation failed: {e}"
    print(error_msg, file=sys.stderr)
    print(error_msg)  # Still output something for Discord
    sys.exit(1)
