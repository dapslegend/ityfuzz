#!/usr/bin/env python3
"""
Forge Transaction Simulator - Uses Anvil to simulate and maximize extraction
Requires: Foundry installed (forge, cast, anvil)
"""

import subprocess
import json
import re
import time
import sys
from typing import List, Dict, Tuple, Optional

class ForgeSimulator:
    """Simulates ItyFuzz vulnerabilities using Forge/Anvil"""
    
    def __init__(self, chain: str = "bsc", block_number: int = None):
        self.chain = chain
        self.block_number = block_number
        self.anvil_process = None
        self.anvil_port = 8545
        
        # RPC endpoints
        self.rpcs = {
            "eth": "https://eth-mainnet.g.alchemy.com/v2/demo",
            "bsc": "https://bsc-dataseed.binance.org/",
            "polygon": "https://polygon-rpc.com",
        }
        
        # Chain IDs
        self.chain_ids = {
            "eth": 1,
            "bsc": 56,
            "polygon": 137,
        }
        
        # Router addresses
        self.routers = {
            "eth": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            "bsc": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
            "polygon": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",
        }
    
    def start_anvil(self):
        """Start Anvil fork"""
        rpc_url = self.rpcs.get(self.chain)
        chain_id = self.chain_ids.get(self.chain)
        
        cmd = [
            "anvil",
            "--fork-url", rpc_url,
            "--fork-block-number", str(self.block_number) if self.block_number else "latest",
            "--chain-id", str(chain_id),
            "--port", str(self.anvil_port),
            "--accounts", "10",
            "--balance", "1000000",
            "--no-cors",
            "--silent"
        ]
        
        print(f"Starting Anvil fork of {self.chain} at block {self.block_number}...")
        self.anvil_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(3)  # Wait for Anvil to start
        
        # Verify Anvil is running
        try:
            result = self._cast_call("eth_blockNumber")
            print(f"Anvil started. Current block: {int(result, 16)}")
        except:
            print("Failed to start Anvil!")
            self.stop_anvil()
            raise
    
    def stop_anvil(self):
        """Stop Anvil"""
        if self.anvil_process:
            self.anvil_process.terminate()
            self.anvil_process.wait()
            print("Anvil stopped")
    
    def _cast_call(self, method: str, params: List = None) -> str:
        """Make RPC call using cast"""
        cmd = ["cast", "rpc", method]
        if params:
            cmd.extend(params)
        cmd.extend(["--rpc-url", f"http://localhost:{self.anvil_port}"])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Cast call failed: {result.stderr}")
        
        return result.stdout.strip().strip('"')
    
    def _send_transaction(self, from_addr: str, to_addr: str, value: str, data: str = "0x") -> str:
        """Send transaction using cast"""
        cmd = [
            "cast", "send",
            to_addr,
            data,
            "--from", from_addr,
            "--value", value,
            "--rpc-url", f"http://localhost:{self.anvil_port}",
            "--unlocked"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Transaction failed: {result.stderr}")
        
        # Extract transaction hash
        tx_hash_match = re.search(r'transactionHash\s+(0x[a-fA-F0-9]+)', result.stdout)
        return tx_hash_match.group(1) if tx_hash_match else ""
    
    def get_balance(self, address: str) -> int:
        """Get ETH balance of address"""
        result = self._cast_call("eth_getBalance", [address, "latest"])
        return int(result, 16)
    
    def simulate_vulnerability(self, transactions: List[Dict]) -> Dict:
        """Simulate vulnerability transactions"""
        # Get test account
        accounts = json.loads(self._cast_call("eth_accounts"))
        test_account = accounts[0]
        
        initial_balance = self.get_balance(test_account)
        print(f"\nTest account: {test_account}")
        print(f"Initial balance: {initial_balance / 1e18:.4f} ETH")
        
        results = []
        total_spent = 0
        
        for i, tx in enumerate(transactions):
            print(f"\nTransaction {i+1}:")
            
            # Prepare transaction
            to_addr = tx.get('to', '')
            value_eth = tx.get('value_eth', 0)
            value_wei = int(value_eth * 1e18)
            data = tx.get('data', '0x')
            
            # Replace router placeholder
            if to_addr == "Router":
                to_addr = self.routers.get(self.chain, to_addr)
            
            print(f"  To: {to_addr}")
            print(f"  Value: {value_eth} ETH")
            print(f"  Data: {data[:10]}...")
            
            try:
                # Send transaction
                tx_hash = self._send_transaction(test_account, to_addr, str(value_wei), data)
                print(f"  Success! Hash: {tx_hash}")
                
                total_spent += value_wei
                results.append({"success": True, "hash": tx_hash})
                
            except Exception as e:
                print(f"  Failed: {e}")
                results.append({"success": False, "error": str(e)})
                break
        
        # Calculate profit
        final_balance = self.get_balance(test_account)
        profit_wei = final_balance - initial_balance + total_spent
        profit_eth = profit_wei / 1e18
        
        print(f"\n=== Results ===")
        print(f"Final balance: {final_balance / 1e18:.4f} ETH")
        print(f"Total spent: {total_spent / 1e18:.4f} ETH")
        print(f"Net profit: {profit_eth:.4f} ETH")
        
        return {
            "success": all(r["success"] for r in results),
            "transactions": results,
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "profit_wei": profit_wei,
            "profit_eth": profit_eth
        }
    
    def find_maximum_extraction(self, base_transactions: List[Dict], 
                              multipliers: List[int] = [1, 2, 5, 10, 50, 100]) -> Dict:
        """Find maximum extraction by testing different multipliers"""
        print("\n=== Finding Maximum Extraction ===")
        
        best_multiplier = 1
        best_profit = 0
        results = {}
        
        for multiplier in multipliers:
            print(f"\nTesting {multiplier}x multiplier...")
            
            # Take snapshot
            snapshot_id = self._cast_call("evm_snapshot")
            
            # Modify transactions with multiplier
            test_txs = []
            for tx in base_transactions:
                test_tx = tx.copy()
                if test_tx.get('type') == 'swap' and test_tx.get('value_eth', 0) > 0:
                    test_tx['value_eth'] = test_tx['value_eth'] * multiplier
                test_txs.append(test_tx)
            
            try:
                # Simulate
                result = self.simulate_vulnerability(test_txs)
                results[multiplier] = result
                
                if result['success'] and result['profit_eth'] > best_profit:
                    best_profit = result['profit_eth']
                    best_multiplier = multiplier
                    print(f"  ✅ New best! Profit: {best_profit:.4f} ETH")
                
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                results[multiplier] = {"success": False, "error": str(e)}
            
            # Revert snapshot
            self._cast_call("evm_revert", [snapshot_id])
        
        return {
            "best_multiplier": best_multiplier,
            "best_profit": best_profit,
            "results": results
        }

def parse_ityfuzz_log(filepath: str) -> Tuple[float, List[Dict]]:
    """Parse ItyFuzz log to extract profit and transactions"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract profit
    profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', content)
    if not profit_match:
        raise ValueError("No vulnerability found in log")
    
    profit = float(profit_match.group(1))
    
    # Extract transactions from trace
    transactions = []
    trace_start = content.find("================ Trace ================")
    if trace_start != -1:
        trace = content[trace_start:trace_start + 2000]
        
        # Parse swaps
        swap_pattern = r'Router\.swapExactETHForTokens\{value: ([\d.]+) ether\}\((.*?)\)'
        for match in re.finditer(swap_pattern, trace):
            value = float(match.group(1))
            params = match.group(2)
            
            # Build transaction
            transactions.append({
                'type': 'swap',
                'to': 'Router',
                'value_eth': value,
                'data': '0x7ff36ab5'  # swapExactETHForTokens selector
            })
        
        # Parse other calls
        call_pattern = r'(0x[a-fA-F0-9]{40})\.(\w+)(?:\{value: ([\d.]+) ether\})?\((.*?)\)'
        for match in re.finditer(call_pattern, trace):
            target = match.group(1)
            function = match.group(2)
            value = float(match.group(3)) if match.group(3) else 0
            
            transactions.append({
                'type': 'call',
                'to': target,
                'value_eth': value,
                'data': '0x'  # Simplified - would need proper encoding
            })
    
    return profit, transactions

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python3 forge_simulator.py <logfile> [block_number]")
        print("\nExample: python3 forge_simulator.py bego_test_extended.log 22315679")
        sys.exit(1)
    
    logfile = sys.argv[1]
    block_number = int(sys.argv[2]) if len(sys.argv) > 2 else None
    
    # Parse log
    print(f"Parsing {logfile}...")
    try:
        reported_profit, transactions = parse_ityfuzz_log(logfile)
        print(f"Reported profit: {reported_profit:.4f} ETH")
        print(f"Found {len(transactions)} transactions")
    except Exception as e:
        print(f"Error parsing log: {e}")
        sys.exit(1)
    
    # Determine chain
    chain = "bsc" if "bsc" in logfile.lower() or "bego" in logfile.lower() else "eth"
    
    # Create simulator
    simulator = ForgeSimulator(chain, block_number)
    
    try:
        # Start Anvil
        simulator.start_anvil()
        
        # Test original
        print("\n=== Testing Original Vulnerability ===")
        original_result = simulator.simulate_vulnerability(transactions)
        
        if original_result['success']:
            print(f"\n✅ Original vulnerability confirmed!")
            print(f"Reported: {reported_profit:.4f} ETH")
            print(f"Simulated: {original_result['profit_eth']:.4f} ETH")
            
            # Find maximum
            print("\n=== Testing Maximum Extraction ===")
            max_result = simulator.find_maximum_extraction(transactions)
            
            print(f"\n🎯 MAXIMUM EXTRACTION RESULTS:")
            print(f"Best multiplier: {max_result['best_multiplier']}x")
            print(f"Maximum profit: {max_result['best_profit']:.4f} ETH")
            print(f"Improvement: {max_result['best_profit'] / reported_profit:.1f}x")
            
        else:
            print("\n❌ Original vulnerability simulation failed!")
            
    finally:
        simulator.stop_anvil()

if __name__ == "__main__":
    main()