#!/usr/bin/env python3
"""
Fuzz known contracts at current block
"""

import subprocess
import os
import time
import json
from datetime import datetime
import re

class KnownContractFuzzer:
    def __init__(self):
        self.rpc_url = "https://bsc-dataseed.binance.org/"
        self.api_key = "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
        self.ityfuzz_path = "./target/debug/ityfuzz"
        
        # Create directories
        os.makedirs("mev/known_contracts", exist_ok=True)
        os.makedirs("mev/known_contracts/logs", exist_ok=True)
        os.makedirs("mev/known_contracts/vulnerabilities", exist_ok=True)
        
        # Known vulnerable contracts from backtest (for testing)
        self.test_contracts = [
            {
                "name": "BEGO",
                "address": "0x68Cc90351a79A4c10078FE021bE430b7a12aaA09",
                "tokens": ["0x88503F48e437a377f1aC2892cBB3a5b09949faDd", "0xc342774492b54ce5F8ac662113ED702Fc1b34972"],
                "block": 22315679  # Historical block where vulnerability exists
            }
        ]
        
        # Popular BSC contracts to fuzz at current block
        self.popular_contracts = [
            {
                "name": "PancakeSwap Router",
                "address": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
                "tokens": ["0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"]
            },
            {
                "name": "Venus vBNB",
                "address": "0xA07c5b74C9B40447a954e1466938b865b6BBea36",
                "tokens": ["0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"]
            },
            {
                "name": "CAKE Token",
                "address": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
                "tokens": ["0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"]
            },
            {
                "name": "Alpaca Finance",
                "address": "0x8F0528cE5eF7B51152A59745bEfDD91D97091d2F",
                "tokens": ["0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"]
            },
            {
                "name": "Belt Finance",
                "address": "0xe0e514c71282b6f4e823703a39374Cf58dc3eA4f",
                "tokens": ["0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"]
            }
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
    
    def fuzz_contract(self, contract_info: dict, block: int = None) -> dict:
        """Fuzz a single contract"""
        # Use provided block or contract's historical block
        if block is None:
            block = contract_info.get("block", self.get_current_block())
        
        results = {
            "name": contract_info["name"],
            "address": contract_info["address"],
            "block": block,
            "timestamp": datetime.now().isoformat(),
            "vulnerabilities": []
        }
        
        print(f"\n🔍 Fuzzing {contract_info['name']} ({contract_info['address']}) at block {block}")
        
        # Build target list: contract + associated tokens
        targets = [contract_info["address"]] + contract_info.get("tokens", [])
        targets_str = ",".join(targets)
        
        for detector in self.detectors:
            print(f"   Testing with {detector} detector...")
            
            # Create work directory
            work_dir = f"mev/known_contracts/work_{contract_info['name'].replace(' ', '_')}_{detector}_{block}"
            os.makedirs(work_dir, exist_ok=True)
            
            # Run ityfuzz
            cmd = [
                "timeout", "60",  # 60 second timeout
                self.ityfuzz_path, "evm",
                "-t", targets_str,
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
            log_file = f"mev/known_contracts/logs/{contract_info['name'].replace(' ', '_')}_{detector}_{block}.log"
            with open(log_file, "w") as log:
                result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
            
            # Check for vulnerabilities
            with open(log_file, "r") as log:
                content = log.read()
                if "Anyone can earn" in content:
                    # Extract profit
                    profit_match = re.search(r"([0-9]+\.[0-9]+) ETH", content)
                    profit = profit_match.group(1) if profit_match else "unknown"
                    
                    print(f"      ✅ VULNERABILITY FOUND! {profit} ETH")
                    
                    # Save vulnerability
                    vuln_file = f"mev/known_contracts/vulnerabilities/{contract_info['name'].replace(' ', '_')}_{detector}_{int(time.time())}.log"
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
    
    def run_fuzzing_session(self):
        """Run fuzzing session on known contracts"""
        print("🚀 Starting Known Contract Fuzzer")
        print(f"   RPC: {self.rpc_url}")
        print("")
        
        current_block = self.get_current_block()
        print(f"📊 Current BSC block: {current_block}")
        
        session_log = f"mev/known_contracts/session_{int(time.time())}.json"
        all_results = []
        
        # First test known vulnerable contracts at their historical blocks
        print("\n🧪 Testing known vulnerable contracts at historical blocks...")
        for contract in self.test_contracts:
            result = self.fuzz_contract(contract)
            all_results.append(result)
        
        # Then test popular contracts at current block
        print("\n🎯 Testing popular contracts at current block...")
        for contract in self.popular_contracts:
            result = self.fuzz_contract(contract, block=current_block)
            all_results.append(result)
        
        # Summary
        print("\n" + "="*50)
        print("📊 FUZZING SESSION COMPLETE")
        print(f"   Contracts scanned: {len(all_results)}")
        
        vuln_count = sum(len(r["vulnerabilities"]) for r in all_results)
        print(f"   Vulnerabilities found: {vuln_count}")
        
        if vuln_count > 0:
            print("\n🎯 Vulnerable contracts:")
            for result in all_results:
                if result["vulnerabilities"]:
                    print(f"   - {result['name']} ({result['address']}): {len(result['vulnerabilities'])} vulnerabilities")
                    for vuln in result["vulnerabilities"]:
                        print(f"     • {vuln['detector']}: {vuln['profit']} ETH")
        
        # Save results
        with open(session_log, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "current_block": current_block,
                "results": all_results
            }, f, indent=2)
        
        print(f"\n📝 Full results saved to: {session_log}")

def main():
    fuzzer = KnownContractFuzzer()
    
    # Check if ityfuzz exists
    if not os.path.exists(fuzzer.ityfuzz_path):
        print(f"❌ Error: {fuzzer.ityfuzz_path} not found!")
        print("   Please build ityfuzz first")
        return
    
    fuzzer.run_fuzzing_session()

if __name__ == "__main__":
    main()