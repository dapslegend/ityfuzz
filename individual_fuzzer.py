#!/usr/bin/env python3
"""
Individual Contract Fuzzer - Runs each contract in isolation
"""

import subprocess
import json
import time
import os
import shutil
from datetime import datetime
from typing import List, Dict, Tuple

class IndividualFuzzer:
    def __init__(self):
        self.ityfuzz_path = "./target/debug/ityfuzz"
        
        # Create MEV directories
        os.makedirs("mev/work_dirs", exist_ok=True)
        os.makedirs("mev/vulnerability_logs", exist_ok=True)
        os.makedirs("mev/fuzzing_logs", exist_ok=True)
        os.makedirs("mev/logs", exist_ok=True)
        
        # RPC endpoints
        self.rpc_url = "https://bsc-dataseed.binance.org/"
        self.api_key = "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
    
    def get_current_block(self) -> int:
        """Get current BSC block"""
        try:
            result = subprocess.check_output([
                "cast", "block-number", 
                "--rpc-url", self.rpc_url
            ], stderr=subprocess.DEVNULL).decode().strip()
            return int(result)
        except:
            return 56627000
    
    def get_recent_contracts(self, block_count: int = 10) -> List[Tuple[str, int]]:
        """Find contracts from recent blocks"""
        contracts = []
        current_block = self.get_current_block()
        
        print(f"📡 Scanning last {block_count} blocks (from {current_block})")
        
        for block_num in range(current_block - block_count, current_block):
            try:
                # Get block data
                result = subprocess.check_output([
                    "cast", "block", str(block_num), "--json",
                    "--rpc-url", self.rpc_url
                ], stderr=subprocess.DEVNULL, timeout=5)
                
                block_data = json.loads(result.decode())
                
                # Check transactions
                for tx_hash in block_data.get("transactions", [])[:20]:  # Limit per block
                    try:
                        # Get transaction details
                        tx_result = subprocess.check_output([
                            "cast", "tx", tx_hash, "--json",
                            "--rpc-url", self.rpc_url
                        ], stderr=subprocess.DEVNULL, timeout=2)
                        
                        tx_data = json.loads(tx_result.decode())
                        
                        # Check if it's a contract creation
                        if tx_data.get("creates"):
                            contract_addr = tx_data["creates"]
                            contracts.append((contract_addr, block_num))
                            print(f"  Found new contract: {contract_addr[:10]}...")
                        
                        # Also check if 'to' is a contract
                        to_addr = tx_data.get("to")
                        if to_addr and to_addr != "0x0000000000000000000000000000000000000000":
                            # Quick check if it has code
                            try:
                                code_result = subprocess.check_output([
                                    "cast", "code", to_addr,
                                    "--rpc-url", self.rpc_url
                                ], stderr=subprocess.DEVNULL, timeout=1)
                                
                                if code_result.decode().strip() != "0x":
                                    contracts.append((to_addr, block_num))
                                    
                            except:
                                pass
                                
                    except:
                        continue
                        
            except Exception as e:
                continue
        
        # Deduplicate
        unique_contracts = list(set(contracts))
        print(f"✅ Found {len(unique_contracts)} unique contracts")
        return unique_contracts
    
    def run_single_contract(self, address: str, block: int, detector: str = "all") -> Dict:
        """Run ityfuzz on a single contract"""
        
        print(f"\n🎯 Fuzzing {address[:10]}... at block {block} with {detector}")
        
        # Create work directory
        work_dir = f"mev/work_dirs/{address}_{detector}_{block}_{int(time.time())}"
        os.makedirs(work_dir, exist_ok=True)
        
        # Build command - ONLY the contract address
        cmd = [
            self.ityfuzz_path, "evm",
            "-t", address,
            "-c", "bsc",
            "--onchain-block-number", str(block),
            "-f",
            "--panic-on-bug",
            "--detectors", detector,
            "--work-dir", work_dir,
            "--onchain-etherscan-api-key", self.api_key,
            "--onchain-url", self.rpc_url
        ]
        
        # Environment
        env = os.environ.copy()
        env["RUST_LOG"] = "info"
        env["RAYON_NUM_THREADS"] = "8"
        
        # Run with timeout
        start_time = time.time()
        result = {
            "address": address,
            "block": block,
            "detector": detector,
            "work_dir": work_dir,
            "start_time": datetime.now().isoformat()
        }
        
        try:
            # Create a temporary script to run the command
            script_path = f"/tmp/fuzz_{address}_{detector}.sh"
            with open(script_path, "w") as f:
                f.write("#!/bin/bash\n")
                f.write("set -e\n")
                f.write(f"cd {os.getcwd()}\n")
                f.write(" ".join(cmd) + "\n")
            
            os.chmod(script_path, 0o755)
            
            # Run the script
            process = subprocess.Popen(
                [script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Wait with timeout
            stdout, stderr = process.communicate(timeout=60)
            output = stdout.decode() + stderr.decode()
            
            # Save log
            log_file = f"mev/logs/{address}_{detector}_{int(time.time())}.log"
            with open(log_file, "w") as f:
                f.write(output)
            
            # Clean up script
            os.remove(script_path)
            
            # Check for vulnerabilities
            if "Anyone can earn" in output or "Found vulnerabilities" in output:
                print(f"   🚨 VULNERABILITY FOUND!")
                
                # Extract profit
                import re
                profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', output)
                profit = float(profit_match.group(1)) if profit_match else 0
                
                # Save vulnerability log
                vuln_log = f"mev/vulnerability_logs/{address}_{detector}_{int(time.time())}.log"
                with open(vuln_log, "w") as f:
                    f.write(output)
                
                # Save metadata
                metadata_file = os.path.join(work_dir, "vulnerability_metadata.json")
                metadata = {
                    "address": address,
                    "block": block,
                    "detector": detector,
                    "profit": profit,
                    "timestamp": datetime.now().isoformat(),
                    "log_file": vuln_log
                }
                with open(metadata_file, "w") as f:
                    json.dump(metadata, f, indent=2)
                
                result.update({
                    "status": "VULNERABLE",
                    "profit": profit,
                    "log_file": vuln_log,
                    "duration": time.time() - start_time
                })
                
            else:
                print(f"   ✅ Clean")
                # Remove work dir if clean
                shutil.rmtree(work_dir, ignore_errors=True)
                result.update({
                    "status": "clean",
                    "duration": time.time() - start_time
                })
            
        except subprocess.TimeoutExpired:
            process.kill()
            print(f"   ⏱️ Timeout")
            result.update({
                "status": "timeout",
                "duration": 60
            })
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            result.update({
                "status": "error",
                "error": str(e),
                "duration": time.time() - start_time
            })
        
        return result

def main():
    print("=== Individual Contract Fuzzer ===")
    print("Running each contract in isolation to avoid ABI conflicts\n")
    
    fuzzer = IndividualFuzzer()
    
    # Test with known vulnerable contract first
    print("🧪 Testing known vulnerable contract...")
    bego_result = fuzzer.run_single_contract(
        "0x68Cc90351a79A4c10078FE021bE430b7a12aaA09",
        22315679,
        "erc20"
    )
    
    if bego_result["status"] == "VULNERABLE":
        print("✅ BEGO vulnerability confirmed!")
    
    # Now scan recent contracts
    print("\n📡 Scanning recent contracts...")
    recent_contracts = fuzzer.get_recent_contracts(block_count=5)
    
    # Run fuzzing
    vulnerabilities = []
    detectors = ["erc20", "reentrancy", "arbitrary_call"]
    max_contracts = 10
    
    start_time = time.time()
    
    for i, (address, block) in enumerate(recent_contracts[:max_contracts]):
        print(f"\n{'='*60}")
        print(f"Contract {i+1}/{min(len(recent_contracts), max_contracts)}: {address}")
        print(f"{'='*60}")
        
        # Try each detector
        for detector in detectors:
            result = fuzzer.run_single_contract(address, block, detector)
            
            if result["status"] == "VULNERABLE":
                vulnerabilities.append(result)
                break  # Skip other detectors for this contract
            
            # Small delay between runs
            time.sleep(0.5)
    
    # Generate report
    duration = time.time() - start_time
    report = {
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": duration,
        "contracts_tested": min(len(recent_contracts), max_contracts),
        "detectors_used": detectors,
        "vulnerabilities_found": len(vulnerabilities),
        "total_profit_eth": sum(v.get("profit", 0) for v in vulnerabilities),
        "results": vulnerabilities
    }
    
    # Save report
    report_file = f"mev/fuzzing_logs/individual_fuzz_report_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 FUZZING COMPLETE")
    print(f"{'='*60}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Contracts tested: {report['contracts_tested']}")
    print(f"Vulnerabilities found: {len(vulnerabilities)}")
    
    if vulnerabilities:
        print(f"\n💰 Total potential profit: {report['total_profit_eth']:.4f} ETH")
        print(f"\n🚨 Vulnerable contracts:")
        for vuln in vulnerabilities:
            print(f"  {vuln['address'][:10]}...")
            print(f"    Block: {vuln['block']}")
            print(f"    Detector: {vuln['detector']}")
            print(f"    Profit: {vuln.get('profit', 0):.4f} ETH")
            print(f"    Work dir: {vuln['work_dir']}")
    
    print(f"\n📄 Report saved to: {report_file}")
    print("✅ All data saved in mev/ directory!")

if __name__ == "__main__":
    main()