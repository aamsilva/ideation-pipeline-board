#!/usr/bin/env python3
import os
import json
import websocket
import threading
import time
import logging
from typing import Dict

logger = logging.getLogger("RealTimeData")
logging.basicConfig(level=logging.INFO)

class AlpacaWebsocketClient:
    """
    Client de WebSockets para dados em tempo real da Alpaca.
    Mantém uma cache em memória dos preços mais recentes para latência ultra-baixa.
    """
    def __init__(self):
        self.api_key = os.environ.get('ALPACA_API_KEY')
        self.secret = os.environ.get('ALPACA_SECRET_KEY')
        self.socket_url = "wss://stream.data.alpaca.markets/v2/iex" # IEX for free real-time data
        self.prices = {}
        self.ws = None
        self.thread = None

    def on_open(self, ws):
        logger.info("📡 WebSocket Connection Opened")
        # 1. Authenticate
        auth_data = {
            "action": "auth",
            "key": self.api_key,
            "secret": self.secret
        }
        ws.send(json.dumps(auth_data))
        
        # 2. Subscribe to trades/quotes for watchlist
        # We'll subscribe later via a helper method
        
    def on_message(self, ws, message):
        data = json.loads(message)
        for msg in data:
            T = msg.get('T')
            if T == 'success' and msg.get('msg') == 'authenticated':
                logger.info("✅ WebSocket Authenticated")
            elif T == 't': # Trade message
                symbol = msg.get('S')
                price = msg.get('p')
                self.prices[symbol] = {
                    "price": price,
                    "time": msg.get('t'),
                    "latency": time.time() - (msg.get('t') / 1e9) # Estimativa de latência
                }
                
    def subscribe(self, symbols: list):
        if not self.ws or not hasattr(self.ws, 'sock') or not self.ws.sock or not self.ws.sock.connected:
            logger.warning("⚠️ Cannot subscribe: WebSocket not connected yet. Will retry in next cycle.")
            return
        try:
            sub_data = {
                "action": "subscribe",
                "trades": symbols
            }
            self.ws.send(json.dumps(sub_data))
            logger.info(f"🏹 Subscribed to real-time trades for: {symbols}")
        except Exception as e:
            logger.warning(f"⚠️ Subscription failed: {e}")

    def run(self):
        self.ws = websocket.WebSocketApp(
            self.socket_url,
            on_open=self.on_open,
            on_message=self.on_message
        )
        self.ws.run_forever()

    def start_async(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()
        logger.info("🚀 Real-time data engine started in background")

    def get_price(self, symbol: str) -> float:
        return self.prices.get(symbol, {}).get("price")

if __name__ == "__main__":
    # Teste rápido de latência
    client = AlpacaWebsocketClient()
    client.start_async()
    time.sleep(5)
    client.subscribe(["AAPL", "NVDA", "MSFT"])
    while True:
        print(f"Current Prices: {client.prices}")
        time.sleep(1)
