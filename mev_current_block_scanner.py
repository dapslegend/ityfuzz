#!/usr/bin/env python3
"""
MEV Scanner - Scans current blocks for contracts and fuzzes them
"""

import subprocess
import json
import time
import os
from datetime import datetime
from typing import List, Dict, Set

class MEVCurrentBlockScanner:
    def __init__(self):
        self.rpc_url = "https://bsc-dataseed.binance.org/"
        self.api_key = "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
        self.ityfuzz_path = "./target/debug/ityfuzz"
        
        # Create MEV directories
        os.makedirs("mev/work_dirs", exist_ok=True)
        os.makedirs("mev/vulnerability_logs", exist_ok=True)
        os.makedirs("mev/fuzzing_logs", exist_ok=True)
        os.makedirs("mev/logs", exist_ok=True)
        
        # Common tokens
        self.common_tokens = [
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # BUSD
            "0x55d398326f99059fF775485246999027B3197955",  # USDT
        ]
        
        # Detectors to use
        self.detectors = ["erc20", "reentrancy", "arbitrary_call", "typed_bug", "balance_drain"]
        
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
    
    def get_contracts_from_block(self, block_number: int) -> Set[str]:
        """Extract contract addresses from a block"""
        contracts = set()
        
        try:
            # Get block data
            result = subprocess.run([
                "cast", "block", "--rpc-url", self.rpc_url, str(block_number), "--json"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                block_data = json.loads(result.stdout)
                
                # Process transactions
                for tx_hash in block_data.get("transactions", [])[:20]:  # Limit to 20 txs
                    # Get transaction details
                    tx_result = subprocess.run([
                        "cast", "tx", tx_hash, "--rpc-url", self.rpc_url, "--json"
                    ], capture_output=True, text=True, timeout=5)
                    
                    if tx_result.returncode == 0:
                        tx_data = json.loads(tx_result.stdout)
                        
                        # Check if it's a contract creation
                        if tx_data.get("to") is None and tx_data.get("contractAddress"):
                            contracts.add(tx_data["contractAddress"].lower())
                        
                        # Also check 'to' address if it's a contract
                        to_addr = tx_data.get("to")
                        if to_addr:
                            # Check if it's a contract by getting code
                            code_result = subprocess.run([
                                "cast", "code", to_addr, "--rpc-url", self.rpc_url
                            ], capture_output=True, text=True, timeout=5)
                            
                            if code_result.returncode == 0 and len(code_result.stdout.strip()) > 10:
                                contracts.add(to_addr.lower())
                                
        except Exception as e:
            print(f"Error processing block {block_number}: {e}")
            
        return contracts
    
    def scan_recent_blocks(self, num_blocks: int = 10) -> Set[str]:
        """Scan recent blocks for contracts"""
        current_block = self.get_current_block()
        if not current_block:
            return set()
        
        print(f"📊 Scanning last {num_blocks} blocks from {current_block}")
        
        all_contracts = set()
        for i in range(num_blocks):
            block = current_block - i
            contracts = self.get_contracts_from_block(block)
            if contracts:
                print(f"   Block {block}: Found {len(contracts)} contracts")
                all_contracts.update(contracts)
        
        return all_contracts
    
    def fuzz_contract(self, address: str, block: int) -> Dict:
        """Fuzz a contract with all detectors"""
        results = {
            "address": address,
            "block": block,
            "timestamp": datetime.now().isoformat(),
            "vulnerabilities": []
        }
        
        for detector in self.detectors:
            print(f"      Testing with {detector} detector...")
            
            # Create work directory
            work_dir = f"mev/work_dirs/{address}_{detector}_{block}_{int(time.time())}"
            os.makedirs(work_dir, exist_ok=True)
            
            # Combine targets
            targets = ",".join([address] + self.common_tokens)
            
            # Run ityfuzz
            cmd = [
                "timeout", "60",  # 1 minute timeout per detector
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
            
            # Run with environment
            env = os.environ.copy()
            env["RUST_LOG"] = "error"
            env["RAYON_NUM_THREADS"] = "8"
            
            # Execute
            log_file = f"{work_dir}/fuzzing.log"
            with open(log_file, "w") as log:
                subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
            
            # Check for vulnerabilities
            with open(log_file, "r") as log:
                content = log.read()
                if "Anyone can earn" in content:
                    print(f"         ✅ VULNERABILITY FOUND with {detector}!")
                    
                    # Save vulnerability log
                    vuln_log = f"mev/vulnerability_logs/{address}_{detector}_{int(time.time())}.log"
                    with open(vuln_log, "w") as vlog:
                        vlog.write(content)
                    
                    results["vulnerabilities"].append({
                        "detector": detector,
                        "log_file": vuln_log
                    })
            
            # Clean up work dir if no vulnerability
            if not any(v["detector"] == detector for v in results["vulnerabilities"]):
                # Remove work dir to save space
                subprocess.run(["rm", "-rf", work_dir], capture_output=True)
        
        return results
    
    def run_continuous_scan(self, duration_minutes: int = 20):
        """Run continuous scanning for specified duration"""
        start_time = time.time()
        max_duration = duration_minutes * 60
        
        session_log = f"mev/logs/session_{int(start_time)}.log"
        
        print(f"\n🚀 Starting MEV Scanner")
        print(f"   Duration: {duration_minutes} minutes")
        print(f"   Session log: {session_log}")
        
        contracts_scanned = set()
        vulnerabilities_found = 0
        
        with open(session_log, "w") as log:
            log.write(f"MEV Scanner Session - {datetime.now()}\n")
            log.write(f"Duration: {duration_minutes} minutes\n\n")
            
            while time.time() - start_time < max_duration:
                current_block = self.get_current_block()
                print(f"\n⏱️  Time elapsed: {int(time.time() - start_time)}s / {max_duration}s")
                print(f"📊 Current block: {current_block}")
                
                # Scan recent blocks
                contracts = self.scan_recent_blocks(5)  # Scan last 5 blocks
                
                # Filter out already scanned
                new_contracts = contracts - contracts_scanned
                
                if new_contracts:
                    print(f"🔍 Found {len(new_contracts)} new contracts to scan")
                    
                    for contract in list(new_contracts)[:3]:  # Limit to 3 per round
                        print(f"\n   📌 Fuzzing {contract}")
                        
                        result = self.fuzz_contract(contract, current_block)
                        contracts_scanned.add(contract)
                        
                        # Log results
                        log.write(f"\nContract: {contract}\n")
                        log.write(f"Block: {current_block}\n")
                        log.write(f"Vulnerabilities: {len(result['vulnerabilities'])}\n")
                        
                        if result["vulnerabilities"]:
                            vulnerabilities_found += len(result["vulnerabilities"])
                            print(f"      🚨 Found {len(result['vulnerabilities'])} vulnerabilities!")
                            
                            # Save detailed report
                            report_file = f"mev/fuzzing_logs/{contract}_report_{int(time.time())}.json"
                            with open(report_file, "w") as report:
                                json.dump(result, report, indent=2)
                else:
                    print("   No new contracts found, waiting...")
                    time.sleep(30)  # Wait 30 seconds before next scan
            
            # Final summary
            log.write(f"\n\nSession Summary:\n")
            log.write(f"Contracts scanned: {len(contracts_scanned)}\n")
            log.write(f"Vulnerabilities found: {vulnerabilities_found}\n")
            log.write(f"End time: {datetime.now()}\n")
        
        print(f"\n✅ Scan complete!")
        print(f"   Contracts scanned: {len(contracts_scanned)}")
        print(f"   Vulnerabilities found: {vulnerabilities_found}")
        print(f"   Logs saved in: mev/")

def main():
    scanner = MEVCurrentBlockScanner()
    
    # Check if ityfuzz exists
    if not os.path.exists(scanner.ityfuzz_path):
        print(f"❌ Error: {scanner.ityfuzz_path} not found!")
        return
    
    # Run for 20 minutes
    scanner.run_continuous_scan(20)

if __name__ == "__main__":
    main()