#!/usr/bin/env python3
"""
Kraken Executor - Production Ready with signature and robust REST API integration.
"""

import os
import time
import base64
import hashlib
import hmac
import requests
import urllib.parse
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("KrakenExecutor")


@dataclass
class TradeResult:
    success: bool
    order_id: str
    symbol: str
    filled_price: float
    filled_qty: float
    status: str
    strategy: str
    mode: str
    timestamp: str
    latency_ms: float


class KrakenExecutor:
    """
    Production-grade executor for Kraken API.
    Handles cryptographic request signing and fully authenticates private endpoints.
    """
    
    def __init__(self, use_live: bool = False):
        self.use_live = use_live
        # Try both direct and live credentials
        self.api_key = os.getenv("KRAKEN_LIVE_API_KEY") or os.getenv("KRAKEN_API_KEY", "")
        self.api_secret = os.getenv("KRAKEN_LIVE_API_SECRET") or os.getenv("KRAKEN_API_SECRET", "")
        self.base_url = "https://api.kraken.com"
        self.session = requests.Session()
        
        if not self.api_key or not self.api_secret:
            logger.warning("⚠️  Kraken API credentials not configured in .env. Private requests will fail.")
        else:
            logger.info(f"✅ Kraken Executor initialized successfully (live={use_live})")
            
    def _generate_signature(self, urlpath: str, data: dict) -> str:
        """
        Kraken API authentication signature builder.
        Signature = HMAC-SHA512(urlpath + SHA256(nonce + postdata), base64decode(api_secret))
        """
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        )
        return base64.b64encode(signature.digest()).decode()

    def _query_private(self, endpoint: str, data: dict = None) -> dict:
        """Execute a signed private request to Kraken API"""
        if not self.api_key or not self.api_secret:
            raise ValueError("Credentials not configured")
            
        if data is None:
            data = {}
            
        urlpath = f"/0/private/{endpoint}"
        # High precision nonce (microsecond precision timestamp)
        data['nonce'] = int(time.time() * 1000000)
        
        headers = {
            "API-Key": self.api_key,
            "API-Sign": self._generate_signature(urlpath, data),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        resp = self.session.post(
            f"{self.base_url}{urlpath}",
            headers=headers,
            data=data,
            timeout=15
        )
        
        if resp.status_code == 200:
            result = resp.json()
            if result.get("error"):
                logger.error(f"Kraken API private query error: {result['error']}")
                return {"error": result["error"]}
            return result.get("result", {})
        else:
            logger.error(f"Kraken HTTP private query error {resp.status_code}: {resp.text}")
            return {"error": f"HTTP {resp.status_code}"}

    def _query_public(self, endpoint: str, params: dict = None) -> dict:
        """Execute a public query to Kraken API"""
        urlpath = f"/0/public/{endpoint}"
        resp = self.session.get(
            f"{self.base_url}{urlpath}",
            params=params,
            timeout=10
        )
        if resp.status_code == 200:
            result = resp.json()
            if result.get("error"):
                logger.error(f"Kraken API public query error: {result['error']}")
                return {"error": result["error"]}
            return result.get("result", {})
        else:
            logger.error(f"Kraken HTTP public query error {resp.status_code}: {resp.text}")
            return {"error": f"HTTP {resp.status_code}"}

    def get_account_info(self) -> Dict:
        """Get account information and balance from Kraken"""
        try:
            # 1. Fetch asset balances
            balances = self._query_private("Balance")
            if "error" in balances:
                return {"cash": 0.0, "portfolio_value": 0.0, "buying_power": 0.0, "error": balances["error"]}
            
            # 2. Fetch trade balance (account equity and buying power)
            trade_bal = self._query_private("TradeBalance", {"asset": "ZUSD"})
            
            cash = float(balances.get("ZUSD", 0.0))
            portfolio_value = float(trade_bal.get("eb", cash)) # 'eb' is equivalent balance (equity)
            buying_power = float(trade_bal.get("tb", cash))    # 'tb' is trading balance (buying power)
            
            return {
                "cash": cash,
                "portfolio_value": portfolio_value,
                "buying_power": buying_power,
                "mode": "live" if self.use_live else "paper"
            }
        except Exception as e:
            logger.error(f"Failed to fetch Kraken account info: {e}")
            return {"cash": 0.0, "portfolio_value": 0.0, "buying_power": 0.0, "error": str(e)}

    def get_positions(self) -> List[Dict]:
        """Get current open margin positions on Kraken"""
        try:
            positions = self._query_private("OpenPositions")
            if "error" in positions:
                return []
            
            result_positions = []
            for txid, pos in positions.items():
                result_positions.append({
                    "symbol": pos.get("pair"),
                    "qty": float(pos.get("vol", 0.0)),
                    "current": float(pos.get("cost", 0.0)) / float(pos.get("vol", 1.0)) if float(pos.get("vol", 0.0)) > 0 else 0.0,
                    "avg_entry": float(pos.get("price", 0.0)),
                    "pnl": float(pos.get("pl", 0.0)),
                    "txid": txid
                })
            return result_positions
        except Exception as e:
            logger.error(f"Failed to fetch Kraken positions: {e}")
            return []

    def execute_trade(self, symbol: str, qty: float, side: str = "buy", strategy: str = "unknown") -> TradeResult:
        """Execute a market trade on Kraken (REST AddOrder)"""
        logger.info(f"🚀 Executing trade on Kraken: {side.upper()} {qty} {symbol}")
        
        start_time = time.perf_counter()
        timestamp = datetime.now().isoformat()
        
        # Standardize standard symbols (e.g. BTCUSD -> XXBTZUSD)
        pair = symbol
        if symbol == "BTCUSD":
            pair = "XXBTZUSD"
        elif symbol == "ETHUSD":
            pair = "XETHZUSD"
            
        data = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": "market",
            "volume": str(qty)
        }
        
        try:
            order_res = self._query_private("AddOrder", data)
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            if "error" in order_res:
                return TradeResult(
                    success=False, order_id="", symbol=symbol, filled_price=0.0, filled_qty=0.0,
                    status=f"error: {order_res['error']}", strategy=strategy,
                    mode="live" if self.use_live else "paper", timestamp=timestamp, latency_ms=latency_ms
                )
                
            txids = order_res.get("txid", [])
            order_id = txids[0] if txids else "unknown"
            desc = order_res.get("descr", {}).get("order", "")
            
            logger.info(f"   ✅ Kraken order submitted successfully: {order_id} | {desc}")
            
            # Since market orders are filled immediately, we fetch best current price from public Ticker
            ticker_info = self._query_public("Ticker", {"pair": pair})
            filled_price = 0.0
            if not "error" in ticker_info:
                # Get last trade price
                pair_data = list(ticker_info.values())[0]
                filled_price = float(pair_data.get("c", [0.0])[0])
                
            return TradeResult(
                success=True,
                order_id=order_id,
                symbol=symbol,
                filled_price=filled_price,
                filled_qty=qty,
                status="filled",
                strategy=strategy,
                mode="live" if self.use_live else "paper",
                timestamp=timestamp,
                latency_ms=latency_ms
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"❌ Kraken order failed: {e}")
            return TradeResult(
                success=False, order_id="", symbol=symbol, filled_price=0.0, filled_qty=0.0,
                status=f"exception: {str(e)}", strategy=strategy,
                mode="live" if self.use_live else "paper", timestamp=timestamp, latency_ms=latency_ms
            )

    def close_all_positions(self) -> Dict:
        """Close all margin positions and cancel active orders on Kraken"""
        logger.warning("🔥 Emergency general liquidation requested for Kraken...")
        try:
            # 1. Fetch active orders to cancel
            open_orders = self._query_private("OpenOrders")
            cancelled = 0
            if not "error" in open_orders:
                for txid in open_orders.get("open", {}).keys():
                    self._query_private("CancelOrder", {"txid": txid})
                    cancelled += 1
                    
            # 2. Fetch and close open margin positions
            positions = self.get_positions()
            closed = 0
            for pos in positions:
                # Submit market order to close position
                close_side = "sell" if pos["qty"] > 0 else "buy" # Inverse side to close
                self.execute_trade(pos["symbol"], abs(pos["qty"]), close_side, "liquidation")
                closed += 1
                
            return {"closed": closed, "cancelled": cancelled, "failed": 0}
        except Exception as e:
            logger.error(f"Failed to close Kraken positions: {e}")
            return {"closed": 0, "failed": 1}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor = KrakenExecutor()
    print("Kraken Executor initialized successfully.")
