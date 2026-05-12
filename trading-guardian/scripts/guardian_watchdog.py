#!/usr/bin/env python3
"""
Trading Guardian Watchdog - High Availability Monitor
Executa cada 5 minutos via cron para garantir que o daemon está sempre a correr
"""
import os
import sys
import time
import subprocess
import logging
from datetime import datetime

# Configurar logging
log_dir = "/Volumes/disco1tb/projects/trading-guardian/logs"
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)-15s | %(levelname)-7s | %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'watchdog.log')),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('GuardianWatchdog')

def is_daemon_running():
    """Check if guardian daemon is running"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "guardian_daemon.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        pids = result.stdout.strip().split('\n')
        pids = [p for p in pids if p and p.isdigit()]
        return len(pids) > 0
    except Exception as e:
        logger.error(f"Erro ao verificar daemon: {e}")
        return False

def is_launchd_loaded():
    """Check if launchd agent is loaded"""
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return "com.trading.guardian.daemon" in result.stdout
    except Exception as e:
        logger.error(f"Erro ao verificar launchd: {e}")
        return False

def reload_launchd():
    """Reload launchd agent"""
    try:
        plist_path = os.path.expanduser("~/Library/LaunchAgents/com.trading.guardian.daemon.plist")
        
        # Unload if loaded
        subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
        time.sleep(1)
        
        # Load again
        result = subprocess.run(
            ["launchctl", "load", plist_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("✅ Launchd agent reloaded successfully")
            return True
        else:
            logger.error(f"❌ Failed to reload launchd: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Exception reloading launchd: {e}")
        return False

def start_daemon_directly():
    """Start daemon directly if launchd fails"""
    try:
        daemon_path = "/Volumes/disco1tb/projects/trading-guardian/src/guardian_daemon.py"
        
        # Start in background
        subprocess.Popen(
            ["/usr/bin/python3", daemon_path],
            cwd="/Volumes/disco1tb/projects/trading-guardian",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        logger.info("✅ Daemon started directly (fallback method)")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to start daemon directly: {e}")
        return False

def main():
    """Main watchdog logic"""
    logger.info("=" * 60)
    logger.info("🛡️ Trading Guardian Watchdog STARTING")
    logger.info("=" * 60)
    
    # Check 1: Is daemon running?
    daemon_running = is_daemon_running()
    logger.info(f"📊 Daemon process: {'✅ RUNNING' if daemon_running else '❌ STOPPED'}")
    
    # Check 2: Is launchd loaded?
    launchd_ok = is_launchd_loaded()
    logger.info(f"📊 Launchd agent: {'✅ LOADED' if launchd_ok else '❌ NOT LOADED'}")
    
    # Action needed?
    if not daemon_running:
        logger.warning("⚠️ Daemon NOT running - attempting restart...")
        
        if not launchd_ok:
            logger.info("🔧 Reloading launchd agent...")
            reload_launchd()
            time.sleep(5)
        
        # Verify restart
        if is_daemon_running():
            logger.info("✅ Daemon successfully restarted via launchd")
        else:
            logger.warning("⚠️ Launchd restart failed - trying direct start...")
            start_daemon_directly()
            time.sleep(5)
            
            if is_daemon_running():
                logger.info("✅ Daemon started directly")
            else:
                logger.error("❌ CRITICAL: Failed to restart daemon!")
                sys.exit(1)
    else:
        logger.info("✅ Daemon is healthy and running")
    
    # Health check: Can we reach the daemon log?
    log_path = "/Volumes/disco1tb/projects/trading-guardian/logs/guardian_daemon.log"
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r') as f:
                f.seek(0, 2)  # Seek to end
                file_size = f.tell()
                logger.info(f"📊 Daemon log: {file_size} bytes")
        except:
            pass
    
    logger.info("✅ Watchdog check COMPLETED")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
