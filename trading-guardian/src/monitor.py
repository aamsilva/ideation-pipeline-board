#!/usr/bin/env python3
"""
Health Monitor (FP4 Fix)
Continuous system health monitoring
"""

import os
import time
import sys
from typing import Dict
from datetime import datetime
from enum import Enum

import logging
logger = logging.getLogger(__name__)

# Import SystemStatus from guardian_core
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guardian_core import SystemStatus


class HealthMonitor:
    """
    Monitors system health and detects issues
    """
    
    def __init__(self, guardian):
        self.guardian = guardian
        self.checks = [
            self._check_credentials,
            self._check_config,
            self._check_api_health,
            self._check_disk_space,
            self._check_error_rate,
        ]
    
    def check_health(self) -> Dict:
        """
        Run all health checks
        Returns health report
        """
        results = {}
        score = 100.0
        
        for check in self.checks:
            check_name = check.__name__.replace("_check_", "")
            try:
                passed, msg, penalty = check()
                results[check_name] = {
                    "status": "OK" if passed else "FAIL",
                    "message": msg,
                    "penalty": penalty
                }
                if not passed:
                    score -= penalty
            except Exception as e:
                results[check_name] = {
                    "status": "ERROR",
                    "message": str(e),
                    "penalty": 20
                }
                score -= 20
        
        # Update guardian metrics
        self.guardian.metrics.health_score = max(score,0.0)
        
        # Determine overall status
        if score >= 80:
            self.guardian.metrics.status = SystemStatus.HEALTHY
        elif score >= 50:
            self.guardian.metrics.status = SystemStatus.DEGRADED
        else:
            self.guardian.metrics.status = SystemStatus.CRITICAL
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_score": self.guardian.metrics.health_score,
            "status": self.guardian.metrics.status.value,
            "checks": results,
            "metrics": {
                "total_trades": self.guardian.metrics.total_trades,
                "success_rate": self.guardian.metrics.success_rate(),
                "api_errors": self.guardian.metrics.api_errors,
                "uptime_seconds": time.time() - self.guardian.start_time
            }
        }
    
    def _check_credentials(self) -> tuple:
        """Check if credentials are configured"""
        if self.guardian.credentials_ok:
            return True, "Credentials configured", 0
        else:
            return False, "Credentials missing", 30
    
    def _check_config(self) -> tuple:
        """Check if config is valid"""
        if self.guardian.config:
            return True, "Config loaded", 0
        else:
            return False, "Config not loaded", 20
    
    def _check_api_health(self) -> tuple:
        """Check API connectivity (simulated)"""
        # In real implementation: ping Alpaca API
        if self.guardian.metrics.api_errors < 5:
            return True, "API healthy", 0
        else:
            return False, f"API errors: {self.guardian.metrics.api_errors}", 25
    
    def _check_disk_space(self) -> tuple:
        """Check available disk space"""
        stat = os.statvfs("/Volumes/disco1tb")
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        
        if free_gb > 10:
            return True, f"Disk space OK ({free_gb:.1f}GB free)", 0
        elif free_gb > 5:
            return True, f"Disk space low ({free_gb:.1f}GB free)", 10
        else:
            return False, f"Disk space critical ({free_gb:.1f}GB free)", 30
    
    def _check_error_rate(self) -> tuple:
        """Check system error rate"""
        total = self.guardian.metrics.total_trades
        errors = self.guardian.metrics.failed_trades
        
        if total == 0:
            return True, "No trades yet", 0
        
        error_rate = (errors / total) * 100
        
        if error_rate < 5:
            return True, f"Error rate OK ({error_rate:.1f}%)", 0
        elif error_rate < 15:
            return True, f"Error rate elevated ({error_rate:.1f}%)", 10
        else:
            return False, f"Error rate critical ({error_rate:.1f}%)", 25
