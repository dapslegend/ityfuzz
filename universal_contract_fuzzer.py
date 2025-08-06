#!/usr/bin/env python3
"""
Universal Contract Fuzzer - Find ALL contracts and let ItyFuzz detect vulnerabilities
"""

import subprocess
import json
import time
import os
import re
import requests
from typing import List, Dict, Set, Tuple
from datetime import datetime
import concurrent.futures

class UniversalContractFuzzer:
    """Find and fuzz ALL contracts - let ItyFuzz do the vulnerability detection"""
    
    def __init__(self):
        # RPC endpoints
        self.historical_rpc = "http://159.198.35.169:8545"
        self.public_rpc = "https://bsc-dataseed.binance.org/"
        
        # Etherscan API v2
        self.api_key = "6J26IP7U4YSMEUFVWQWJJRMIT2XNBY2VPU"
        self.base_url = "https://api.etherscan.io/v2/api"
        self.chain_id = "56"
        
        # ItyFuzz path
        self.ityfuzz_path = "./target/debug/cli"
        
        # Common tokens to always include
        self.common_tokens = [
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # BUSD
            "0x55d398326f99059fF775485246999027B3197955",  # USDT
            "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",  # USDC
            "0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3",  # DAI
        ]
    
    def get_recent_contracts_etherscan(self, limit: int = 100) -> List[str]:
        """Get recently verified contracts from Etherscan"""
        contracts = []
        
        for page in range(1, 3):  # Get 2 pages
            url = f"{self.base_url}?chainid={self.chain_id}&module=contract&action=getverifiedcontracts"
            params = {
                "page": page,
                "offset": 50,
                "apikey": self.api_key,
                "sort": "desc"  # Most recent first
            }
            
            try:
                response = requests.get(url, params=params)
                data = response.json()
                
                if data.get("status") == "1":
                    for contract in data.get("result", []):
                        if contract.get("Address"):
                            contracts.append(contract["Address"])
                
                time.sleep(0.2)  # Rate limit
            except:
                pass
        
        return contracts[:limit]
    
    def get_contracts_from_block(self, block_num: int) -> Set[str]:
        """Get all contract addresses from a block"""
        contracts = set()
        
        try:
            # Get block
            cmd = ["cast", "block", str(block_num), "--json", "--rpc-url", self.historical_rpc]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                block_data = json.loads(result.stdout)
                
                # Check each transaction
                for tx_hash in block_data.get("transactions", [])[:20]:  # Limit per block
                    try:
                        # Get transaction
                        tx_cmd = ["cast", "tx", tx_hash, "--json", "--rpc-url", self.historical_rpc]
                        tx_result = subprocess.run(tx_cmd, capture_output=True, text=True)
                        
                        if tx_result.returncode == 0:
                            tx_data = json.loads(tx_result.stdout)
                            
                            # Add 'to' address if it's a contract
                            to_addr = tx_data.get("to")
                            if to_addr and self.is_contract(to_addr):
                                contracts.add(to_addr)
                            
                            # Check for contract creation
                            if not to_addr:
                                receipt_cmd = ["cast", "receipt", tx_hash, "--json", "--rpc-url", self.historical_rpc]
                                receipt_result = subprocess.run(receipt_cmd, capture_output=True, text=True)
                                
                                if receipt_result.returncode == 0:
                                    receipt = json.loads(receipt_result.stdout)
                                    if receipt.get("contractAddress"):
                                        contracts.add(receipt["contractAddress"])
                    except:
                        pass
                        
        except:
            pass
        
        return contracts
    
    def is_contract(self, address: str) -> bool:
        """Check if address is a contract"""
        try:
            code = subprocess.check_output([
                "cast", "code", address, "--rpc-url", self.historical_rpc
            ]).decode().strip()
            
            return len(code) > 10  # Has bytecode
        except:
            return False
    
    def find_contract_tokens(self, address: str) -> List[str]:
        """Find tokens associated with a contract"""
        tokens = []
        
        # Method 1: Check storage slots for token addresses
        for slot in range(20):  # Check first 20 slots
            try:
                value = subprocess.check_output([
                    "cast", "storage", address, str(slot),
                    "--rpc-url", self.historical_rpc
                ]).decode().strip()
                
                # Check if it looks like an address
                if len(value) == 66 and "0x00000000000000000000" in value:
                    potential_addr = "0x" + value[-40:]
                    
                    # Quick check if it's a token (has symbol)
                    try:
                        symbol = subprocess.check_output([
                            "cast", "call", potential_addr, "symbol()(string)",
                            "--rpc-url", self.historical_rpc
                        ], timeout=2).decode().strip()
                        
                        if symbol and len(symbol) < 50:  # Valid symbol
                            tokens.append(potential_addr)
                    except:
                        pass
                        
            except:
                pass
        
        # Method 2: Try Etherscan token transfers
        url = f"{self.base_url}?chainid={self.chain_id}&module=account&action=tokentx"
        params = {
            "address": address,
            "page": 1,
            "offset": 20,
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            data = response.json()
            
            if data.get("status") == "1":
                for tx in data.get("result", []):
                    token = tx.get("contractAddress")
                    if token and token not in tokens:
                        tokens.append(token)
        except:
            pass
        
        return tokens[:5]  # Limit to 5 tokens
    
    def fuzz_contract(self, address: str, tokens: List[str], block: int) -> Dict:
        """Fuzz a single contract with ItyFuzz"""
        result = {
            "address": address,
            "status": "pending",
            "profit": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Build ItyFuzz command
        cmd = [
            self.ityfuzz_path,
            "-t", address,
            "-c", "BSC",
            "--onchain-block-number", str(block),
            "-f", "-i", "-p",
            "--run-forever", "60"  # 1 minute timeout
        ]
        
        # Add common tokens
        for token in self.common_tokens:
            cmd.extend(["-t", token])
        
        # Add contract-specific tokens
        for token in tokens:
            if token not in self.common_tokens:
                cmd.extend(["-t", token])
        
        # Set environment
        env = os.environ.copy()
        env["ETH_RPC_URL"] = self.public_rpc
        env["RUST_LOG"] = "info"
        
        print(f"\n🎯 Fuzzing {address}")
        print(f"   Tokens: {len(self.common_tokens) + len(tokens)}")
        
        try:
            # Run fuzzer
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Wait with timeout
            stdout, stderr = process.communicate(timeout=70)
            output = stdout.decode() + stderr.decode()
            
            # Check for vulnerabilities
            if "Anyone can earn" in output:
                profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', output)
                if profit_match:
                    result["profit"] = float(profit_match.group(1))
                    result["status"] = "VULNERABLE"
                    
                    # Save full log
                    log_file = f"vuln_{address}_{int(time.time())}.log"
                    with open(log_file, "w") as f:
                        f.write(output)
                    result["log_file"] = log_file
                    
                    print(f"   🚨 VULNERABLE! Profit: {result['profit']} ETH")
                    print(f"   📄 Log: {log_file}")
                else:
                    result["status"] = "found_issue"
                    print(f"   ⚠️  Found issue but couldn't parse profit")
            else:
                result["status"] = "clean"
                print(f"   ✅ Clean")
                
        except subprocess.TimeoutExpired:
            process.kill()
            result["status"] = "timeout"
            print(f"   ⏱️  Timeout")
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"   ❌ Error: {e}")
        
        return result

def main():
    """Main execution"""
    print("=== Universal Contract Fuzzer ===")
    print("Finding ALL contracts and letting ItyFuzz detect vulnerabilities\n")
    
    fuzzer = UniversalContractFuzzer()
    
    # Get current blocks
    hist_block = int(subprocess.check_output([
        "cast", "block-number", "--rpc-url", fuzzer.historical_rpc
    ]).decode().strip())
    
    pub_block = int(subprocess.check_output([
        "cast", "block-number", "--rpc-url", fuzzer.public_rpc
    ]).decode().strip())
    
    print(f"Historical RPC: Block {hist_block}")
    print(f"Public RPC: Block {pub_block}")
    print(f"Will fuzz at block: {pub_block - 1}\n")
    
    # Collect contracts from multiple sources
    all_contracts = set()
    
    # Source 1: Recent blocks from historical RPC
    print("📡 Source 1: Scanning recent blocks...")
    block_range = range(hist_block - 50, hist_block + 1)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fuzzer.get_contracts_from_block, block): block 
                  for block in block_range}
        
        for future in concurrent.futures.as_completed(futures):
            contracts = future.result()
            if contracts:
                all_contracts.update(contracts)
                print(f"  Found {len(contracts)} contracts in block {futures[future]}")
    
    print(f"  Total from blocks: {len(all_contracts)} contracts")
    
    # Source 2: Etherscan verified contracts
    print("\n📡 Source 2: Getting verified contracts from Etherscan...")
    etherscan_contracts = fuzzer.get_recent_contracts_etherscan(100)
    print(f"  Found {len(etherscan_contracts)} verified contracts")
    all_contracts.update(etherscan_contracts)
    
    print(f"\n📊 Total unique contracts found: {len(all_contracts)}")
    
    # Find tokens for each contract
    print("\n🔍 Analyzing contracts and finding associated tokens...")
    contracts_with_tokens = []
    
    for i, address in enumerate(list(all_contracts)[:50]):  # Limit to 50
        print(f"  [{i+1}/50] {address}", end="")
        tokens = fuzzer.find_contract_tokens(address)
        contracts_with_tokens.append({
            "address": address,
            "tokens": tokens
        })
        print(f" - {len(tokens)} tokens found")
    
    # Start fuzzing
    print(f"\n🚀 Starting fuzzing campaign on {len(contracts_with_tokens)} contracts...")
    print("Each contract will be fuzzed for 1 minute\n")
    
    vulnerabilities = []
    start_time = time.time()
    
    for i, contract_info in enumerate(contracts_with_tokens[:20]):  # Limit to 20 for demo
        print(f"[{i+1}/20] Contract {i+1} of 20")
        
        result = fuzzer.fuzz_contract(
            contract_info["address"],
            contract_info["tokens"],
            pub_block - 1
        )
        
        if result["status"] == "VULNERABLE":
            vulnerabilities.append(result)
    
    # Generate report
    elapsed = time.time() - start_time
    report = {
        "scan_time": datetime.now().isoformat(),
        "duration_seconds": elapsed,
        "blocks": {
            "historical_latest": hist_block,
            "public_latest": pub_block,
            "fuzzing_block": pub_block - 1
        },
        "contracts": {
            "total_found": len(all_contracts),
            "analyzed": len(contracts_with_tokens),
            "fuzzed": min(20, len(contracts_with_tokens))
        },
        "vulnerabilities_found": len(vulnerabilities),
        "total_profit_eth": sum(v["profit"] for v in vulnerabilities),
        "results": vulnerabilities
    }
    
    # Save report
    report_file = f"universal_fuzz_report_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 FUZZING COMPLETE")
    print(f"{'='*60}")
    print(f"Duration: {elapsed/60:.1f} minutes")
    print(f"Contracts found: {len(all_contracts)}")
    print(f"Contracts analyzed: {len(contracts_with_tokens)}")
    print(f"Contracts fuzzed: {min(20, len(contracts_with_tokens))}")
    print(f"Vulnerabilities found: {len(vulnerabilities)}")
    
    if vulnerabilities:
        print(f"\n💰 Total potential profit: {report['total_profit_eth']:.4f} ETH")
        print(f"\n🚨 Vulnerable contracts:")
        for vuln in vulnerabilities:
            print(f"  {vuln['address']}: {vuln['profit']:.4f} ETH")
            print(f"    Log: {vuln['log_file']}")
    
    print(f"\n📄 Full report saved to: {report_file}")
    print("\n✅ ItyFuzz has completed vulnerability detection!")

if __name__ == "__main__":
    main()