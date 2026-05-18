#!/usr/bin/env python3
"""Test sell order manually to debug 401 error"""
import os
import sys
import requests

# Set live credentials
os.environ['ALPACA_API_KEY'] = 'AKAHSR7C6XH7OAR7L6EJYVCRRK'
os.environ['ALPACA_SECRET_KEY'] = 'DjM8rMUbwHnGbkUJJoTt5BpAiujuQ39vzpxFosm2YEac'
os.environ['ALPACA_BASE_URL'] = 'https://api.alpaca.markets'

api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
base_url = os.getenv('ALPACA_BASE_URL')

headers = {
    'APCA-API-KEY-ID': api_key,
    'APCA-API-SECRET-KEY': secret_key,
}

print("🧪 TESTE MANUAL DE ORDEM DE VENDA (LIVE)")
print("=" * 50)

# 1. Check account (GET request - should work)
print("\n1. Testing GET /v2/account...")
resp = requests.get(f"{base_url}/v2/account", headers=headers, timeout=10)
print(f"   Status: {resp.status_code}")
if resp.status_code == 200:
    print(f"   Account Status: {resp.json().get('status')}")
else:
    print(f"   Error: {resp.text}")

# 2. Test POST /v2/orders (sell order - should fail with 401?)
print("\n2. Testing POST /v2/orders (sell 0.00244 MSFT)...")
data = {
    'symbol': 'MSFT',
    'qty': 0.00244,
    'side': 'sell',
    'type': 'market',
    'time_in_force': 'day',
    'extended_hours': False
}
resp = requests.post(f"{base_url}/v2/orders", json=data, headers=headers, timeout=10)
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.text[:200]}")

# 3. Test with notional instead of qty
print("\n3. Testing POST /v2/orders (sell $1 MSFT notional)...")
data = {
    'symbol': 'MSFT',
    'notional': 1.0,
    'side': 'sell',
    'type': 'market',
    'time_in_force': 'day',
    'extended_hours': False
}
resp = requests.post(f"{base_url}/v2/orders", json=data, headers=headers, timeout=10)
print(f"   Status: {resp.status_code}")
print(f"   Response: {resp.text[:200]}")
