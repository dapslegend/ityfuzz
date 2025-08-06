#!/usr/bin/env python3
"""
Debug ABI fetching issue
"""

import requests
import json

# Test fetching ABI from Etherscan
api_key = "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
contract = "0x68Cc90351a79A4c10078FE021bE430b7a12aaA09"  # BEGO

url = f"https://api.etherscan.io/v2/api?chainid=56&module=contract&action=getabi&address={contract.lower()}&format=json&apikey={api_key}"

print(f"Fetching ABI from: {url}")
response = requests.get(url)

print(f"Status code: {response.status_code}")
print(f"Response (first 500 chars): {response.text[:500]}")

try:
    data = response.json()
    print(f"\nParsed JSON structure: {list(data.keys()) if isinstance(data, dict) else type(data)}")
    
    if isinstance(data, dict) and 'result' in data:
        result = data['result']
        print(f"Result type: {type(result)}")
        if isinstance(result, str):
            print(f"Result (first 200 chars): {result[:200]}")
            # Try to parse the result as JSON
            try:
                abi = json.loads(result)
                print(f"Successfully parsed ABI, found {len(abi)} entries")
            except:
                print("Failed to parse result as JSON")
except Exception as e:
    print(f"Error parsing response: {e}")

# Also check if the API endpoint is correct
print("\n\nChecking alternative endpoints:")
alt_url = f"https://api.bscscan.com/api?module=contract&action=getabi&address={contract}&apikey={api_key}"
print(f"Alternative URL: {alt_url}")