#!/usr/bin/env python3
"""
MEV Tiger Scanner - Works exactly like run_tiger_mode.sh
"""

import subprocess
import os
import time
import json
from datetime import datetime
from typing import List, Dict, Tuple
import concurrent.futures

class MEVTigerScanner:
    def __init__(self):
        self.api_key = "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
        self.rpc_url = "https://rpc.ankr.com/bsc"
        self.ityfuzz_path = "./target/debug/ityfuzz"
        
        # Create MEV directories
        os.makedirs("mev/work_dirs", exist_ok=True)
        os.makedirs("mev/vulnerability_logs", exist_ok=True)
        os.makedirs("mev/fuzzing_logs", exist_ok=True)
        os.makedirs("mev/logs", exist_ok=True)
        
        # Tiger mode detectors (run separately)
        self.detectors = [
            "erc20",
            "reentrancy", 
            "erc20,reentrancy",
            "arbitrary_call",
            "typed_bug",
            "erc20,balance_drain",
            "all"
        ]
        
        # Known vulnerable contracts from tiger script
        self.test_configs = [
            ("BEGO", "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972", 22315679),
            ("BBOX", "0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c", 23106506),
            ("FAPEN", "0xf3f1abae8bfeca054b330c379794a7bf84988228,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0xf3F1aBae8BfeCA054B330C379794A7bf84988228", 28637846),
            ("SEAMAN", "0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e", 23467515)
        ]
        
    def tiger_hunt(self, name: str, targets: str, block: int, detector: str) -> Dict:
        """Run ityfuzz exactly like tiger mode"""
        
        # Create work directory
        detector_safe = detector.replace(",", "_")
        work_dir = f"mev/work_dirs/{name}_{detector_safe}_{int(time.time())}"
        os.makedirs(work_dir, exist_ok=True)
        
        # Prepare command - EXACTLY like tiger script
        cmd = [
            "timeout", "60",  # 60 second timeout (15 was too short)
            self.ityfuzz_path, "evm",
            "-t", targets,  # Pass all targets as single comma-separated string
            "-c", "bsc",
            "--onchain-block-number", str(block),
            "-f",
            "--panic-on-bug",
            "--onchain-etherscan-api-key", self.api_key,
            "--onchain-url", self.rpc_url,
            "--detectors", detector,
            "--work-dir", work_dir
        ]
        
        # Set environment exactly like tiger
        env = os.environ.copy()
        env["RUST_LOG"] = "error"
        env["RAYON_NUM_THREADS"] = "32"
        
        # Execute
        log_file = f"{work_dir}/fuzzing.log"
        print(f"🐅 {name} [{detector}]: ", end="", flush=True)
        
        with open(log_file, "w") as log:
            result = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
        
        # Check for vulnerabilities
        found = False
        profit = None
        
        with open(log_file, "r") as log:
            content = log.read()
            if "Found vulnerabilities" in content or "Anyone can earn" in content:
                found = True
                # Extract profit
                import re
                profit_match = re.search(r"([0-9]+\.[0-9]+) ETH", content)
                if profit_match:
                    profit = profit_match.group(1)
                
                # Save to vulnerability logs
                vuln_log = f"mev/vulnerability_logs/{name}_{detector_safe}_{int(time.time())}.log"
                with open(vuln_log, "w") as vlog:
                    vlog.write(content)
        
        if found:
            print(f"✅ CAUGHT! {profit} ETH" if profit else "✅ CAUGHT!")
        else:
            print("❌ missed")
            # Clean up work dir if no vulnerability
            subprocess.run(["rm", "-rf", work_dir], capture_output=True)
        
        return {
            "name": name,
            "detector": detector,
            "found": found,
            "profit": profit,
            "log_file": log_file if found else None
        }
    
    def scan_current_contracts(self):
        """Also scan current block contracts"""
        # Get current block
        try:
            result = subprocess.run([
                "cast", "block", "--rpc-url", self.rpc_url, "latest"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('number'):
                        current_block = int(line.split()[1])
                        print(f"\n📊 Current BSC block: {current_block}")
                        
                        # Add some current contracts to test
                        self.test_configs.extend([
                            ("CAKE_CURRENT", "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", current_block),
                            ("PANCAKE_CURRENT", "0x10ED43C718714eb63d5aA57B78B54704E256024E,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56", current_block),
                        ])
                        break
        except:
            pass
    
    def run_all_tests(self):
        """Run all tests like tiger mode"""
        print("🐅 TIGER MODE - MEV Scanner 🐅")
        print("=" * 40)
        print("")
        print("Tiger settings:")
        print("  🔥 60 second timeouts")
        print("  🔥 Each detector runs separately")
        print("  🔥 Maximum parallelism")
        print("")
        
        # Add current block contracts
        self.scan_current_contracts()
        
        print("🐅 TIGER HUNT BEGINS!")
        print("")
        
        all_results = []
        
        # Process each test configuration
        for name, targets, block in self.test_configs:
            print("━" * 40)
            print(f"🎯 Hunting: {name} at block {block}")
            
            # Run all detectors in parallel for this target
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.detectors)) as executor:
                futures = []
                for detector in self.detectors:
                    future = executor.submit(self.tiger_hunt, name, targets, block, detector)
                    futures.append(future)
                
                # Collect results
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    all_results.append(result)
            
            print("")
        
        # Summary
        print("━" * 40)
        print("🐅 TIGER HUNT COMPLETE!")
        print("")
        
        # Count kills
        kills = sum(1 for r in all_results if r["found"])
        print(f"🏆 Total kills: {kills}")
        print("")
        
        # Show successful hunts
        print("Successful hunts:")
        for result in all_results:
            if result["found"]:
                profit_str = f": {result['profit']} ETH" if result["profit"] else ""
                print(f"  ✅ {result['name']} [{result['detector']}]{profit_str}")
        
        # Save summary
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(all_results),
            "vulnerabilities_found": kills,
            "results": all_results
        }
        
        summary_file = f"mev/logs/tiger_summary_{int(time.time())}.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📝 Summary saved to: {summary_file}")
        print("\n🐅 The tiger is satisfied! 🐅")

def main():
    scanner = MEVTigerScanner()
    
    # Check if ityfuzz exists
    if not os.path.exists(scanner.ityfuzz_path):
        print(f"❌ Error: {scanner.ityfuzz_path} not found!")
        return
    
    scanner.run_all_tests()

if __name__ == "__main__":
    main()