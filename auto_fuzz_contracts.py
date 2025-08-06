#!/usr/bin/env python3
"""
Auto Fuzz Contracts - Automatically find and fuzz contracts on BSC
"""

import subprocess
import json
import time
import os
import re
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

class ContractScanner:
    """Scan blockchain for contracts with potential vulnerabilities"""
    
    def __init__(self, historical_rpc: str = "http://159.198.35.169:8545", 
                 public_rpc: str = "https://bsc-dataseed.binance.org/"):
        self.historical_rpc = historical_rpc
        self.public_rpc = public_rpc
        self.bsc_api_key = "YourBSCApiKey"  # From the backtest scripts
        
        # Common token interfaces
        self.token_selectors = {
            "0x70a08231": "balanceOf(address)",
            "0x18160ddd": "totalSupply()",
            "0x95d89b41": "symbol()",
            "0x06fdde03": "name()",
            "0xa9059cbb": "transfer(address,uint256)",
            "0x23b872dd": "transferFrom(address,address,uint256)",
            "0xdd62ed3e": "allowance(address,address)"
        }
        
        # Vulnerable function selectors
        self.vuln_selectors = {
            "0x3ccfd60b": "withdraw()",
            "0x853828b6": "withdrawAll()",
            "0xdb2e21bc": "emergencyWithdraw()",
            "0xbc25cf77": "skim(address)",
            "0x2e1a7d4d": "withdraw(uint256)",
            "0x69328dec": "harvest(address,uint256)"
        }
        
        # Known routers
        self.routers = {
            "0x10ED43C718714eb63d5aA57B78B54704E256024E": "PancakeSwap",
            "0xcF0feBd3f17CEf5b47b0cD257aCf6025c5BFf3b7": "ApeSwap",
            "0x3a6d8cA21D1CF76F653A67577FA0D27453350dD8": "BiSwap"
        }
        
        # WBNB address
        self.wbnb = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
    
    def get_latest_blocks(self) -> Dict:
        """Get latest block numbers from both RPCs"""
        historical_block = int(subprocess.check_output([
            "cast", "block-number", "--rpc-url", self.historical_rpc
        ]).decode().strip())
        
        public_block = int(subprocess.check_output([
            "cast", "block-number", "--rpc-url", self.public_rpc
        ]).decode().strip())
        
        return {
            "historical": historical_block,
            "public": public_block,
            "range": (historical_block - 1000, historical_block)  # Last 1000 blocks
        }
    
    def scan_block_for_contracts(self, block_num: int) -> List[str]:
        """Scan a block for contract creations"""
        contracts = []
        
        try:
            # Get block with transactions
            block_data = subprocess.check_output([
                "cast", "block", str(block_num), 
                "--json", "--rpc-url", self.historical_rpc
            ]).decode()
            
            block = json.loads(block_data)
            
            # Check each transaction
            for tx_hash in block.get("transactions", []):
                # Get transaction receipt
                receipt = subprocess.check_output([
                    "cast", "receipt", tx_hash,
                    "--json", "--rpc-url", self.historical_rpc
                ]).decode()
                
                receipt_data = json.loads(receipt)
                
                # Check if contract creation
                if receipt_data.get("contractAddress"):
                    contracts.append(receipt_data["contractAddress"])
                    
        except Exception as e:
            pass
        
        return contracts
    
    def analyze_contract(self, address: str) -> Dict:
        """Analyze a contract to find its tokens and functions"""
        result = {
            "address": address,
            "has_code": False,
            "is_token": False,
            "has_vulnerable_functions": False,
            "tokens": [],
            "pairs": [],
            "functions": []
        }
        
        try:
            # Get contract code
            code = subprocess.check_output([
                "cast", "code", address, "--rpc-url", self.historical_rpc
            ]).decode().strip()
            
            if len(code) <= 2:
                return result
            
            result["has_code"] = True
            
            # Check if it's a token
            token_funcs = 0
            for selector, name in self.token_selectors.items():
                if selector[2:] in code:  # Remove 0x prefix
                    token_funcs += 1
                    
            if token_funcs >= 4:  # Has most token functions
                result["is_token"] = True
            
            # Check for vulnerable functions
            for selector, name in self.vuln_selectors.items():
                if selector[2:] in code:
                    result["has_vulnerable_functions"] = True
                    result["functions"].append(name)
            
            # Try to find associated tokens
            result["tokens"] = self.find_associated_tokens(address)
            
        except Exception as e:
            pass
        
        return result
    
    def find_associated_tokens(self, contract: str) -> List[Dict]:
        """Find tokens associated with a contract"""
        tokens = []
        
        # Common token storage slots
        for slot in range(0, 20):
            try:
                # Read storage slot
                value = subprocess.check_output([
                    "cast", "storage", contract, str(slot),
                    "--rpc-url", self.historical_rpc
                ]).decode().strip()
                
                # Check if it looks like an address
                if value.startswith("0x000000000000000000000000"):
                    addr = "0x" + value[-40:]
                    
                    # Verify it's a token
                    try:
                        symbol = subprocess.check_output([
                            "cast", "call", addr, "symbol()(string)",
                            "--rpc-url", self.historical_rpc
                        ]).decode().strip()
                        
                        if symbol:
                            tokens.append({
                                "address": addr,
                                "symbol": symbol,
                                "slot": slot
                            })
                    except:
                        pass
                        
            except:
                pass
        
        return tokens
    
    def find_liquidity_pairs(self, token: str) -> List[str]:
        """Find liquidity pairs for a token"""
        pairs = []
        
        # Check PancakeSwap factory
        factory = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
        
        try:
            # Get pair address
            pair = subprocess.check_output([
                "cast", "call", factory,
                "getPair(address,address)(address)",
                self.wbnb, token,
                "--rpc-url", self.historical_rpc
            ]).decode().strip()
            
            if pair != "0x0000000000000000000000000000000000000000":
                pairs.append(pair)
                
        except:
            pass
        
        return pairs

class ItyFuzzRunner:
    """Run ItyFuzz on contracts"""
    
    def __init__(self, public_rpc: str):
        self.public_rpc = public_rpc
        self.ityfuzz_path = "./target/debug/cli"
        
    def fuzz_contract(self, contract_info: Dict, block_num: int, 
                     timeout: int = 60) -> Dict:
        """Fuzz a single contract"""
        
        result = {
            "contract": contract_info["address"],
            "status": "pending",
            "vulnerabilities": [],
            "output": ""
        }
        
        # Build command
        cmd = [
            self.ityfuzz_path,
            "-t", contract_info["address"],
            "-c", "BSC",
            "--onchain-block-number", str(block_num),
            "-f", "-i", "-p",
            "--run-forever", str(timeout)
        ]
        
        # Add token addresses if found
        if contract_info["tokens"]:
            for token in contract_info["tokens"]:
                cmd.extend(["-t", token["address"]])
        
        # Add WBNB
        cmd.extend(["-t", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"])
        
        # Set RPC
        env = os.environ.copy()
        env["ETH_RPC_URL"] = self.public_rpc
        
        print(f"\nFuzzing {contract_info['address']}...")
        print(f"Command: {' '.join(cmd)}")
        
        try:
            # Run fuzzer
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Wait for timeout
            stdout, stderr = process.communicate(timeout=timeout + 10)
            
            output = stdout.decode() + stderr.decode()
            result["output"] = output
            
            # Parse for vulnerabilities
            if "Anyone can earn" in output:
                profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', output)
                if profit_match:
                    result["vulnerabilities"].append({
                        "type": "profit",
                        "amount": float(profit_match.group(1))
                    })
                    result["status"] = "vulnerable"
            else:
                result["status"] = "clean"
                
        except subprocess.TimeoutExpired:
            process.kill()
            result["status"] = "timeout"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result

def main():
    """Main execution"""
    print("=== Auto Fuzz BSC Contracts ===\n")
    
    # Initialize scanner
    scanner = ContractScanner()
    
    # Get block ranges
    blocks = scanner.get_latest_blocks()
    print(f"Historical RPC latest: {blocks['historical']}")
    print(f"Public RPC latest: {blocks['public']}")
    print(f"Scanning blocks: {blocks['range'][0]} to {blocks['range'][1]}")
    
    # Scan for contracts
    print("\n=== Scanning for Contracts ===")
    all_contracts = []
    
    # Use thread pool for faster scanning
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        
        for block in range(blocks['range'][0], blocks['range'][1]):
            future = executor.submit(scanner.scan_block_for_contracts, block)
            futures.append(future)
        
        for future in as_completed(futures):
            contracts = future.result()
            all_contracts.extend(contracts)
    
    print(f"\nFound {len(all_contracts)} contracts")
    
    # Analyze contracts
    print("\n=== Analyzing Contracts ===")
    vulnerable_contracts = []
    
    for contract in all_contracts[:50]:  # Limit to first 50
        info = scanner.analyze_contract(contract)
        
        if info["has_code"] and (info["has_vulnerable_functions"] or info["tokens"]):
            vulnerable_contracts.append(info)
            print(f"\n{contract}:")
            print(f"  Token: {info['is_token']}")
            print(f"  Vulnerable functions: {info['functions']}")
            print(f"  Associated tokens: {len(info['tokens'])}")
    
    print(f"\nFound {len(vulnerable_contracts)} potentially vulnerable contracts")
    
    # Fuzz contracts
    print("\n=== Fuzzing Contracts ===")
    fuzzer = ItyFuzzRunner(scanner.public_rpc)
    
    results = []
    for contract_info in vulnerable_contracts[:10]:  # Limit to first 10
        result = fuzzer.fuzz_contract(
            contract_info, 
            blocks['public'] - 1,  # Use recent block
            timeout=60  # 1 minute timeout
        )
        results.append(result)
        
        if result["status"] == "vulnerable":
            print(f"\n🚨 VULNERABILITY FOUND in {contract_info['address']}!")
            print(f"   Profit: {result['vulnerabilities'][0]['amount']} ETH")
    
    # Save results
    with open("auto_fuzz_results.json", "w") as f:
        json.dump({
            "scan_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "blocks_scanned": blocks,
            "contracts_found": len(all_contracts),
            "contracts_analyzed": len(vulnerable_contracts),
            "results": results
        }, f, indent=2)
    
    print("\n✅ Results saved to auto_fuzz_results.json")

if __name__ == "__main__":
    main()