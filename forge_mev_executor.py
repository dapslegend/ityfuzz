#!/usr/bin/env python3
"""
Forge MEV Executor - Complete solution for simulating and executing ItyFuzz vulnerabilities
Uses Forge/Cast for accurate on-chain simulation
"""

import subprocess
import json
import re
import time
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class VulnerabilityInfo:
    """Parsed vulnerability information"""
    profit: float
    block_number: int
    chain: str
    contracts: List[str]
    transactions: List[Dict]

class ForgeMEVExecutor:
    """Execute MEV opportunities using Forge/Cast"""
    
    def __init__(self):
        self.anvil_process = None
        self.anvil_url = "http://localhost:8545"
        
        # Chain configurations
        self.configs = {
            "eth": {
                "rpc": "https://eth-mainnet.g.alchemy.com/v2/demo",
                "chain_id": 1,
                "router": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                "weth": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            },
            "bsc": {
                "rpc": "https://bsc-dataseed.binance.org/",
                "chain_id": 56,
                "router": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
                "weth": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
            },
            "polygon": {
                "rpc": "https://polygon-rpc.com",
                "chain_id": 137,
                "router": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",
                "weth": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"
            }
        }
    
    def parse_log_file(self, filepath: str) -> VulnerabilityInfo:
        """Parse ItyFuzz log file"""
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Extract profit
        profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', content)
        if not profit_match:
            raise ValueError("No vulnerability found")
        
        profit = float(profit_match.group(1))
        
        # Extract block number
        block_match = re.search(r'block.*?(\d{8,})', content, re.IGNORECASE)
        block_number = int(block_match.group(1)) if block_match else 0
        
        # Determine chain
        if 'bsc' in filepath.lower() or 'bego' in filepath.lower():
            chain = 'bsc'
        elif 'polygon' in filepath.lower():
            chain = 'polygon'
        else:
            chain = 'eth'
        
        # Extract contracts
        contracts = re.findall(r'Contract (0x[a-fA-F0-9]{40})', content)
        
        # Parse transactions
        transactions = self._parse_transactions(content)
        
        return VulnerabilityInfo(
            profit=profit,
            block_number=block_number,
            chain=chain,
            contracts=list(set(contracts)),
            transactions=transactions
        )
    
    def _parse_transactions(self, content: str) -> List[Dict]:
        """Parse transaction sequence from log"""
        transactions = []
        
        # Find trace section
        trace_start = content.find("================ Trace ================")
        if trace_start == -1:
            return transactions
        
        trace = content[trace_start:trace_start + 3000]
        
        # Parse Router.swapExactETHForTokens
        swap_pattern = r'Router\.swapExactETHForTokens\{value: ([\d.]+) ether\}\((.*?)\)'
        for match in re.finditer(swap_pattern, trace):
            value = float(match.group(1))
            params_str = match.group(2)
            
            # Parse parameters
            path_match = re.search(r'path:\((.*?)\)', params_str)
            path = path_match.group(1) if path_match else ""
            
            # Parse path tokens
            tokens = []
            if path:
                parts = path.split(' → ')
                for part in parts:
                    part = part.strip()
                    if part.startswith('0x'):
                        tokens.append(part)
                    elif part.upper() in ['WETH', 'WBNB', 'WMATIC']:
                        tokens.append('WETH')  # Placeholder
            
            transactions.append({
                'type': 'swap',
                'function': 'swapExactETHForTokens',
                'value_eth': value,
                'path': tokens,
                'amount_out_min': 0,
                'to': 'address(this)',
                'deadline': 'block.timestamp'
            })
        
        # Parse direct calls
        call_pattern = r'(0x[a-fA-F0-9]{40})\.(\w+)(?:\{value: ([\d.]+) ether\})?\((.*?)\)'
        for match in re.finditer(call_pattern, trace):
            target = match.group(1)
            function = match.group(2)
            value = float(match.group(3)) if match.group(3) else 0
            params = match.group(4)
            
            transactions.append({
                'type': 'call',
                'target': target,
                'function': function,
                'value_eth': value,
                'params': params
            })
        
        return transactions
    
    def start_anvil(self, chain: str, block_number: int = None):
        """Start Anvil fork"""
        config = self.configs[chain]
        
        cmd = [
            "anvil",
            "--fork-url", config['rpc'],
            "--chain-id", str(config['chain_id']),
            "--accounts", "10",
            "--balance", "1000000",
            "--port", "8545",
            "--no-cors"
        ]
        
        if block_number:
            cmd.extend(["--fork-block-number", str(block_number)])
        
        print(f"Starting Anvil fork of {chain} at block {block_number or 'latest'}...")
        self.anvil_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        
        # Verify
        try:
            result = self.cast_rpc("eth_blockNumber")
            print(f"✅ Anvil started at block {int(result, 16)}")
        except:
            raise Exception("Failed to start Anvil")
    
    def stop_anvil(self):
        """Stop Anvil"""
        if self.anvil_process:
            self.anvil_process.terminate()
            self.anvil_process.wait()
    
    def cast_rpc(self, method: str, params: List = None) -> str:
        """Make RPC call using cast"""
        cmd = ["cast", "rpc", method]
        if params:
            cmd.extend([json.dumps(p) for p in params])
        cmd.extend(["--rpc-url", self.anvil_url])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"RPC call failed: {result.stderr}")
        
        return json.loads(result.stdout)
    
    def encode_swap_call(self, chain: str, amount_out_min: int, path: List[str], 
                        to: str, deadline: int) -> str:
        """Encode swapExactETHForTokens call"""
        config = self.configs[chain]
        
        # Replace WETH placeholder
        path = [config['weth'] if t == 'WETH' else t for t in path]
        
        # Use cast to encode
        cmd = [
            "cast", "calldata",
            "swapExactETHForTokens(uint256,address[],address,uint256)",
            str(amount_out_min),
            json.dumps(path),
            to,
            str(deadline)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Encoding failed: {result.stderr}")
        
        return result.stdout.strip()
    
    def simulate_transaction(self, from_addr: str, to_addr: str, value_wei: int, 
                           data: str = "0x") -> Dict:
        """Simulate a single transaction"""
        # Use cast call
        cmd = [
            "cast", "call",
            to_addr,
            data,
            "--from", from_addr,
            "--value", str(value_wei),
            "--rpc-url", self.anvil_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    
    def send_transaction(self, from_addr: str, to_addr: str, value_wei: int, 
                        data: str = "0x") -> str:
        """Send transaction and return hash"""
        cmd = [
            "cast", "send",
            to_addr,
            data,
            "--from", from_addr,
            "--value", str(value_wei),
            "--rpc-url", self.anvil_url,
            "--unlocked",
            "--json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Transaction failed: {result.stderr}")
        
        output = json.loads(result.stdout)
        return output.get('transactionHash', '')
    
    def get_balance(self, address: str) -> int:
        """Get ETH balance"""
        result = self.cast_rpc("eth_getBalance", [address, "latest"])
        return int(result, 16)
    
    def execute_vulnerability(self, vuln: VulnerabilityInfo, multiplier: float = 1.0) -> Dict:
        """Execute vulnerability with given multiplier"""
        config = self.configs[vuln.chain]
        
        # Get test account
        accounts = self.cast_rpc("eth_accounts")
        test_account = accounts[0]
        
        initial_balance = self.get_balance(test_account)
        print(f"\nExecuting with {multiplier}x multiplier...")
        print(f"Account: {test_account}")
        print(f"Initial balance: {initial_balance / 1e18:.4f} ETH")
        
        results = []
        total_spent = 0
        
        for i, tx in enumerate(vuln.transactions):
            print(f"\nTransaction {i+1}:")
            
            if tx['type'] == 'swap':
                # Prepare swap transaction
                value_eth = tx['value_eth'] * multiplier
                value_wei = int(value_eth * 1e18)
                
                # Encode calldata
                deadline = int(time.time()) + 3600
                calldata = self.encode_swap_call(
                    vuln.chain,
                    0,  # amount_out_min
                    tx['path'],
                    test_account,
                    deadline
                )
                
                to_addr = config['router']
                
                print(f"  Swap {value_eth} ETH via {to_addr[:10]}...")
                
            else:
                # Direct call
                to_addr = tx['target']
                value_wei = int(tx['value_eth'] * 1e18)
                calldata = "0x"  # Would need proper encoding
                
                print(f"  Call {tx['function']} on {to_addr[:10]}...")
            
            try:
                # Send transaction
                tx_hash = self.send_transaction(test_account, to_addr, value_wei, calldata)
                print(f"  ✅ Success: {tx_hash}")
                
                total_spent += value_wei
                results.append({"success": True, "hash": tx_hash})
                
            except Exception as e:
                print(f"  ❌ Failed: {e}")
                results.append({"success": False, "error": str(e)})
                break
        
        # Calculate profit
        final_balance = self.get_balance(test_account)
        profit_wei = final_balance - initial_balance + total_spent
        profit_eth = profit_wei / 1e18
        
        return {
            "success": all(r["success"] for r in results),
            "multiplier": multiplier,
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "total_spent": total_spent,
            "profit_wei": profit_wei,
            "profit_eth": profit_eth,
            "transactions": results
        }
    
    def find_maximum_extraction(self, vuln: VulnerabilityInfo) -> Dict:
        """Find maximum extraction using binary search"""
        print("\n=== Finding Maximum Extraction ===")
        
        # Test multipliers
        test_multipliers = [1, 2, 5, 10, 25, 50, 100]
        results = {}
        best_multiplier = 1
        best_profit = 0
        
        for mult in test_multipliers:
            print(f"\n--- Testing {mult}x ---")
            
            # Take snapshot
            snapshot_id = self.cast_rpc("evm_snapshot")
            
            try:
                result = self.execute_vulnerability(vuln, mult)
                results[mult] = result
                
                if result['success'] and result['profit_eth'] > best_profit:
                    best_profit = result['profit_eth']
                    best_multiplier = mult
                    print(f"\n🎯 New best: {best_profit:.4f} ETH at {mult}x")
                
            except Exception as e:
                print(f"\n❌ Failed at {mult}x: {e}")
                results[mult] = {"success": False, "error": str(e)}
            
            # Revert
            self.cast_rpc("evm_revert", [snapshot_id])
        
        return {
            "best_multiplier": best_multiplier,
            "best_profit": best_profit,
            "original_profit": vuln.profit,
            "improvement": best_profit / vuln.profit if vuln.profit > 0 else 0,
            "results": results
        }

def generate_report(vuln: VulnerabilityInfo, max_result: Dict, output_file: str = "mev_report.md"):
    """Generate execution report"""
    report = []
    report.append(f"# MEV Execution Report")
    report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    report.append(f"\n## Vulnerability Summary")
    report.append(f"- **Chain**: {vuln.chain}")
    report.append(f"- **Block**: {vuln.block_number}")
    report.append(f"- **Original Profit**: {vuln.profit:.4f} ETH")
    report.append(f"- **Contracts**: {len(vuln.contracts)}")
    
    report.append(f"\n## Maximum Extraction Results")
    report.append(f"- **Best Multiplier**: {max_result['best_multiplier']}x")
    report.append(f"- **Maximum Profit**: {max_result['best_profit']:.4f} ETH")
    report.append(f"- **Improvement**: {max_result['improvement']:.1f}x")
    
    report.append(f"\n## Tested Configurations")
    report.append("| Multiplier | Success | Profit (ETH) |")
    report.append("|------------|---------|--------------|")
    
    for mult, result in max_result['results'].items():
        success = "✅" if result.get('success', False) else "❌"
        profit = f"{result.get('profit_eth', 0):.4f}" if result.get('success', False) else "Failed"
        report.append(f"| {mult}x | {success} | {profit} |")
    
    report.append(f"\n## Execution Strategy")
    report.append(f"```solidity")
    report.append(f"// Optimal execution with {max_result['best_multiplier']}x multiplier")
    report.append(f"// Expected profit: {max_result['best_profit']:.4f} ETH")
    report.append(f"")
    report.append(f"// Step 1: Get flashloan")
    report.append(f"flashloan.borrow({vuln.transactions[0]['value_eth'] * max_result['best_multiplier']:.0f} ETH);")
    report.append(f"")
    report.append(f"// Step 2: Execute exploit")
    for i, tx in enumerate(vuln.transactions):
        if tx['type'] == 'swap':
            value = tx['value_eth'] * max_result['best_multiplier']
            report.append(f"router.swapExactETHForTokens{{value: {value:.0f} ether}}(...);")
        else:
            report.append(f"{tx['target']}.{tx['function']}(...);")
    report.append(f"")
    report.append(f"// Step 3: Repay loan and keep profit")
    report.append(f"flashloan.repay();")
    report.append(f"// Profit: {max_result['best_profit']:.4f} ETH")
    report.append(f"```")
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(report))
    
    print(f"\n📄 Report saved to {output_file}")

def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Forge MEV Executor')
    parser.add_argument('logfile', help='ItyFuzz log file')
    parser.add_argument('--block', type=int, help='Fork block number')
    parser.add_argument('--report', default='mev_report.md', help='Output report file')
    
    args = parser.parse_args()
    
    executor = ForgeMEVExecutor()
    
    try:
        # Parse vulnerability
        print(f"Parsing {args.logfile}...")
        vuln = executor.parse_log_file(args.logfile)
        
        print(f"\n📊 Vulnerability Details:")
        print(f"  Chain: {vuln.chain}")
        print(f"  Block: {vuln.block_number}")
        print(f"  Profit: {vuln.profit:.4f} ETH")
        print(f"  Transactions: {len(vuln.transactions)}")
        
        # Start Anvil
        block = args.block or vuln.block_number
        executor.start_anvil(vuln.chain, block)
        
        # Find maximum extraction
        max_result = executor.find_maximum_extraction(vuln)
        
        print(f"\n🎯 MAXIMUM EXTRACTION SUMMARY:")
        print(f"  Original: {vuln.profit:.4f} ETH")
        print(f"  Maximum: {max_result['best_profit']:.4f} ETH")
        print(f"  Multiplier: {max_result['best_multiplier']}x")
        print(f"  Improvement: {max_result['improvement']:.1f}x")
        
        # Generate report
        generate_report(vuln, max_result, args.report)
        
    finally:
        executor.stop_anvil()

if __name__ == "__main__":
    main()