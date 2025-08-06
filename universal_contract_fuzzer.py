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
import shutil

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
        self.ityfuzz_path = "./target/debug/ityfuzz"
        
        # Create directories
        os.makedirs("work_dirs", exist_ok=True)
        os.makedirs("vulnerability_logs", exist_ok=True)
        os.makedirs("fuzzing_logs", exist_ok=True)
        
        # Common tokens to always include
        self.common_tokens = [
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # BUSD
            "0x55d398326f99059fF775485246999027B3197955",  # USDT
            "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",  # USDC
            "0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3",  # DAI
        ]
    
    def get_recent_contracts_etherscan(self, limit: int = 100) -> List[str]:
        """Get recently verified contracts from Etherscan API v2"""
        contracts = []
        
        # Use the correct Etherscan API v2 endpoint structure
        url = "https://api.etherscan.io/v2/api"
        
        # Get recent verified contracts for BSC (chainId 56)
        params = {
            "chainid": "56",
            "module": "contract",
            "action": "listcontracts",
            "page": "1",
            "offset": "100",
            "sort": "desc",
            "apikey": self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get("status") == "1" and data.get("result"):
                for contract in data.get("result", []):
                    if contract.get("ContractAddress"):
                        contracts.append(contract["ContractAddress"])
                    elif contract.get("Address"):
                        contracts.append(contract["Address"])
                    elif contract.get("address"):
                        contracts.append(contract["address"])
            
            # If first attempt doesn't work, try alternative endpoint
            if len(contracts) == 0:
                # Try getting recent transactions and extract contract addresses
                params["action"] = "txlist"
                params["address"] = "0x10ED43C718714eb63d5aA57B78B54704E256024E"  # PancakeSwap Router
                
                response = requests.get(url, params=params)
                data = response.json()
                
                if data.get("status") == "1" and data.get("result"):
                    seen = set()
                    for tx in data.get("result", []):
                        # Get unique contract addresses
                        if tx.get("to") and tx.get("to") not in seen:
                            seen.add(tx["to"])
                            contracts.append(tx["to"])
                        if tx.get("contractAddress") and tx.get("contractAddress") not in seen:
                            seen.add(tx["contractAddress"])
                            contracts.append(tx["contractAddress"])
                
        except Exception as e:
            print(f"  Etherscan API error: {e}")
        
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
            "timestamp": datetime.now().isoformat(),
            "work_dir": None
        }
        
        # Create unique work directory for this contract
        work_dir = f"work_dirs/{address}_{block}_{int(time.time())}"
        os.makedirs(work_dir, exist_ok=True)
        result["work_dir"] = work_dir
        
        # Build ItyFuzz command with work directory
        cmd = [
            self.ityfuzz_path,
            "-t", address,
            "-c", "BSC",
            "--onchain-block-number", str(block),
            "-f", "-i", "-p",
            "--work-dir", work_dir,  # Save corpus and findings here
            "--run-forever"  # Keep fuzzing until timeout
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
        print(f"   Work dir: {work_dir}")
        
        try:
            # Run fuzzer
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Wait with timeout (60 seconds fuzzing + 10 buffer)
            stdout, stderr = process.communicate(timeout=70)
            output = stdout.decode() + stderr.decode()
            
            # Check for vulnerabilities
            if "Anyone can earn" in output:
                profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', output)
                if profit_match:
                    result["profit"] = float(profit_match.group(1))
                    result["status"] = "VULNERABLE"
                    
                    # Save full log
                    log_file = f"vulnerability_logs/vuln_{address}_{int(time.time())}.log"
                    with open(log_file, "w") as f:
                        f.write(output)
                    result["log_file"] = log_file
                    
                    # Also save metadata for MEV
                    metadata = {
                        "address": address,
                        "block": block,
                        "profit": result["profit"],
                        "work_dir": work_dir,
                        "log_file": log_file,
                        "tokens": self.common_tokens + tokens,
                        "timestamp": result["timestamp"]
                    }
                    
                    metadata_file = os.path.join(work_dir, "vulnerability_metadata.json")
                    with open(metadata_file, "w") as f:
                        json.dump(metadata, f, indent=2)
                    
                    print(f"   🚨 VULNERABLE! Profit: {result['profit']} ETH")
                    print(f"   📄 Log: {log_file}")
                    print(f"   📁 Work dir: {work_dir}")
                else:
                    result["status"] = "found_issue"
                    print(f"   ⚠️  Found issue but couldn't parse profit")
            else:
                result["status"] = "clean"
                print(f"   ✅ Clean")
                # Remove work dir if clean to save space
                shutil.rmtree(work_dir, ignore_errors=True)
                result["work_dir"] = None
                
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
    print("Finding ALL contracts and letting ItyFuzz detect vulnerabilities")
    print("Each project saves its work_dir for MEV exploitation\n")
    
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
    # Scan only last 10 blocks but more thoroughly
    block_range = range(hist_block - 10, hist_block + 1)
    
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
    
    # If no contracts found, add some known ones for testing
    if len(all_contracts) == 0:
        print("\n⚠️  No contracts found from scanning. Adding known BSC contracts...")
        # Add some active BSC contracts
        test_contracts = [
            "0x68Cc90351a79A4c10078FE021bE430b7a12aaA09",  # BEGO from previous tests
            "0x88503F48e437a377f1aC2892cBB3a5b09949faDd",  # Another from previous
            "0xc342774492b54ce5F8ac662113ED702Fc1b34972",  # Another from previous
            "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",  # CAKE token
            "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # ETH on BSC
            "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",  # BTCB
            "0xF8A0BF9cF54Bb92F17374d9e9A321E6a111a51bD",  # LINK
            "0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47",  # ADA
        ]
        all_contracts.update(test_contracts)
        print(f"  Added {len(test_contracts)} BSC contracts")
    
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
    
    # Start fuzzing - run for 20 minutes total
    print(f"\n🚀 Starting 20-minute fuzzing campaign...")
    print(f"Will fuzz as many contracts as possible in 20 minutes\n")
    
    vulnerabilities = []
    start_time = time.time()
    max_duration = 20 * 60  # 20 minutes in seconds
    contracts_fuzzed = 0
    
    for i, contract_info in enumerate(contracts_with_tokens):
        # Check if we've exceeded 20 minutes
        elapsed = time.time() - start_time
        if elapsed >= max_duration:
            print(f"\n⏰ 20 minutes reached! Stopping fuzzing.")
            break
        
        remaining = max_duration - elapsed
        print(f"\n[{i+1}] Time remaining: {remaining/60:.1f} minutes")
        
        result = fuzzer.fuzz_contract(
            contract_info["address"],
            contract_info["tokens"],
            pub_block - 1
        )
        
        contracts_fuzzed = i + 1
        
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
            "fuzzed": contracts_fuzzed
        },
        "vulnerabilities_found": len(vulnerabilities),
        "total_profit_eth": sum(v["profit"] for v in vulnerabilities),
        "results": vulnerabilities
    }
    
    # Save report
    report_file = f"fuzzing_logs/universal_fuzz_report_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 FUZZING COMPLETE")
    print(f"{'='*60}")
    print(f"Duration: {elapsed/60:.1f} minutes")
    print(f"Contracts found: {len(all_contracts)}")
    print(f"Contracts analyzed: {len(contracts_with_tokens)}")
    print(f"Contracts fuzzed: {contracts_fuzzed}")
    print(f"Vulnerabilities found: {len(vulnerabilities)}")
    
    if vulnerabilities:
        print(f"\n💰 Total potential profit: {report['total_profit_eth']:.4f} ETH")
        print(f"\n🚨 Vulnerable contracts with work directories:")
        for vuln in vulnerabilities:
            print(f"\n  Contract: {vuln['address']}")
            print(f"  Profit: {vuln['profit']:.4f} ETH")
            print(f"  Work dir: {vuln['work_dir']}")
            print(f"  Log: {vuln.get('log_file', 'N/A')}")
    
    print(f"\n📄 Full report saved to: {report_file}")
    print(f"📁 Work directories saved in: work_dirs/")
    print("\n✅ Work directories preserved for MEV exploitation!")

if __name__ == "__main__":
    main()