#!/usr/bin/env python3
"""
Smart Provider API Proxy - Drop-in replacement for OpenAI API.

Listens on localhost and routes requests to OpenRouter or DeepInfra based on:
- Provider health (failure rate)
- Budget constraints
- Automatic failover and recovery

Usage:
    python3 provider_api_proxy.py [--port 8766]

Then configure Hermes to use:
    base_url: http://localhost:8766/v1
    api_key: any-dummy-key (not used)
"""

import os
import sys
import json
import logging
import time
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import urllib.request
import urllib.error

# Load .env from Hermes config if available
env_file = Path.home() / ".hermes" / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

SCRIPT_DIR = Path("/Volumes/disco1tb/projects/hermes-scripts")
sys.path.insert(0, str(SCRIPT_DIR))

from provider_health_monitor import ProviderHealthMonitor, PROVIDERS
from smart_provider_router import get_router

# Global health monitor instance
_health_monitor = None

def get_monitor():
    """Get or create the global health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = ProviderHealthMonitor()
    return _health_monitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8766"))
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

# Timeout for upstream API calls
REQUEST_TIMEOUT = 60


class ProxyHandler(BaseHTTPRequestHandler):
    """Handles OpenAI-compatible API requests with smart routing."""
    
    def log_message(self, format, *args):
        """Custom logging."""
        logger.info(f"{self.client_address[0]} - {format % args}")
    
    def _get_request_body(self) -> dict:
        """Read and parse JSON request body."""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode('utf-8'))
    
    def _send_json_response(self, status_code: int, data: dict):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _proxy_request(self, method: str, url: str, headers: dict, body: dict = None) -> tuple:
        """
        Proxy request to upstream provider.
        Returns: (status_code, response_body, response_headers)
        """
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode('utf-8') if body else None,
                headers=headers,
                method=method
            )
            
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                response_body = response.read().decode('utf-8')
                response_headers = dict(response.headers)
                return response.status, response_body, response_headers
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else "{}"
            return e.code, error_body, dict(e.headers) if e.headers else {}
        except urllib.error.URLError as e:
            return 500, json.dumps({"error": {"message": str(e.reason), "type": "connection_error"}}), {}
        except Exception as e:
            return 500, json.dumps({"error": {"message": str(e), "type": "internal_error"}}), {}
    
    def do_POST(self):
        """Handle POST requests to /v1/chat/completions and other endpoints."""
        print(f"[DEBUG] Received POST request: {self.path}", flush=True)
        
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            
            # Get router and health monitor
            router = get_router()
            health_monitor = get_monitor()
            
            # Get current provider config
            provider_config = router.current_config
            current_provider = provider_config["provider"]
            print(f"[DEBUG] Routing via: {current_provider}", flush=True)
            
            logger.info(f"Routing request via {current_provider}")
            
            # Get request body
            body = self._get_request_body()
            
            # Determine target URL and headers
            if current_provider == "deepinfra":
                base_url = "https://api.deepinfra.com/v1/openai"
                # DeepInfra uses model name directly (not with provider prefix)
                model = body.get("model", DEFAULT_MODEL).split("/")[-1]
            else:
                base_url = "https://openrouter.ai/api/v1"
                model = body.get("model", DEFAULT_MODEL)
            
            # Update body with correct model
            body["model"] = model
            
            # Build target URL
            if path == "/v1/chat/completions":
                target_url = f"{base_url}/chat/completions"
            elif path == "/v1/completions":
                target_url = f"{base_url}/completions"
            elif path == "/v1/embeddings":
                target_url = f"{base_url}/embeddings"
            else:
                # Pass through to default OpenRouter
                target_url = f"https://openrouter.ai/api/v1{path}"
            
            # Build headers (pass through most headers, but ensure Content-Type)
            # Get API key directly from environment
            api_key = os.environ.get("OPENROUTER_API_KEY", "")
            if current_provider == "deepinfra":
                api_key = os.environ.get("DEEPINFRA_API_KEY", api_key)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "http://localhost:8766",
                "X-Title": "Hermes Smart Proxy"
            }
            
            print(f"[DEBUG] Target URL: {target_url}", flush=True)
            
            # Forward request
            start_time = time.time()
            status, response_body, response_headers = self._proxy_request(
                "POST", target_url, headers, body
            )
            elapsed = time.time() - start_time
            
            # Track success/failure
            if status >= 200 and status < 300:
                logger.info(f"✓ {current_provider} success ({status}) in {elapsed:.2f}s")
                health_monitor.record_request(current_provider, model, True)
                
                # Add usage tracking if available
                try:
                    response_data = json.loads(response_body)
                    if "usage" in response_data:
                        logger.info(f"   Usage: {response_data['usage']}")
                except:
                    pass
            else:
                logger.warning(f"✗ {current_provider} failure ({status}) in {elapsed:.2f}s")
                health_monitor.record_request(current_provider, model, False)
            
            # Forward response
            self.send_response(status)
            for key, value in response_headers.items():
                if key.lower() not in ('transfer-encoding', 'connection'):
                    self.send_header(key, value)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(response_body.encode('utf-8'))
            
        except Exception as e:
            print(f"[ERROR] do_POST failed: {e}", flush=True)
            import traceback
            traceback.print_exc()
            self._send_json_response(500, {"error": {"message": str(e), "type": "internal_error"}})
    
    def do_GET(self):
        """Handle GET requests (health check, etc.)."""
        if self.path == "/health" or self.path == "/v1/models":
            # Return mock models list for compatibility
            router = get_router()
            provider = router.current_config["provider"]
            
            models = {
                "object": "list",
                "data": [
                    {"id": "google/gemma-3-27b-it:free", "object": "model", "created": 1700000000, "owned_by": "openrouter"},
                    {"id": "meta-llama/llama-3.1-8b-instruct:free", "object": "model", "created": 1700000000, "owned_by": "openrouter"},
                    {"id": "anthropic/claude-3-haiku:free", "object": "model", "created": 1700000000, "owned_by": "openrouter"},
                ]
            }
            
            self._send_json_response(200, models)
        else:
            self._send_json_response(404, {"error": "Not found"})


def run_server(port: int = PROXY_PORT):
    """Start the proxy server."""
    server = HTTPServer(('127.0.0.1', port), ProxyHandler)
    logger.info(f"🚀 Smart Provider Proxy running on http://127.0.0.1:{port}")
    logger.info(f"   Configure Hermes: base_url=http://127.0.0.1:{port}/v1")
    logger.info(f"   Health dashboard: http://localhost:8765/")
    logger.info("-" * 50)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Smart Provider API Proxy")
    parser.add_argument("--port", type=int, default=PROXY_PORT, help="Port to listen on")
    args = parser.parse_args()
    
    run_server(args.port)