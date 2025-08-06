#!/usr/bin/env python3
"""
BSC Auto Fuzzer - Uses Etherscan API v2 to find and fuzz contracts
"""

import subprocess
import json
import time
import os
import re
import requests
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

class BSCContractFinder:
    """Find contracts using Etherscan API v2"""
    
    def __init__(self):
        # Etherscan API v2 configuration
        self.api_key = "6J26IP7U4YSMEUFVWQWJJRMIT2XNBY2VPU"  # From backtest
        self.base_url = "https://api.etherscan.io/v2/api"
        self.chain_id = "56"  # BSC
        
        # RPC endpoints
        self.historical_rpc = "http://159.198.35.169:8545"
        self.public_rpc = "https://bsc-dataseed.binance.org/"
        
        # Known addresses
        self.wbnb = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
        self.pancake_router = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
        self.pancake_factory = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
        
    def get_verified_contracts(self, page: int = 1, offset: int = 100) -> List[Dict]:
        """Get verified contracts from Etherscan API v2"""
        url = f"{self.base_url}?chainid={self.chain_id}&module=contract&action=getverifiedcontracts"
        params = {
            "page": page,
            "offset": offset,
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get("status") == "1":
                return data.get("result", [])
            else:
                print(f"API Error: {data.get('message', 'Unknown error')}")
                return []
        except Exception as e:
            print(f"Request error: {e}")
            return []
    
    def get_contract_abi(self, address: str) -> Dict:
        """Get contract ABI from Etherscan"""
        url = f"{self.base_url}?chainid={self.chain_id}&module=contract&action=getabi"
        params = {
            "address": address,
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get("status") == "1":
                return json.loads(data.get("result", "[]"))
            return []
        except:
            return []
    
    def get_recent_token_transfers(self, address: str) -> List[str]:
        """Get tokens that have been transferred by this contract"""
        url = f"{self.base_url}?chainid={self.chain_id}&module=account&action=tokentx"
        params = {
            "address": address,
            "page": 1,
            "offset": 50,
            "sort": "desc",
            "apikey": self.api_key
        }
        
        tokens = set()
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get("status") == "1":
                for tx in data.get("result", []):
                    tokens.add(tx.get("contractAddress", ""))
            
            return list(tokens)
        except:
            return []
    
    def analyze_contract_for_vulnerabilities(self, address: str, abi: List[Dict]) -> Dict:
        """Analyze contract ABI for vulnerable patterns"""
        result = {
            "address": address,
            "vulnerable_functions": [],
            "has_withdraw": False,
            "has_skim": False,
            "has_harvest": False,
            "is_token": False,
            "is_pair": False,
            "tokens": []
        }
        
        # Check functions
        for item in abi:
            if item.get("type") == "function":
                name = item.get("name", "").lower()
                
                # Check for vulnerable functions
                if "withdraw" in name:
                    result["vulnerable_functions"].append(name)
                    result["has_withdraw"] = True
                elif "skim" in name:
                    result["vulnerable_functions"].append(name)
                    result["has_skim"] = True
                elif "harvest" in name:
                    result["vulnerable_functions"].append(name)
                    result["has_harvest"] = True
                elif name in ["claim", "sweep", "rescue"]:
                    result["vulnerable_functions"].append(name)
                
                # Check if it's a token
                if name in ["transfer", "transferfrom", "balanceof", "totalsupply"]:
                    result["is_token"] = True
                
                # Check if it's a pair
                if name in ["getreserves", "swap", "mint", "burn"]:
                    result["is_pair"] = True
        
        # Get associated tokens
        if result["vulnerable_functions"] and not result["is_token"]:
            result["tokens"] = self.get_recent_token_transfers(address)
        
        return result
    
    def find_pair_for_token(self, token: str) -> Optional[str]:
        """Find liquidity pair for a token"""
        try:
            # Call PancakeSwap factory
            pair = subprocess.check_output([
                "cast", "call", self.pancake_factory,
                "getPair(address,address)(address)",
                self.wbnb, token,
                "--rpc-url", self.public_rpc
            ]).decode().strip()
            
            if pair != "0x0000000000000000000000000000000000000000":
                return pair
            return None
        except:
            return None

class ItyFuzzExecutor:
    """Execute ItyFuzz on contracts"""
    
    def __init__(self):
        self.ityfuzz_path = "./target/debug/cli"
        self.public_rpc = "https://bsc-dataseed.binance.org/"
        
    def build_fuzz_command(self, contract: str, tokens: List[str], 
                          block: int, timeout: int = 60) -> List[str]:
        """Build ItyFuzz command"""
        cmd = [
            self.ityfuzz_path,
            "-t", contract,
            "-c", "BSC",
            "--onchain-block-number", str(block),
            "-f", "-i", "-p",
            "--run-forever", str(timeout)
        ]
        
        # Add WBNB
        cmd.extend(["-t", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"])
        
        # Add tokens
        for token in tokens[:5]:  # Limit to 5 tokens
            if token and token != "0x0000000000000000000000000000000000000000":
                cmd.extend(["-t", token])
        
        return cmd
    
    def fuzz_contract(self, contract_info: Dict, block: int, timeout: int = 60) -> Dict:
        """Fuzz a single contract"""
        result = {
            "address": contract_info["address"],
            "vulnerable_functions": contract_info["vulnerable_functions"],
            "status": "pending",
            "profit": 0,
            "output": ""
        }
        
        # Build command
        cmd = self.build_fuzz_command(
            contract_info["address"],
            contract_info["tokens"],
            block,
            timeout
        )
        
        # Set environment
        env = os.environ.copy()
        env["ETH_RPC_URL"] = self.public_rpc
        env["RUST_LOG"] = "info"
        
        print(f"\n🔍 Fuzzing {contract_info['address']}...")
        print(f"   Functions: {', '.join(contract_info['vulnerable_functions'])}")
        print(f"   Tokens: {len(contract_info['tokens'])}")
        
        try:
            # Run fuzzer
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Wait with timeout
            stdout, stderr = process.communicate(timeout=timeout + 10)
            output = stdout.decode() + stderr.decode()
            
            # Parse results
            if "Anyone can earn" in output:
                profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', output)
                if profit_match:
                    result["profit"] = float(profit_match.group(1))
                    result["status"] = "VULNERABLE"
                    
                    # Save full output
                    filename = f"vuln_{contract_info['address']}_{int(time.time())}.log"
                    with open(filename, "w") as f:
                        f.write(output)
                    result["log_file"] = filename
                else:
                    result["status"] = "clean"
            else:
                result["status"] = "clean"
            
            # Save output snippet
            result["output"] = output[-1000:]  # Last 1000 chars
            
        except subprocess.TimeoutExpired:
            process.kill()
            result["status"] = "timeout"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
        
        return result

def main():
    """Main execution"""
    print("=== BSC Auto Fuzzer with Etherscan API v2 ===\n")
    
    # Initialize
    finder = BSCContractFinder()
    fuzzer = ItyFuzzExecutor()
    
    # Get current block
    current_block = int(subprocess.check_output([
        "cast", "block-number", "--rpc-url", finder.public_rpc
    ]).decode().strip())
    
    print(f"Current BSC block: {current_block}")
    
    # Get contracts to analyze
    print("\n📋 Fetching verified contracts...")
    contracts_to_analyze = []
    
    # Fetch recent verified contracts
    for page in range(1, 3):  # First 2 pages
        contracts = finder.get_verified_contracts(page=page, offset=100)
        print(f"  Page {page}: {len(contracts)} contracts")
        
        for contract in contracts:
            # Get ABI
            address = contract.get("Address", "")
            if address:
                abi = finder.get_contract_abi(address)
                
                # Analyze
                analysis = finder.analyze_contract_for_vulnerabilities(address, abi)
                
                # Add if potentially vulnerable
                if analysis["vulnerable_functions"]:
                    contracts_to_analyze.append(analysis)
                    print(f"  ✓ {address}: {', '.join(analysis['vulnerable_functions'])}")
        
        time.sleep(0.2)  # Rate limit
    
    print(f"\n📊 Found {len(contracts_to_analyze)} contracts with vulnerable functions")
    
    # Fuzz contracts
    print("\n🚀 Starting fuzzing process...")
    vulnerabilities_found = []
    
    for i, contract_info in enumerate(contracts_to_analyze[:20]):  # Limit to 20
        print(f"\n[{i+1}/{min(20, len(contracts_to_analyze))}] Processing {contract_info['address']}")
        
        # Fuzz with 1 minute timeout
        result = fuzzer.fuzz_contract(contract_info, current_block - 1, timeout=60)
        
        if result["status"] == "VULNERABLE":
            vulnerabilities_found.append(result)
            print(f"  🚨 VULNERABLE! Profit: {result['profit']} ETH")
            print(f"  📄 Log saved to: {result['log_file']}")
        elif result["status"] == "clean":
            print(f"  ✅ Clean")
        elif result["status"] == "timeout":
            print(f"  ⏱️  Timeout")
        else:
            print(f"  ❌ Error: {result.get('error', 'Unknown')}")
    
    # Generate report
    report = {
        "scan_time": datetime.now().isoformat(),
        "block_number": current_block,
        "contracts_analyzed": len(contracts_to_analyze),
        "contracts_fuzzed": min(20, len(contracts_to_analyze)),
        "vulnerabilities_found": len(vulnerabilities_found),
        "results": vulnerabilities_found
    }
    
    # Save report
    report_file = f"bsc_fuzz_report_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 Summary:")
    print(f"  Contracts analyzed: {len(contracts_to_analyze)}")
    print(f"  Contracts fuzzed: {min(20, len(contracts_to_analyze))}")
    print(f"  Vulnerabilities found: {len(vulnerabilities_found)}")
    print(f"  Report saved to: {report_file}")
    
    # Print vulnerabilities
    if vulnerabilities_found:
        print(f"\n🚨 Vulnerabilities Found:")
        total_profit = 0
        for vuln in vulnerabilities_found:
            print(f"  {vuln['address']}: {vuln['profit']} ETH")
            total_profit += vuln['profit']
        print(f"  Total potential profit: {total_profit} ETH")

if __name__ == "__main__":
    main()