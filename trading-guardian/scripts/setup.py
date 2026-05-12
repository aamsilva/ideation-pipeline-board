#!/usr/bin/env python3
"""
Trading Guardian - Autonomous Setup Script
Initializes the system for fully autonomous operation
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_PATH = "/Volumes/disco1tb/projects/trading-guardian"
ENV_PATH = f"{PROJECT_PATH}/.env"
TEMPLATE_PATH = f"{PROJECT_PATH}/.env.template"

def run_command(cmd, check=True):
    """Run shell command"""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=PROJECT_PATH
    )
    if check and result.returncode != 0:
        print(f"⚠️  Command failed: {cmd}")
        print(f"   Error: {result.stderr}")
    return result

def setup_git():
    """Initialize git repo if needed"""
    if os.path.exists(f"{PROJECT_PATH}/.git"):
        print("✅ Git repo already initialized")
        return True
    
    print("📁 Initializing git repository...")
    run_command("git init")
    run_command("git add .")
    run_command('git commit -m "🚀 Initial commit: Trading Guardian - Autonomous Trading System"')
    print("✅ Git repo initialized")
    return True

def create_env_file():
    """Create .env from template if needed"""
    if os.path.exists(ENV_PATH):
        print("✅ .env file already exists")
        return True
    
    print("📝 Creating .env file from template...")
    if os.path.exists(TEMPLATE_PATH):
        with open(TEMPLATE_PATH, 'r') as f:
            content = f.read()
        
        with open(ENV_PATH, 'w') as f:
            f.write(content)
        
        print("✅ .env file created (EDIT WITH YOUR CREDENTIALS)")
        print("   ⚠️  Remember to fill in API keys!")
        return True
    else:
        print("❌ Template not found")
        return False

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    req_path = f"{PROJECT_PATH}/requirements.txt"
    if os.path.exists(req_path):
        run_command(f"pip3 install -r {req_path}")
        print("✅ Dependencies installed")
        return True
    else:
        print("⚠️  requirements.txt not found")
        return False

def run_tests():
    """Run test suite"""
    print("🧪 Running test suite...")
    result = run_command("python3 tests/test_guardian.py", check=False)
    if result.returncode == 0:
        print("✅ All tests passed")
        return True
    else:
        print("⚠️  Some tests failed (non-critical)")
        return False

def create_gitignore():
    """Create .gitignore"""
    gitignore_path = f"{PROJECT_PATH}/.gitignore"
    if os.path.exists(gitignore_path):
        print("✅ .gitignore already exists")
        return
    
    content = """# Environment
.env

# Python
__pycache__/
*.py[cod]
*.so
*.egg-info/
dist/
build/

# Logs
logs/*.log
*.log

# Data
data/*.jsonl
data/*.json
backups/

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
"""
    with open(gitignore_path, 'w') as f:
        f.write(content)
    print("✅ .gitignore created")

def main():
    print("🚀 Trading Guardian - Autonomous Setup")
    print("=" * 60)
    print(f"Project: {PROJECT_PATH}")
    print()
    
    steps = [
        ("Git Init", setup_git),
        ("Create .env", create_env_file),
        ("GitIgnore", create_gitignore),
        ("Dependencies", install_dependencies),
        ("Tests", run_tests),
    ]
    
    results = []
    for name, func in steps:
        print(f"\n▶️  {name}...")
        try:
            success = func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📊 SETUP SUMMARY")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ OK" if success else "⚠️  ISSUE"
        print(f"   {name}: {status}")
    
    print("\n🎉 Setup complete!")
    print("\nNext steps (autonomous operation):")
    print("   1. Edit .env with your Alpaca API credentials")
    print("   2. Run: python3 src/guardian_core.py")
    print("   3. Or schedule cron job for autonomous operation")
    
    return all(success for _, success in results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
