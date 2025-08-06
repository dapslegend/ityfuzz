#!/usr/bin/env python3
"""
Proven MEV Scanner - Focus on ERC20 vulnerabilities
"""

import subprocess
import json
import time
import os
import shutil
from datetime import datetime
from typing import List, Dict, Tuple

class ProvenMEVScanner:
    def __init__(self):
        self.ityfuzz_path = "./target/debug/ityfuzz"
        
        # Create MEV directories
        os.makedirs("mev/work_dirs", exist_ok=True)
        os.makedirs("mev/vulnerability_logs", exist_ok=True)
        os.makedirs("mev/fuzzing_logs", exist_ok=True)
        os.makedirs("mev/logs", exist_ok=True)
        
        # Configuration
        self.rpc_url = "https://bsc-dataseed.binance.org/"
        self.api_key = "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
        
        # Known vulnerable pattern tokens
        self.vulnerable_tokens = [
            "0x88503F48e437a377f1aC2892cBB3a5b09949faDd",
            "0xc342774492b54ce5F8ac662113ED702Fc1b34972",
        ]
        
        # Common BSC tokens
        self.common_tokens = [
            "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
            "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # BUSD
            "0x55d398326f99059fF775485246999027B3197955",  # USDT
        ]
    
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
    
    def scan_for_erc20_contracts(self, start_block: int, num_blocks: int = 5) -> List[Tuple[str, int]]:
        """Scan blocks for potential ERC20 contracts"""
        contracts = []
        
        print(f"📡 Scanning {num_blocks} blocks from {start_block}")
        
        for block_num in range(start_block, start_block + num_blocks):
            print(f"  Block {block_num}...")
            try:
                # Get block
                result = subprocess.check_output([
                    "cast", "block", str(block_num), "--json",
                    "--rpc-url", self.rpc_url
                ], stderr=subprocess.DEVNULL, timeout=5)
                
                block_data = json.loads(result.decode())
                
                # Check transactions for contract creations
                for tx_hash in block_data.get("transactions", [])[:10]:
                    try:
                        tx_result = subprocess.check_output([
                            "cast", "tx", tx_hash, "--json",
                            "--rpc-url", self.rpc_url
                        ], stderr=subprocess.DEVNULL, timeout=2)
                        
                        tx_data = json.loads(tx_result.decode())
                        
                        # Contract creation
                        if tx_data.get("creates"):
                            contracts.append((tx_data["creates"], block_num))
                            print(f"    Found: {tx_data['creates'][:10]}...")
                    except:
                        continue
                        
            except:
                continue
        
        return list(set(contracts))
    
    def run_erc20_fuzzer(self, address: str, block: int, tokens: List[str] = None) -> Dict:
        """Run ityfuzz with erc20 detector"""
        
        if tokens is None:
            tokens = self.common_tokens
        
        print(f"\n🎯 Fuzzing {address[:10]}... at block {block}")
        
        # Create work directory
        work_dir = f"mev/work_dirs/{address}_erc20_{block}_{int(time.time())}"
        os.makedirs(work_dir, exist_ok=True)
        
        # Build targets
        all_targets = [address] + tokens
        targets_str = ",".join(all_targets)
        
        # Build command
        cmd = [
            self.ityfuzz_path, "evm",
            "-t", targets_str,
            "-c", "bsc",
            "--onchain-block-number", str(block),
            "-f",
            "--panic-on-bug",
            "--detectors", "erc20",
            "--work-dir", work_dir,
            "--onchain-etherscan-api-key", self.api_key,
            "--onchain-url", self.rpc_url
        ]
        
        # Environment
        env = os.environ.copy()
        env["RUST_LOG"] = "error"
        env["RAYON_NUM_THREADS"] = "32"
        
        # Run
        start_time = time.time()
        result = {
            "address": address,
            "block": block,
            "work_dir": work_dir,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env
            )
            
            # Timeout 45 seconds
            output, _ = process.communicate(timeout=45)
            output = output.decode()
            
            # Save log
            log_file = f"mev/logs/{address}_erc20_{int(time.time())}.log"
            with open(log_file, "w") as f:
                f.write(output)
            
            # Check for vulnerability
            if "Anyone can earn" in output:
                print(f"   🚨 VULNERABILITY FOUND!")
                
                # Extract profit
                import re
                profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', output)
                profit = float(profit_match.group(1)) if profit_match else 0
                
                # Save vulnerability
                vuln_log = f"mev/vulnerability_logs/{address}_erc20_{int(time.time())}.log"
                with open(vuln_log, "w") as f:
                    f.write(output)
                
                # Save metadata
                metadata = {
                    "address": address,
                    "block": block,
                    "profit_eth": profit,
                    "timestamp": datetime.now().isoformat(),
                    "tokens_used": tokens,
                    "work_dir": work_dir
                }
                
                with open(os.path.join(work_dir, "vulnerability.json"), "w") as f:
                    json.dump(metadata, f, indent=2)
                
                result.update({
                    "status": "VULNERABLE",
                    "profit": profit,
                    "log_file": vuln_log
                })
                
                return result
                
            else:
                print(f"   ✅ Clean")
                shutil.rmtree(work_dir, ignore_errors=True)
                result["status"] = "clean"
                
        except subprocess.TimeoutExpired:
            process.kill()
            print(f"   ⏱️ Timeout")
            result["status"] = "timeout"
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        
        return result

def main():
    print("=== Proven MEV Scanner ===")
    print("Focused on ERC20 vulnerabilities\n")
    
    scanner = ProvenMEVScanner()
    
    # Test known vulnerability first
    print("🧪 Confirming BEGO vulnerability...")
    bego_result = scanner.run_erc20_fuzzer(
        "0x68Cc90351a79A4c10078FE021bE430b7a12aaA09",
        22315679,
        scanner.vulnerable_tokens
    )
    
    if bego_result["status"] == "VULNERABLE":
        print(f"✅ Confirmed! Profit: {bego_result['profit']} ETH")
    
    # Scan recent blocks
    print("\n📡 Scanning recent blocks for similar patterns...")
    current_block = scanner.get_current_block()
    
    # Look at blocks from the last hour
    blocks_per_hour = 1200  # ~3 sec per block on BSC
    start_block = current_block - blocks_per_hour
    
    contracts = scanner.scan_for_erc20_contracts(start_block, num_blocks=10)
    print(f"\nFound {len(contracts)} new contracts")
    
    # Test each contract
    vulnerabilities = []
    if bego_result["status"] == "VULNERABLE":
        vulnerabilities.append(bego_result)
    
    for address, block in contracts[:5]:  # Test first 5
        # Try with common tokens
        result = scanner.run_erc20_fuzzer(address, block)
        
        if result["status"] == "VULNERABLE":
            vulnerabilities.append(result)
        
        # Small delay
        time.sleep(1)
    
    # Generate report
    report = {
        "timestamp": datetime.now().isoformat(),
        "current_block": current_block,
        "contracts_tested": len(contracts[:5]) + 1,
        "vulnerabilities_found": len(vulnerabilities),
        "total_profit_eth": sum(v.get("profit", 0) for v in vulnerabilities),
        "vulnerabilities": vulnerabilities
    }
    
    # Save report
    report_file = f"mev/fuzzing_logs/proven_mev_scan_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SCAN COMPLETE")
    print(f"{'='*60}")
    print(f"Contracts tested: {report['contracts_tested']}")
    print(f"Vulnerabilities found: {len(vulnerabilities)}")
    
    if vulnerabilities:
        print(f"\n💰 Total profit potential: {report['total_profit_eth']:.4f} ETH")
        print(f"\n🚨 Vulnerable contracts:")
        for vuln in vulnerabilities:
            print(f"  {vuln['address'][:10]}... at block {vuln['block']}")
            print(f"    Profit: {vuln.get('profit', 0):.4f} ETH")
            print(f"    Work dir: {vuln['work_dir']}")
    
    print(f"\n📄 Report: {report_file}")
    print("✅ All MEV data saved!")

if __name__ == "__main__":
    main()