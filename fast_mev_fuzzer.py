#!/usr/bin/env python3
"""
Fast MEV Fuzzer - Optimized for speed
"""

import subprocess
import json
import time
import os
from datetime import datetime
from typing import List, Dict

class FastMEVFuzzer:
    def __init__(self):
        # Use debug build
        self.ityfuzz_path = "./target/debug/ityfuzz"
        
        # Create MEV directories
        os.makedirs("mev/work_dirs", exist_ok=True)
        os.makedirs("mev/vulnerability_logs", exist_ok=True)
        os.makedirs("mev/fuzzing_logs", exist_ok=True)
        os.makedirs("mev/logs", exist_ok=True)
        
        # Common BSC tokens - just use the essentials
        self.tokens = [
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # BUSD
            "0x55d398326f99059fF775485246999027B3197955",  # USDT
        ]
        
        # Known vulnerable contracts for testing
        self.test_contracts = [
            # BEGO with its specific tokens
            ("BEGO", "0x68Cc90351a79A4c10078FE021bE430b7a12aaA09", 22315679,
             ["0x88503F48e437a377f1aC2892cBB3a5b09949faDd", "0xc342774492b54ce5F8ac662113ED702Fc1b34972"]),
            ("CAKE", "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", "latest", []),
            ("PancakeRouter", "0x10ED43C718714eb63d5aA57B78B54704E256024E", "latest", []),
        ]
    
    def get_current_block(self) -> int:
        """Get current BSC block"""
        try:
            result = subprocess.check_output([
                "cast", "block-number", 
                "--rpc-url", "https://bsc-dataseed.binance.org/"
            ]).decode().strip()
            return int(result)
        except:
            return 56627000  # Fallback
    
    def fuzz_contract(self, name: str, address: str, block, detector: str, extra_tokens: List[str] = []) -> Dict:
        """Fuzz a single contract with one detector"""
        
        # Handle block number
        if block == "latest":
            block_num = self.get_current_block()
        else:
            block_num = int(block)
        
        print(f"\n🎯 Fuzzing {name} ({address[:10]}...) with {detector}")
        print(f"   Block: {block_num}")
        
        # Prepare work directory
        work_dir = f"mev/work_dirs/{name}_{detector}_{block_num}_{int(time.time())}"
        os.makedirs(work_dir, exist_ok=True)
        
        # Build target string - include extra tokens if provided
        all_tokens = self.tokens + extra_tokens
        targets = ",".join([address] + all_tokens)
        
        # Build command
        cmd = [
            self.ityfuzz_path, "evm",
            "-t", targets,
            "-c", "bsc",
            "--onchain-block-number", str(block_num),
            "-f",
            "--panic-on-bug",
            "--detectors", detector,
            "--work-dir", work_dir,
            "--onchain-etherscan-api-key", "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP",
            "--onchain-url", "https://bsc-dataseed.binance.org/"
        ]
        
        # Set environment
        env = os.environ.copy()
        env["RUST_LOG"] = "error"
        env["RAYON_NUM_THREADS"] = "32"
        
        # Run with timeout
        start_time = time.time()
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            # Wait for completion (30 seconds max)
            stdout, stderr = process.communicate(timeout=30)
            output = stdout.decode() + stderr.decode()
            
            # Save output
            log_file = f"mev/logs/{name}_{detector}_{int(time.time())}.log"
            with open(log_file, "w") as f:
                f.write(output)
            
            # Check for vulnerability
            if "Anyone can earn" in output or "Found vulnerabilities" in output:
                print(f"   🚨 VULNERABILITY FOUND!")
                
                # Extract profit
                import re
                profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', output)
                profit = float(profit_match.group(1)) if profit_match else 0
                
                # Save vulnerability log
                vuln_log = f"mev/vulnerability_logs/{name}_{detector}_{int(time.time())}.log"
                with open(vuln_log, "w") as f:
                    f.write(output)
                
                return {
                    "status": "VULNERABLE",
                    "name": name,
                    "address": address,
                    "detector": detector,
                    "profit": profit,
                    "work_dir": work_dir,
                    "log_file": vuln_log,
                    "duration": time.time() - start_time
                }
            else:
                print(f"   ✅ Clean")
                return {
                    "status": "clean",
                    "name": name,
                    "address": address,
                    "detector": detector,
                    "duration": time.time() - start_time
                }
                
        except subprocess.TimeoutExpired:
            process.kill()
            print(f"   ⏱️  Timeout")
            return {
                "status": "timeout",
                "name": name,
                "address": address,
                "detector": detector,
                "duration": 30
            }
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {
                "status": "error",
                "name": name,
                "address": address,
                "detector": detector,
                "error": str(e),
                "duration": time.time() - start_time
            }

def main():
    print("=== Fast MEV Fuzzer ===")
    print("Optimized for speed - minimal token discovery\n")
    
    fuzzer = FastMEVFuzzer()
    
    # Detectors to test (most effective first)
    detectors = ["erc20", "reentrancy", "arbitrary_call"]
    
    vulnerabilities = []
    start_time = time.time()
    
    # Test known contracts
    for name, address, block, extra_tokens in fuzzer.test_contracts:
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"{'='*60}")
        
        for detector in detectors:
            result = fuzzer.fuzz_contract(name, address, block, detector, extra_tokens)
            
            if result["status"] == "VULNERABLE":
                vulnerabilities.append(result)
                print(f"\n💰 Found vulnerability! Breaking detector loop for {name}")
                break  # Move to next contract
    
    # Generate report
    duration = time.time() - start_time
    report = {
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": duration,
        "contracts_tested": len(fuzzer.test_contracts),
        "detectors_used": detectors,
        "vulnerabilities_found": len(vulnerabilities),
        "total_profit_eth": sum(v.get("profit", 0) for v in vulnerabilities),
        "results": vulnerabilities
    }
    
    # Save report
    report_file = f"mev/fuzzing_logs/fast_mev_report_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 FUZZING COMPLETE")
    print(f"{'='*60}")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Contracts tested: {len(fuzzer.test_contracts)}")
    print(f"Vulnerabilities found: {len(vulnerabilities)}")
    
    if vulnerabilities:
        print(f"\n💰 Total potential profit: {report['total_profit_eth']:.4f} ETH")
        print(f"\n🚨 Vulnerable contracts:")
        for vuln in vulnerabilities:
            print(f"  {vuln['name']} ({vuln['address'][:10]}...)")
            print(f"    Detector: {vuln['detector']}")
            print(f"    Profit: {vuln.get('profit', 0):.4f} ETH")
            print(f"    Work dir: {vuln['work_dir']}")
    
    print(f"\n📄 Report saved to: {report_file}")
    print("✅ All data saved in mev/ directory for exploitation!")

if __name__ == "__main__":
    main()