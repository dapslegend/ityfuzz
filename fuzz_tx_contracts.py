#!/usr/bin/env python3
"""
Extract contracts from recent transactions and fuzz them
"""

import subprocess
import json
import time
import os
from datetime import datetime
import re
from typing import List, Dict, Set

class TxContractFuzzer:
    def __init__(self):
        self.rpc_url = "https://bsc-dataseed.binance.org/"
        self.api_key = "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
        self.ityfuzz_path = "./target/debug/ityfuzz"
        
        # Create directories
        os.makedirs("mev/tx_contracts", exist_ok=True)
        os.makedirs("mev/tx_contracts/logs", exist_ok=True)
        os.makedirs("mev/tx_contracts/vulnerabilities", exist_ok=True)
        
        # Common tokens to include when fuzzing
        self.common_tokens = [
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # BUSD
            "0x55d398326f99059fF775485246999027B3197955",  # USDT
        ]
        
        # Detectors to use
        self.detectors = ["erc20", "reentrancy", "all"]
        
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
    
    def get_block_info(self, block_number: int) -> Dict:
        """Get block information including transactions"""
        try:
            # Get block with transaction details
            result = subprocess.run([
                "cast", "block", str(block_number), 
                "--rpc-url", self.rpc_url,
                "--full"  # Get full transaction objects
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse the output to extract transaction information
                contracts = set()
                lines = result.stdout.split('\n')
                
                for i, line in enumerate(lines):
                    # Look for "to" addresses
                    if line.strip().startswith('to:'):
                        address = line.split(':', 1)[1].strip()
                        if address and address != '0x0000000000000000000000000000000000000000':
                            contracts.add(address.lower())
                    
                    # Look for contract creation
                    if line.strip().startswith('contractAddress:'):
                        address = line.split(':', 1)[1].strip()
                        if address and address != 'null':
                            contracts.add(address.lower())
                
                return {"contracts": list(contracts), "tx_count": len(lines)}
        except Exception as e:
            print(f"Error getting block info: {e}")
        
        return {"contracts": [], "tx_count": 0}
    
    def is_contract(self, address: str) -> bool:
        """Check if address has code (is a contract)"""
        try:
            result = subprocess.run([
                "cast", "code", address, 
                "--rpc-url", self.rpc_url
            ], capture_output=True, text=True, timeout=5)
            
            # If it has code longer than "0x", it's a contract
            if result.returncode == 0:
                code = result.stdout.strip()
                return len(code) > 2
        except:
            pass
        return False
    
    def get_recent_contracts(self, num_blocks: int = 5) -> List[Dict]:
        """Get contracts from recent blocks"""
        current_block = self.get_current_block()
        if not current_block:
            return []
        
        print(f"📊 Current BSC block: {current_block}")
        print(f"🔍 Scanning last {num_blocks} blocks for contracts...")
        
        all_contracts = []
        
        for i in range(num_blocks):
            block = current_block - i
            print(f"\n📦 Checking block {block}...")
            
            block_info = self.get_block_info(block)
            print(f"   Found {len(block_info['contracts'])} potential contracts")
            
            # Verify each address is actually a contract
            verified_contracts = []
            for addr in block_info['contracts'][:10]:  # Limit to 10 per block
                if self.is_contract(addr):
                    verified_contracts.append({
                        "address": addr,
                        "block": block,
                        "found_at": datetime.now().isoformat()
                    })
                    print(f"   ✅ Verified contract: {addr}")
            
            all_contracts.extend(verified_contracts)
            
            if len(all_contracts) >= 10:  # Stop after finding 10 contracts
                break
        
        return all_contracts
    
    def fuzz_contract(self, contract_info: Dict, timeout: int = 30) -> Dict:
        """Fuzz a single contract"""
        address = contract_info["address"]
        block = contract_info["block"]
        
        results = {
            "address": address,
            "block": block,
            "timestamp": datetime.now().isoformat(),
            "vulnerabilities": []
        }
        
        print(f"\n🔍 Fuzzing contract: {address} at block {block}")
        
        # Build targets: contract + common tokens
        targets = [address] + self.common_tokens
        targets_str = ",".join(targets)
        
        for detector in self.detectors:
            print(f"   Testing with {detector} detector...")
            
            # Create work directory
            work_dir = f"mev/tx_contracts/work_{address[:8]}_{detector}_{block}"
            os.makedirs(work_dir, exist_ok=True)
            
            # Run ityfuzz
            cmd = [
                "timeout", str(timeout),
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
            log_file = f"mev/tx_contracts/logs/{address[:8]}_{detector}_{block}.log"
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
                    vuln_file = f"mev/tx_contracts/vulnerabilities/{address[:8]}_{detector}_{int(time.time())}.log"
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
    
    def run_continuous_fuzzing(self, duration_minutes: int = 10):
        """Run continuous fuzzing of contracts from recent transactions"""
        print("🚀 Starting Transaction Contract Fuzzer")
        print(f"   Duration: {duration_minutes} minutes")
        print(f"   RPC: {self.rpc_url}")
        print("")
        
        start_time = time.time()
        max_duration = duration_minutes * 60
        
        session_log = f"mev/tx_contracts/session_{int(start_time)}.json"
        all_results = []
        
        round_num = 0
        while time.time() - start_time < max_duration:
            round_num += 1
            elapsed = int(time.time() - start_time)
            remaining = max_duration - elapsed
            
            print(f"\n{'='*50}")
            print(f"⏱️  Round {round_num} - Time: {elapsed}s / {max_duration}s (remaining: {remaining}s)")
            
            # Get contracts from recent transactions
            contracts = self.get_recent_contracts(num_blocks=3)
            
            if not contracts:
                print("❌ No contracts found in recent blocks")
                time.sleep(30)
                continue
            
            print(f"\n🎯 Found {len(contracts)} contracts to fuzz")
            
            # Fuzz each contract
            for contract_info in contracts[:3]:  # Limit to 3 per round
                if time.time() - start_time >= max_duration:
                    break
                
                result = self.fuzz_contract(contract_info, timeout=30)
                all_results.append(result)
                
                if result["vulnerabilities"]:
                    print(f"\n🎉 Found {len(result['vulnerabilities'])} vulnerabilities in {contract_info['address']}!")
            
            # Save session results
            with open(session_log, "w") as f:
                json.dump({
                    "start_time": start_time,
                    "duration": elapsed,
                    "rounds": round_num,
                    "results": all_results
                }, f, indent=2)
            
            # Wait before next round
            if time.time() - start_time < max_duration:
                wait_time = min(60, max_duration - elapsed)
                print(f"\n💤 Waiting {wait_time} seconds before next round...")
                time.sleep(wait_time)
        
        # Final summary
        print("\n" + "="*50)
        print("📊 FUZZING SESSION COMPLETE")
        print(f"   Duration: {duration_minutes} minutes")
        print(f"   Rounds: {round_num}")
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
    fuzzer = TxContractFuzzer()
    
    # Check if ityfuzz exists
    if not os.path.exists(fuzzer.ityfuzz_path):
        print(f"❌ Error: {fuzzer.ityfuzz_path} not found!")
        return
    
    # Run continuous fuzzing for 10 minutes
    fuzzer.run_continuous_fuzzing(duration_minutes=10)

if __name__ == "__main__":
    main()