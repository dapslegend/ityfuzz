#!/usr/bin/env python3
"""
Fuzz recent on-chain transactions to find vulnerabilities
"""

import subprocess
import json
import time
import os
from datetime import datetime
from typing import List, Dict, Set
import concurrent.futures

class OnchainTxFuzzer:
    def __init__(self):
        self.rpc_url = "https://bsc-dataseed.binance.org/"
        self.api_key = "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
        self.ityfuzz_path = "./target/debug/ityfuzz"
        
        # Create directories
        os.makedirs("mev/onchain_tx", exist_ok=True)
        os.makedirs("mev/onchain_tx/logs", exist_ok=True)
        os.makedirs("mev/onchain_tx/vulnerabilities", exist_ok=True)
        
        # Common tokens to include
        self.common_tokens = [
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # BUSD
            "0x55d398326f99059fF775485246999027B3197955",  # USDT
        ]
        
        # Detectors to use
        self.detectors = ["erc20", "reentrancy", "arbitrary_call", "typed_bug", "all"]
        
    def get_current_block(self) -> int:
        """Get current block number"""
        try:
            result = subprocess.run([
                "cast", "block", "--rpc-url", self.rpc_url, "latest"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('number'):
                        return int(line.split()[1])
        except Exception as e:
            print(f"Error getting block: {e}")
        return None
    
    def get_block_transactions(self, block_number: int) -> List[str]:
        """Get all transactions from a block"""
        try:
            result = subprocess.run([
                "cast", "block", "--rpc-url", self.rpc_url, str(block_number), "--json"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                block_data = json.loads(result.stdout)
                # The transactions might be a list of tx hashes or tx objects
                transactions = block_data.get("transactions", [])
                if transactions and isinstance(transactions[0], dict):
                    # Extract hashes from transaction objects
                    return [tx.get("hash", tx) for tx in transactions]
                return transactions
        except Exception as e:
            print(f"Error getting block transactions: {e}")
        return []
    
    def get_transaction_details(self, tx_hash: str) -> Dict:
        """Get transaction details"""
        try:
            result = subprocess.run([
                "cast", "tx", tx_hash, "--rpc-url", self.rpc_url, "--json"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            print(f"Error getting tx details: {e}")
        return None
    
    def is_contract(self, address: str) -> bool:
        """Check if address is a contract"""
        try:
            result = subprocess.run([
                "cast", "code", address, "--rpc-url", self.rpc_url
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and len(result.stdout.strip()) > 10:
                return True
        except:
            pass
        return False
    
    def extract_unique_contracts(self, tx_details: Dict) -> Set[str]:
        """Extract unique contract addresses from transaction"""
        contracts = set()
        
        # Check 'to' address
        to_addr = tx_details.get("to")
        if to_addr and self.is_contract(to_addr):
            contracts.add(to_addr.lower())
        
        # Check if it's a contract creation
        contract_addr = tx_details.get("contractAddress")
        if contract_addr:
            contracts.add(contract_addr.lower())
        
        # TODO: Could also extract addresses from input data for more thorough analysis
        
        return contracts
    
    def fuzz_contract(self, address: str, block: int, timeout: int = 60) -> Dict:
        """Fuzz a single contract"""
        results = {
            "address": address,
            "block": block,
            "timestamp": datetime.now().isoformat(),
            "vulnerabilities": []
        }
        
        print(f"\n🔍 Fuzzing contract: {address} at block {block}")
        
        for detector in self.detectors:
            print(f"   Testing with {detector} detector...")
            
            # Create work directory
            work_dir = f"mev/onchain_tx/work_{address[:8]}_{detector}_{block}"
            os.makedirs(work_dir, exist_ok=True)
            
            # Combine targets
            targets = ",".join([address] + self.common_tokens)
            
            # Run ityfuzz
            cmd = [
                "timeout", str(timeout),
                self.ityfuzz_path, "evm",
                "-t", targets,
                "-c", "bsc",
                "--onchain-block-number", str(block),
                "-f",
                "--panic-on-bug",
                "--detectors", detector,
                "--work-dir", work_dir,
                "--onchain-etherscan-api-key", self.api_key,
                "--onchain-url", self.rpc_url
            ]
            
            # Execute
            log_file = f"mev/onchain_tx/logs/{address[:8]}_{detector}_{block}.log"
            with open(log_file, "w") as log:
                result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
            
            # Check for vulnerabilities
            with open(log_file, "r") as log:
                content = log.read()
                if "Anyone can earn" in content:
                    # Extract profit
                    import re
                    profit_match = re.search(r"([0-9]+\.[0-9]+) ETH", content)
                    profit = profit_match.group(1) if profit_match else "unknown"
                    
                    print(f"      ✅ VULNERABILITY FOUND! {profit} ETH")
                    
                    # Save vulnerability
                    vuln_file = f"mev/onchain_tx/vulnerabilities/{address[:8]}_{detector}_{int(time.time())}.log"
                    with open(vuln_file, "w") as vf:
                        vf.write(content)
                    
                    results["vulnerabilities"].append({
                        "detector": detector,
                        "profit": profit,
                        "log_file": vuln_file
                    })
            
            # Clean up work dir if no vulnerability
            if not any(v["detector"] == detector for v in results["vulnerabilities"]):
                subprocess.run(["rm", "-rf", work_dir], capture_output=True)
        
        return results
    
    def scan_recent_blocks(self, num_blocks: int = 5, max_tx_per_block: int = 20):
        """Scan recent blocks for contracts to fuzz"""
        current_block = self.get_current_block()
        if not current_block:
            print("❌ Failed to get current block")
            return
        
        print(f"📊 Current BSC block: {current_block}")
        print(f"🔍 Scanning last {num_blocks} blocks for contracts...")
        
        all_contracts = set()
        
        for i in range(num_blocks):
            block = current_block - i
            print(f"\n📦 Scanning block {block}...")
            
            # Get transactions
            tx_hashes = self.get_block_transactions(block)
            print(f"   Found {len(tx_hashes)} transactions")
            
            # Process limited number of transactions
            contracts_in_block = set()
            for tx_hash in tx_hashes[:max_tx_per_block]:
                tx_details = self.get_transaction_details(tx_hash)
                if tx_details:
                    contracts = self.extract_unique_contracts(tx_details)
                    contracts_in_block.update(contracts)
            
            print(f"   Found {len(contracts_in_block)} unique contracts")
            all_contracts.update(contracts_in_block)
        
        return all_contracts, current_block
    
    def run_fuzzing_session(self, duration_minutes: int = 10):
        """Run a fuzzing session"""
        print(f"\n🚀 Starting On-chain Transaction Fuzzer")
        print(f"   Duration: {duration_minutes} minutes")
        print(f"   RPC: {self.rpc_url}")
        print("")
        
        start_time = time.time()
        max_duration = duration_minutes * 60
        
        session_log = f"mev/onchain_tx/session_{int(start_time)}.json"
        all_results = []
        
        while time.time() - start_time < max_duration:
            elapsed = int(time.time() - start_time)
            remaining = max_duration - elapsed
            
            print(f"\n⏱️  Time: {elapsed}s / {max_duration}s (remaining: {remaining}s)")
            
            # Scan recent blocks
            contracts, current_block = self.scan_recent_blocks(num_blocks=3, max_tx_per_block=10)
            
            if not contracts:
                print("❌ No contracts found in recent blocks")
                time.sleep(30)  # Wait before next scan
                continue
            
            print(f"\n🎯 Found {len(contracts)} unique contracts to fuzz")
            
            # Fuzz each contract
            for contract in list(contracts)[:5]:  # Limit to 5 contracts per round
                if time.time() - start_time >= max_duration:
                    break
                
                result = self.fuzz_contract(contract, current_block, timeout=30)
                all_results.append(result)
                
                if result["vulnerabilities"]:
                    print(f"\n🎉 Found {len(result['vulnerabilities'])} vulnerabilities in {contract}!")
            
            # Save session results
            with open(session_log, "w") as f:
                json.dump({
                    "start_time": start_time,
                    "duration": elapsed,
                    "results": all_results
                }, f, indent=2)
            
            # Wait before next round
            if time.time() - start_time < max_duration:
                print("\n💤 Waiting 60 seconds before next scan...")
                time.sleep(60)
        
        # Final summary
        print("\n" + "="*50)
        print("📊 FUZZING SESSION COMPLETE")
        print(f"   Duration: {duration_minutes} minutes")
        print(f"   Contracts scanned: {len(all_results)}")
        
        vuln_count = sum(len(r["vulnerabilities"]) for r in all_results)
        print(f"   Vulnerabilities found: {vuln_count}")
        
        if vuln_count > 0:
            print("\n🎯 Vulnerable contracts:")
            for result in all_results:
                if result["vulnerabilities"]:
                    print(f"   - {result['address']}: {len(result['vulnerabilities'])} vulnerabilities")
                    for vuln in result["vulnerabilities"]:
                        print(f"     • {vuln['detector']}: {vuln['profit']} ETH")
        
        print(f"\n📝 Full results saved to: {session_log}")

def main():
    fuzzer = OnchainTxFuzzer()
    
    # Check if ityfuzz exists
    if not os.path.exists(fuzzer.ityfuzz_path):
        print(f"❌ Error: {fuzzer.ityfuzz_path} not found!")
        print("   Please build ityfuzz first")
        return
    
    # Run fuzzing session for 10 minutes
    fuzzer.run_fuzzing_session(duration_minutes=10)

if __name__ == "__main__":
    main()