#!/usr/bin/env python3
"""Debug Forge issues"""

import subprocess
import json

# Check current block
block = subprocess.check_output([
    "cast", "block-number", "--rpc-url", "http://localhost:8545"
]).decode().strip()

print(f"Current block: {block}")

# Check account balance
accounts = json.loads(subprocess.check_output([
    "cast", "rpc", "eth_accounts", "--rpc-url", "http://localhost:8545"
]).decode())

account = accounts[0]
balance = subprocess.check_output([
    "cast", "balance", account, "--rpc-url", "http://localhost:8545"
]).decode().strip()

print(f"Account: {account}")
print(f"Balance: {int(balance) / 1e18:.4f} ETH")

# Check if contracts exist
contracts = {
    "PancakeRouter": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
    "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    "BEGO": "0xc342774492b54ce5F8ac662113ED702Fc1b34972"
}

for name, addr in contracts.items():
    code = subprocess.check_output([
        "cast", "code", addr, "--rpc-url", "http://localhost:8545"
    ]).decode().strip()
    
    print(f"\n{name} ({addr}):")
    print(f"  Has code: {'Yes' if len(code) > 2 else 'No'}")
    
    if len(code) > 2:
        # Try to get token info
        if name != "PancakeRouter":
            try:
                symbol = subprocess.check_output([
                    "cast", "call", addr, "symbol()(string)",
                    "--rpc-url", "http://localhost:8545"
                ]).decode().strip()
                print(f"  Symbol: {symbol}")
            except:
                pass

# Test simple swap encoding
print("\n=== Testing Swap Encoding ===")

# Manual encoding test
selector = "0x7ff36ab5"  # swapExactETHForTokens
print(f"Selector: {selector}")

# Try direct swap
print("\nTrying direct swap...")
result = subprocess.run([
    "cast", "send",
    contracts["PancakeRouter"],
    "swapExactETHForTokens(uint256,address[],address,uint256)(uint256[])",
    "0",  # amountOutMin
    f'[{contracts["WBNB"]},{contracts["BEGO"]}]',  # path
    account,  # to
    "9999999999",  # deadline
    "--from", account,
    "--value", "1ether",
    "--rpc-url", "http://localhost:8545",
    "--unlocked"
], capture_output=True, text=True)

if result.returncode == 0:
    print("✅ Swap successful!")
else:
    print(f"❌ Swap failed: {result.stderr}")