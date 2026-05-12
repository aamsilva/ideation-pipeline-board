#!/usr/bin/env python3
"""
Pre-Execution Validator (FP2 Fix)
Validates all trades before execution
"""

import logging
from typing import Tuple, List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class PreExecutionValidator:
    """Validates trades before execution"""
    
    def __init__(self, guardian):
        self.guardian = guardian
        self.validation_rules = [
            self._validate_credentials,
            self._validate_symbol,
            self._validate_quantity,
            self._validate_risk_limits,
            self._validate_market_hours,
        ]
    
    def validate_order(self, order) -> Tuple[bool, str]:
        """
        Run all validation rules
        Returns: (is_valid, error_message)
        """
        for rule in self.validation_rules:
            valid, msg = rule(order)
            if not valid:
                logger.warning(f"Validation failed: {msg}")
                return False, msg
        
        logger.info(f"✅ Order validated: {order.side} {order.quantity} {order.symbol}")
        return True, "OK"
    
    def _validate_credentials(self, order) -> Tuple[bool, str]:
        """Check if API credentials are configured"""
        if not self.guardian.credentials_ok:
            return False, "API credentials not configured"
        return True, "OK"
    
    def _validate_symbol(self, order) -> Tuple[bool, str]:
        """Validate symbol format"""
        if not order.symbol or len(order.symbol) < 1:
            return False, "Invalid symbol"
        
        # Basic check: uppercase letters only for stocks
        if not order.symbol.isalpha():
            return False, "Symbol must contain only letters"
        
        return True, "OK"
    
    def _validate_quantity(self, order) -> Tuple[bool, str]:
        """Validate order quantity"""
        if order.quantity <= 0:
            return False, "Quantity must be positive"
        
        if order.quantity > 10000:  # Sanity check
            return False, "Quantity exceeds maximum allowed (10000)"
        
        return True, "OK"
    
    def _validate_risk_limits(self, order) -> Tuple[bool, str]:
        """Check risk limits"""
        config = self.guardian.config.get("guardian", {})
        max_risk = config.get("max_risk_per_trade", 0.01)
        
        # Simulate position value check
        # In real implementation: fetch current price, calculate position value
        estimated_value = order.quantity * 100.0  # Simulated price
        
        # Check against account balance (simulated)
        account_balance = 100000.0  # Simulated
        risk_amount = estimated_value * max_risk
        
        if risk_amount > account_balance * max_risk:
            return False, f"Risk amount ${risk_amount:.2f} exceeds limit"
        
        return True, "OK"
    
    def _validate_market_hours(self, order) -> Tuple[bool, str]:
        """Check if market is open (optional validation)"""
        # This is a soft validation - warn but don't block
        now = datetime.now()
        
        # Simple check: weekends
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            logger.warning("Weekend - market closed (soft warning)")
        
        return True, "OK"
    
    def validate_system_state(self) -> Dict[str, bool]:
        """Validate overall system state"""
        checks = {
            "credentials": self.guardian.credentials_ok,
            "config_loaded": bool(self.guardian.config),
            "health_score_ok": self.guardian.metrics.health_score > 50,
            "api_errors_acceptable": (
                self.guardian.metrics.api_errors < 10
            ),
        }
        return checks
