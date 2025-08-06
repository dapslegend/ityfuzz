#!/usr/bin/env python3
"""
Fuzz contracts from recent transactions using JSON output
"""

import subprocess
import json
import time
import os
from datetime import datetime
import re

class RecentTxFuzzer:
    def __init__(self):
        self.rpc_url = "https://bsc-dataseed.binance.org/"
        self.api_key = "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
        self.ityfuzz_path = "./target/debug/ityfuzz"
        
        # Create directories
        os.makedirs("mev/recent_tx", exist_ok=True)
        os.makedirs("mev/recent_tx/logs", exist_ok=True)
        os.makedirs("mev/recent_tx/vulnerabilities", exist_ok=True)
        
        # Common tokens
        self.common_tokens = [
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # BUSD
        ]
        
        # Detectors
        self.detectors = ["erc20", "all"]
        
    def get_current_block(self):
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
            print(f"Error: {e}")
        return None
    
    def get_block_contracts(self, block_number):
        """Get contract addresses from a block"""
        contracts = set()
        
        try:
            # Get block with transactions in JSON format
            result = subprocess.run([
                "cast", "block", str(block_number), 
                "--rpc-url", self.rpc_url,
                "--json"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                block_data = json.loads(result.stdout)
                
                # Process each transaction
                transactions = block_data.get("transactions", [])[:20]  # Limit to 20 txs
                for tx in transactions:
                    # If transactions are hashes (strings), fetch full tx
                    if isinstance(tx, str):
                        tx_result = subprocess.run([
                            "cast", "tx", tx,
                            "--rpc-url", self.rpc_url,
                            "--json"
                        ], capture_output=True, text=True, timeout=5)
                        
                        if tx_result.returncode == 0:
                            try:
                                tx = json.loads(tx_result.stdout)
                            except json.JSONDecodeError:
                                continue
                    
                    # Now tx is a dictionary
                    if isinstance(tx, dict):
                        # Check 'to' address
                        to_addr = tx.get("to")
                        if to_addr and to_addr != "0x0000000000000000000000000000000000000000":
                            contracts.add(to_addr.lower())
                        
                        # Check for contract creation (when 'to' is null)
                        if not to_addr or to_addr == "0x0000000000000000000000000000000000000000":
                            # This might be a contract creation
                            # We'd need to get the receipt to find the contract address
                            pass
        
        except Exception as e:
            print(f"Error processing block {block_number}: {e}")
        
        return list(contracts)
    
    def is_contract(self, address):
        """Check if address is a contract"""
        try:
            result = subprocess.run([
                "cast", "code", address,
                "--rpc-url", self.rpc_url
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                code = result.stdout.strip()
                return len(code) > 2  # More than just "0x"
        except:
            pass
        return False
    
    def fuzz_contract(self, address, block):
        """Fuzz a single contract"""
        print(f"\n🔍 Fuzzing {address} at block {block}")
        
        results = {
            "address": address,
            "block": block,
            "vulnerabilities": []
        }
        
        # Build targets
        targets = ",".join([address] + self.common_tokens)
        
        for detector in self.detectors:
            print(f"   Testing with {detector} detector...")
            
            work_dir = f"mev/recent_tx/work_{address[:8]}_{detector}_{block}"
            os.makedirs(work_dir, exist_ok=True)
            
            cmd = [
                "timeout", "30",
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
            
            log_file = f"mev/recent_tx/logs/{address[:8]}_{detector}_{block}.log"
            with open(log_file, "w") as log:
                subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
            
            # Check for vulnerabilities
            with open(log_file, "r") as log:
                content = log.read()
                if "Anyone can earn" in content:
                    profit_match = re.search(r"([0-9]+\.[0-9]+) ETH", content)
                    profit = profit_match.group(1) if profit_match else "unknown"
                    
                    print(f"      ✅ VULNERABILITY FOUND! {profit} ETH")
                    
                    vuln_file = f"mev/recent_tx/vulnerabilities/{address[:8]}_{detector}_{int(time.time())}.log"
                    with open(vuln_file, "w") as vf:
                        vf.write(content)
                    
                    results["vulnerabilities"].append({
                        "detector": detector,
                        "profit": profit
                    })
            
            # Clean up if no vulnerability
            if not any(v["detector"] == detector for v in results["vulnerabilities"]):
                subprocess.run(["rm", "-rf", work_dir], capture_output=True)
        
        return results
    
    def run(self):
        """Main fuzzing loop"""
        print("🚀 Starting Recent Transaction Fuzzer")
        print(f"   RPC: {self.rpc_url}")
        print("")
        
        current_block = self.get_current_block()
        if not current_block:
            print("❌ Failed to get current block")
            return
        
        print(f"📊 Current BSC block: {current_block}")
        
        all_results = []
        contracts_found = 0
        
        # Scan last 5 blocks
        for i in range(5):
            block = current_block - i
            print(f"\n📦 Scanning block {block}...")
            
            # Get contracts from block
            potential_contracts = self.get_block_contracts(block)
            print(f"   Found {len(potential_contracts)} potential contracts")
            
            # Verify and fuzz contracts
            for addr in potential_contracts[:5]:  # Limit to 5 per block
                if self.is_contract(addr):
                    print(f"   ✅ Verified contract: {addr}")
                    contracts_found += 1
                    
                    result = self.fuzz_contract(addr, block)
                    all_results.append(result)
                    
                    if contracts_found >= 10:  # Stop after 10 contracts
                        break
            
            if contracts_found >= 10:
                break
        
        # Summary
        print("\n" + "="*50)
        print("📊 FUZZING COMPLETE")
        print(f"   Contracts scanned: {len(all_results)}")
        
        vuln_count = sum(len(r["vulnerabilities"]) for r in all_results)
        print(f"   Vulnerabilities found: {vuln_count}")
        
        if vuln_count > 0:
            print("\n🎯 Vulnerable contracts:")
            for result in all_results:
                if result["vulnerabilities"]:
                    print(f"   - {result['address']}")
                    for vuln in result["vulnerabilities"]:
                        print(f"     • {vuln['detector']}: {vuln['profit']} ETH")
        
        # Save results
        results_file = f"mev/recent_tx/results_{int(time.time())}.json"
        with open(results_file, "w") as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\n📝 Results saved to: {results_file}")

def main():
    fuzzer = RecentTxFuzzer()
    
    if not os.path.exists(fuzzer.ityfuzz_path):
        print(f"❌ Error: {fuzzer.ityfuzz_path} not found!")
        return
    
    fuzzer.run()

if __name__ == "__main__":
    main()