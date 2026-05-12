#!/usr/bin/env python3
import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class AlpacaExecutor:
    def __init__(self, use_live=False):
        self.use_live = use_live
        self.load_credentials()
        self.base_url = "https://api.alpaca.markets" if use_live else "https://paper-api.alpaca.markets"
        self.data_url = "https://data.alpaca.markets"
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret
        }
        self._price_cache = {}
        self._cache_ttl = 60

    def load_credentials(self):
        env_path = os.path.expanduser('~/.openclaw/secrets/alpaca_real.env' if self.use_live else '~/.openclaw/secrets/alpaca_paper.env')
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and '=' in line and not line.startswith('#'):
                        k, v = line.split('=', 1)
                        os.environ[k.strip()] = v.strip()
        self.api_key = os.environ.get('ALPACA_API_KEY')
        self.secret = os.environ.get('ALPACA_SECRET_KEY')

    def get_account(self) -> Optional[Dict]:
        try:
            resp = requests.get(f"{self.base_url}/v2/account", headers=self.headers, timeout=10)
            return resp.json() if resp.status_code == 200 else None
        except Exception: return None

    def get_positions(self) -> Dict:
        try:
            resp = requests.get(f"{self.base_url}/v2/positions", headers=self.headers, timeout=10)
            if resp.status_code == 200:
                return {p['symbol']: {'qty': float(p['qty']), 'current': float(p['current_price']), 'avg_entry': float(p['avg_entry_price']), 'pnl': float(p['unrealized_pl'])} for p in resp.json() if float(p['qty']) > 0}
        except Exception: pass
        return {}

    def get_orders(self, status: str = 'all', limit: int = 100) -> List[Dict]:
        try:
            resp = requests.get(f"{self.base_url}/v2/orders", params={'status': status, 'limit': limit}, headers=self.headers, timeout=10)
            return resp.json() if resp.status_code == 200 else []
        except Exception: return []

    def submit_order(self, symbol: str, qty: float, side: str, order_type: str = 'market') -> Optional[Dict]:
        try:
            data = {
                'symbol': symbol, 
                'qty': qty, 
                'side': side, 
                'type': order_type, 
                'time_in_force': 'day' if qty % 1 != 0 else 'gtc',
                'extended_hours': True # Support Pre/Post market
            }
            resp = requests.post(f"{self.base_url}/v2/orders", json=data, headers=self.headers, timeout=10)
            return resp.json() if resp.status_code == 200 else None
        except Exception: return None

def get_executor(use_live=False):
    return AlpacaExecutor(use_live=use_live)
