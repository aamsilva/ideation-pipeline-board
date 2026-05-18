#!/usr/bin/env python3
import os
import json
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None

class AlpacaExecutor:
    def __init__(self, use_live=False):
        """Initialize executor with Alpaca credentials and cache.
        Args:
            use_live (bool): Whether to operate on the live Alpaca account.
        """
        self.use_live = use_live
        if use_live:
            self.api_key = os.getenv('ALPACA_LIVE_API_KEY') or os.getenv('ALPACA_API_KEY')
            self.secret_key = os.getenv('ALPACA_LIVE_SECRET_KEY') or os.getenv('ALPACA_SECRET_KEY')
        else:
            self.api_key = os.getenv('ALPACA_API_KEY')
            self.secret_key = os.getenv('ALPACA_SECRET_KEY')
        self.base_url = 'https://paper-api.alpaca.markets' if not use_live else 'https://api.alpaca.markets'
        self.data_url = 'https://data.alpaca.markets'
        self.headers = {
            'APCA-API-KEY-ID': self.api_key,
            'APCA-API-SECRET-KEY': self.secret_key,
        }
        # Simple in-memory price cache (price, timestamp)
        self._price_cache = {}
        self._cache_ttl = 60  # seconds
        # Simple request session for reuse
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # Logger
        self.logger = logging.getLogger(__name__)
        self.logger.info('AlpacaExecutor initialized (live=%s)', use_live)

    def get_account(self) -> Optional[Dict]:
        try:
            resp = self.session.get(f"{self.base_url}/v2/account", timeout=10)
            return resp.json() if resp.status_code == 200 else None
        except Exception as e:
            self.logger.error("get_account error: %s", e)
            return None

    def get_positions(self) -> Dict:
        try:
            resp = self.session.get(f"{self.base_url}/v2/positions", timeout=10)
            if resp.status_code == 200:
                return {p['symbol']: {'qty': float(p['qty']), 'current': float(p['current_price']), 'avg_entry': float(p['avg_entry_price']), 'pnl': float(p['unrealized_pl'])} for p in resp.json() if float(p['qty']) > 0}
        except Exception as e:
            self.logger.error("get_positions error: %s", e)
        return {}

    def get_orders(self, status: str = 'all', limit: int = 100) -> List[Dict]:
        try:
            resp = self.session.get(f"{self.base_url}/v2/orders", params={'status': status, 'limit': limit}, timeout=10)
            return resp.json() if resp.status_code == 200 else []
        except Exception as e:
            self.logger.error("get_orders error: %s", e)
            return []

    def submit_order(self, symbol: str, qty: float, side: str, order_type: str = 'market', time_in_force: str = None) -> Optional[Dict]:
        """Submit an order via Alpaca API.
        Args:
            symbol: Stock ticker
            qty: Quantity (can be fractional)
            side: 'buy' or 'sell'
            order_type: 'market', 'limit', 'stop', etc.
            time_in_force: 'day' or 'gtc'
        Returns:
            Order dict or None on failure
        """
        try:
            if time_in_force is None:
                time_in_force = 'day'  # Always use 'day' for fractional orders
            
            # For SELL orders: use exact qty (avoid notional floating point errors)
            # For BUY orders: use notional (fixed dollar amount)
            data = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'time_in_force': time_in_force,
                'extended_hours': False
            }
            
            if side.lower() == 'sell':
                # Use exact qty for sell orders, rounded down to 4 decimals to prevent exceeding available balance
                data['qty'] = int(qty * 10000) / 10000.0
            else:
                # Buy orders: use notional (fixed dollar amount)
                current_price = self.get_current_price(symbol)
                if current_price:
                    notional = round(qty * current_price, 2)
                    data['notional'] = notional
                else:
                    data['qty'] = round(qty, 4)
            
            resp = self.session.post(f"{self.base_url}/v2/orders", json=data, timeout=10)
            if resp.status_code == 200:
                self.logger.info("Order submitted: %s %s (qty: %s, notional: %s)", 
                              side, symbol, data.get('qty'), data.get('notional'))
                return resp.json()
            else:
                self.logger.warning("Order submit failed: %s - %s", resp.status_code, resp.text)
                return None
        except Exception as e:
            self.logger.error("submit_order error: %s", e)
            return None

    def buy(self, symbol: str, qty: float, order_type: str = 'market') -> Optional[Dict]:
        """Convenience method for buying."""
        return self.submit_order(symbol, qty, 'buy', order_type)

    def sell(self, symbol: str, qty: float, order_type: str = 'market') -> Optional[Dict]:
        """Convenience method for selling."""
        return self.submit_order(symbol, qty, 'sell', order_type)

    def cancel_all_orders(self):
        """Cancel all pending orders."""
        try:
            self.session.delete(f"{self.base_url}/v2/orders", timeout=10)
            self.logger.info("All orders cancelled")
        except Exception as e:
            self.logger.error("cancel_all_orders error: %s", e)

    def get_bars(self, symbol: str, period: int = 14, timeframe: str = '1Day') -> List[Dict]:
        """Get historical bars for a symbol. Tries Alpaca IEX feed first, then yfinance."""
        # Try Alpaca IEX feed first (free tier)
        try:
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=period * 2)
            params = {
                'start': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'end': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'timeframe': timeframe,
                'limit': period + 10,
                'adjustment': 'all',
                'feed': 'iex'  # Use IEX feed for free tier
            }
            resp = self.session.get(f"{self.data_url}/v2/stocks/{symbol}/bars", params=params, timeout=10)
            if resp.status_code == 200:
                bars = resp.json().get('bars', [])
                if bars:
                    self.logger.info(f"Got {len(bars)} bars from Alpaca IEX for {symbol}")
                    return bars
        except Exception as e:
            self.logger.error("get_bars Alpaca error: %s", e)
        
        # Fallback to yfinance if Alpaca failed
        if YFINANCE_AVAILABLE:
            try:
                self.logger.info(f"Falling back to yfinance for {symbol}")
                ticker = yf.Ticker(symbol)
                # Get period*2 days of data, interval 1d
                df = ticker.history(period=f"{period * 2}d", interval="1d")
                if df.empty:
                    return []
                # Convert to Alpaca bar format
                bars = []
                for idx, row in df.iterrows():
                    bar = {
                        't': int(idx.timestamp()),
                        'o': float(row['Open']),
                        'h': float(row['High']),
                        'l': float(row['Low']),
                        'c': float(row['Close']),
                        'v': int(row['Volume'])
                    }
                    bars.append(bar)
                self.logger.info(f"Got {len(bars)} bars from yfinance for {symbol}")
                return bars[-(period + 10):]  # Return last (period+10) bars
            except Exception as e:
                self.logger.error("get_bars yfinance error: %s", e)
        
        return []

    def calculate_bollinger_bands(self, symbol: str, period: int = 30, std_dev: float = 2.5) -> Optional[Dict]:
        """Calculate Bollinger Bands for a symbol."""
        try:
            bars = self.get_bars(symbol, period=period + 5)
            if not bars or len(bars) < period:
                return None
            closes = [float(b['c']) for b in bars[-period:]]
            if not closes:
                return None
            sma = sum(closes) / len(closes)
            variance = sum((x - sma) ** 2 for x in closes) / len(closes)
            std = variance ** 0.5
            return {
                'upper': sma + (std_dev * std),
                'middle': sma,
                'lower': sma - (std_dev * std),
                'current': closes[-1]
            }
        except Exception as e:
            self.logger.error("calculate_bollinger_bands error: %s", e)
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the latest price for a symbol using Alpaca Data API v2, with yfinance fallback."""
        # Check cache first
        if symbol in self._price_cache:
            price, timestamp = self._price_cache[symbol]
            if time.time() - timestamp < self._cache_ttl:
                return price
        
        # Try Alpaca Data API - Latest Trade
        try:
            resp = self.session.get(f"{self.data_url}/v2/stocks/{symbol}/trades/latest", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                price = float(data['trade']['p'])
                self._price_cache[symbol] = (price, time.time())
                return price
        except Exception as e:
            self.logger.error("get_current_price Alpaca error: %s", e)
        
        # Fallback to yfinance
        if YFINANCE_AVAILABLE:
            try:
                ticker = yf.Ticker(symbol)
                # Get last 1 day of data
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                    self._price_cache[symbol] = (price, time.time())
                    self.logger.info(f"Got current price for {symbol} from yfinance: ${price:.2f}")
                    return price
            except Exception as e:
                self.logger.error("get_current_price yfinance error: %s", e)
        
        self.logger.warning("Could not get current price for %s", symbol)
        return None


def get_executor(use_live=False):
    return AlpacaExecutor(use_live=use_live)