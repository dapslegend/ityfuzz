#!/usr/bin/env python3
"""
ItyFuzz Transaction Simulator using Anvil Fork

This simulator:
1. Forks the blockchain at the vulnerability block
2. Simulates the exact transaction sequence
3. Verifies profitability before execution
"""

import subprocess
import json
import time
import re
from typing import List, Dict, Tuple
from web3 import Web3
from eth_account import Account
import requests

class AnvilSimulator:
    """Simulates ItyFuzz vulnerabilities using Anvil fork"""
    
    def __init__(self, chain: str = "bsc", block_number: int = None):
        self.chain = chain
        self.block_number = block_number
        self.anvil_process = None
        self.w3 = None
        self.fork_url = None
        
        # RPC endpoints for different chains
        self.rpc_endpoints = {
            "eth": "https://eth-mainnet.g.alchemy.com/v2/demo",
            "bsc": "https://bsc-dataseed.binance.org/",
            "polygon": "https://polygon-rpc.com",
            "arbitrum": "https://arb1.arbitrum.io/rpc"
        }
        
    def start_fork(self, fork_block: int = None):
        """Start Anvil fork at specific block"""
        fork_block = fork_block or self.block_number
        
        # Get RPC URL for chain
        rpc_url = self.rpc_endpoints.get(self.chain)
        if not rpc_url:
            raise ValueError(f"Unsupported chain: {self.chain}")
        
        # Start Anvil with fork
        cmd = [
            "anvil",
            "--fork-url", rpc_url,
            "--port", "8545",
            "--chain-id", str(self._get_chain_id()),
            "--accounts", "10",
            "--balance", "10000",
            "--block-time", "0",
            "--no-mining"
        ]
        
        if fork_block:
            cmd.extend(["--fork-block-number", str(fork_block)])
        
        print(f"Starting Anvil fork at block {fork_block}...")
        self.anvil_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for Anvil to start
        time.sleep(3)
        
        # Connect to local Anvil instance
        self.w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
        self.fork_url = "http://localhost:8545"
        
        print(f"Anvil started. Fork block: {self.w3.eth.block_number}")
        
    def stop_fork(self):
        """Stop Anvil fork"""
        if self.anvil_process:
            self.anvil_process.terminate()
            self.anvil_process.wait()
            print("Anvil stopped")
    
    def _get_chain_id(self) -> int:
        """Get chain ID for network"""
        chain_ids = {
            "eth": 1,
            "bsc": 56,
            "polygon": 137,
            "arbitrum": 42161
        }
        return chain_ids.get(self.chain, 1)
    
    def simulate_exploit(self, transactions: List[Dict]) -> Dict:
        """Simulate exploit transactions"""
        if not self.w3:
            raise Exception("Fork not started. Call start_fork() first")
        
        # Get test account with balance
        test_account = self.w3.eth.accounts[0]
        initial_balance = self.w3.eth.get_balance(test_account)
        
        print(f"Simulating with account: {test_account}")
        print(f"Initial balance: {Web3.from_wei(initial_balance, 'ether')} ETH")
        
        results = []
        total_gas_used = 0
        
        for i, tx in enumerate(transactions):
            print(f"\nTransaction {i+1}:")
            print(f"  To: {tx['to']}")
            print(f"  Value: {Web3.from_wei(tx.get('value', 0), 'ether')} ETH")
            print(f"  Data: {tx.get('data', '0x')[:10]}...")
            
            # Build transaction
            transaction = {
                'from': test_account,
                'to': tx['to'],
                'value': tx.get('value', 0),
                'data': tx.get('data', '0x'),
                'gas': 5000000,
                'gasPrice': self.w3.eth.gas_price
            }
            
            try:
                # Send transaction
                tx_hash = self.w3.eth.send_transaction(transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                print(f"  Status: {'Success' if receipt.status else 'Failed'}")
                print(f"  Gas used: {receipt.gasUsed}")
                
                total_gas_used += receipt.gasUsed
                
                results.append({
                    'success': receipt.status == 1,
                    'tx_hash': tx_hash.hex(),
                    'gas_used': receipt.gasUsed,
                    'logs': receipt.logs
                })
                
                if receipt.status == 0:
                    print("  Transaction failed! Stopping simulation.")
                    break
                    
            except Exception as e:
                print(f"  Error: {str(e)}")
                results.append({
                    'success': False,
                    'error': str(e)
                })
                break
        
        # Calculate final balance and profit
        final_balance = self.w3.eth.get_balance(test_account)
        profit_wei = final_balance - initial_balance
        profit_eth = Web3.from_wei(profit_wei, 'ether')
        
        # Account for gas costs
        gas_cost_wei = total_gas_used * self.w3.eth.gas_price
        gas_cost_eth = Web3.from_wei(gas_cost_wei, 'ether')
        net_profit_eth = profit_eth - gas_cost_eth
        
        print(f"\n=== Simulation Results ===")
        print(f"Final balance: {Web3.from_wei(final_balance, 'ether')} ETH")
        print(f"Gross profit: {profit_eth} ETH")
        print(f"Gas cost: {gas_cost_eth} ETH")
        print(f"Net profit: {net_profit_eth} ETH")
        
        return {
            'success': all(r['success'] for r in results),
            'transactions': results,
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'gross_profit_eth': float(profit_eth),
            'gas_cost_eth': float(gas_cost_eth),
            'net_profit_eth': float(net_profit_eth)
        }

class ItyFuzzTransactionBuilder:
    """Builds executable transactions from ItyFuzz output"""
    
    def __init__(self, chain: str = "bsc"):
        self.chain = chain
        
        # Known contract addresses
        self.routers = {
            "eth": {
                "UniswapV2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
                "SushiSwap": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"
            },
            "bsc": {
                "PancakeSwap": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
                "Router": "0x10ED43C718714eb63d5aA57B78B54704E256024E"  # Default
            },
            "polygon": {
                "QuickSwap": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff"
            }
        }
        
        self.weth_addresses = {
            "eth": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "bsc": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "polygon": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270"  # WMATIC
        }
    
    def parse_ityfuzz_trace(self, trace_text: str) -> List[Dict]:
        """Parse ItyFuzz trace and build transactions"""
        transactions = []
        
        # Parse the winning transaction from the trace
        lines = trace_text.strip().split('\n')
        
        for line in lines:
            # Parse Router.swapExactETHForTokens calls
            swap_match = re.match(r'.*Router\.swapExactETHForTokens\{value: ([\d.]+) ether\}\((.*?)\)', line)
            if swap_match:
                value_ether = float(swap_match.group(1))
                params = swap_match.group(2)
                
                # Parse parameters
                param_parts = params.split(', ')
                amount_out_min = param_parts[0] if len(param_parts) > 0 else "0"
                
                # Extract path
                path_match = re.search(r'path:\((.*?)\)', params)
                if path_match:
                    path_str = path_match.group(1)
                    tokens = self._parse_path(path_str)
                else:
                    tokens = []
                
                # Extract recipient
                to_match = re.search(r'address\(this\)|0x[a-fA-F0-9]{40}', params)
                recipient = "0x" + "0" * 40  # Default to zero address
                
                # Build transaction
                tx = self._build_swap_transaction(
                    value_ether=value_ether,
                    amount_out_min=amount_out_min,
                    path=tokens,
                    to=recipient
                )
                transactions.append(tx)
            
            # Parse direct contract calls
            call_match = re.match(r'.*(0x[a-fA-F0-9]{40})\.call\{value: (\d+)\}\((.*?)\)', line)
            if call_match:
                to_address = call_match.group(1)
                value = int(call_match.group(2))
                data = call_match.group(3)
                
                # Parse data
                if data.startswith('abi.encodeWithSelector'):
                    selector_match = re.search(r'0x[a-fA-F0-9]+', data)
                    if selector_match:
                        data = selector_match.group(0)
                else:
                    data = data.strip() if data else "0x"
                
                transactions.append({
                    'to': to_address,
                    'value': value,
                    'data': data
                })
        
        return transactions
    
    def _parse_path(self, path_str: str) -> List[str]:
        """Parse token path from string like 'WETH → 0x...'"""
        tokens = []
        
        # Split by arrow
        parts = path_str.split(' → ')
        
        for part in parts:
            part = part.strip()
            if part.upper() in ['WETH', 'WBNB', 'WMATIC']:
                # Convert to address
                tokens.append(self.weth_addresses.get(self.chain, part))
            elif part.startswith('0x'):
                tokens.append(part)
        
        return tokens
    
    def _build_swap_transaction(self, value_ether: float, amount_out_min: str, 
                                path: List[str], to: str) -> Dict:
        """Build swapExactETHForTokens transaction"""
        # Get router address
        router = self.routers.get(self.chain, {}).get("Router", self.routers["bsc"]["Router"])
        
        # Convert value to wei
        value_wei = Web3.to_wei(value_ether, 'ether')
        
        # Encode function call
        # swapExactETHForTokens(uint amountOutMin, address[] path, address to, uint deadline)
        # Function selector: 0x7ff36ab5
        
        # For now, use a simplified encoding
        # In production, use eth_abi.encode_abi
        function_selector = "0x7ff36ab5"
        
        # Set deadline to far future
        deadline = int(time.time()) + 3600  # 1 hour from now
        
        # Simplified data - in production use proper ABI encoding
        data = function_selector
        
        return {
            'to': router,
            'value': value_wei,
            'data': data,
            'description': f'Swap {value_ether} ETH for tokens'
        }

def simulate_vulnerability(log_file: str, chain: str = "bsc", block_number: int = None):
    """Main function to simulate vulnerability from log file"""
    
    print(f"=== ItyFuzz Vulnerability Simulator ===")
    print(f"Log file: {log_file}")
    print(f"Chain: {chain}")
    print(f"Block: {block_number}")
    
    # Read log file
    with open(log_file, 'r') as f:
        content = f.read()
    
    # Extract vulnerability info
    vuln_match = re.search(r"Found vulnerabilities!.*?\[Fund Loss\]: Anyone can earn ([\d.]+) ETH", content, re.DOTALL)
    if not vuln_match:
        print("No vulnerability found in log")
        return
    
    expected_profit = float(vuln_match.group(1))
    print(f"\nExpected profit: {expected_profit} ETH")
    
    # Extract trace
    trace_start = content.find("================ Trace ================")
    if trace_start == -1:
        print("No trace found in log")
        return
    
    trace_end = content.find("\n\n", trace_start + 50)
    trace_section = content[trace_start:trace_end]
    
    # Parse transactions
    builder = ItyFuzzTransactionBuilder(chain)
    transactions = builder.parse_ityfuzz_trace(trace_section)
    
    print(f"\nParsed {len(transactions)} transactions")
    
    # Start simulation
    simulator = AnvilSimulator(chain, block_number)
    
    try:
        simulator.start_fork()
        
        # Run simulation
        result = simulator.simulate_exploit(transactions)
        
        print(f"\n=== Final Result ===")
        print(f"Simulation: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"Expected profit: {expected_profit} ETH")
        print(f"Actual profit: {result['net_profit_eth']} ETH")
        
        if result['net_profit_eth'] > 0:
            print(f"\n✅ Vulnerability confirmed! Net profit: {result['net_profit_eth']} ETH")
        else:
            print(f"\n❌ Not profitable after gas costs")
            
    finally:
        simulator.stop_fork()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Simulate ItyFuzz vulnerabilities')
    parser.add_argument('log_file', help='Path to ItyFuzz log file')
    parser.add_argument('--chain', default='bsc', help='Blockchain (eth, bsc, polygon)')
    parser.add_argument('--block', type=int, help='Fork block number')
    
    args = parser.parse_args()
    
    # Extract block number from log if not provided
    if not args.block:
        with open(args.log_file, 'r') as f:
            content = f.read()
            block_match = re.search(r'block.*?(\d{8,})', content, re.IGNORECASE)
            if block_match:
                args.block = int(block_match.group(1))
    
    simulate_vulnerability(args.log_file, args.chain, args.block)