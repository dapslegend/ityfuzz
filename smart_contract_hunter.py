#!/usr/bin/env python3
"""
Smart Contract Hunter - Find contracts on historical RPC and fuzz with public RPC
"""

import subprocess
import json
import time
import os
import re
from typing import List, Dict, Set, Tuple
from datetime import datetime
import concurrent.futures

class SmartContractHunter:
    """Hunt for vulnerable smart contracts"""
    
    def __init__(self):
        self.historical_rpc = "http://159.198.35.169:8545"
        self.public_rpc = "https://bsc-dataseed.binance.org/"
        self.ityfuzz_path = "./target/debug/cli"
        
        # Known addresses
        self.wbnb = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
        self.busd = "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"
        self.usdt = "0x55d398326f99059fF775485246999027B3197955"
        self.pancake_router = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
        
        # Vulnerable selectors to look for
        self.vuln_selectors = {
            "3ccfd60b": "withdraw()",
            "853828b6": "withdrawAll()", 
            "db2e21bc": "emergencyWithdraw()",
            "2e1a7d4d": "withdraw(uint256)",
            "bc25cf77": "skim(address)",
            "69328dec": "harvest(address,uint256)",
            "4e71d92d": "claim()",
            "8e4035d6": "sweep(address)",
            "4b820093": "rescue(address,uint256)"
        }
    
    def get_block_range(self) -> Tuple[Tuple[int, int], int]:
        """Get available block range"""
        # Get historical latest
        hist_block = int(subprocess.check_output([
            "cast", "block-number", "--rpc-url", self.historical_rpc
        ]).decode().strip())
        
        # Get public latest
        pub_block = int(subprocess.check_output([
            "cast", "block-number", "--rpc-url", self.public_rpc
        ]).decode().strip())
        
        print(f"Historical RPC: Block {hist_block}")
        print(f"Public RPC: Block {pub_block}")
        
        # Scan last 100 blocks from historical
        return (hist_block - 100, hist_block), pub_block
    
    def find_contracts_in_block(self, block_num: int) -> List[Dict]:
        """Find all contracts deployed or interacted in a block"""
        contracts = []
        
        try:
            # Get block transactions
            cmd = ["cast", "block", str(block_num), "--json", "--rpc-url", self.historical_rpc]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                block_data = json.loads(result.stdout)
                
                # Extract unique addresses from transactions
                addresses = set()
                for tx_hash in block_data.get("transactions", []):
                    # Get transaction details
                    tx_cmd = ["cast", "tx", tx_hash, "--json", "--rpc-url", self.historical_rpc]
                    tx_result = subprocess.run(tx_cmd, capture_output=True, text=True)
                    
                    if tx_result.returncode == 0:
                        tx_data = json.loads(tx_result.stdout)
                        
                        # Add 'to' address if it's a contract
                        if tx_data.get("to"):
                            addresses.add(tx_data["to"])
                        
                        # Check for contract creation
                        if not tx_data.get("to"):
                            # Get receipt for contract address
                            receipt_cmd = ["cast", "receipt", tx_hash, "--json", "--rpc-url", self.historical_rpc]
                            receipt_result = subprocess.run(receipt_cmd, capture_output=True, text=True)
                            
                            if receipt_result.returncode == 0:
                                receipt = json.loads(receipt_result.stdout)
                                if receipt.get("contractAddress"):
                                    addresses.add(receipt["contractAddress"])
                
                # Check each address
                for addr in addresses:
                    if self.is_vulnerable_contract(addr):
                        contracts.append({
                            "address": addr,
                            "block": block_num
                        })
                        
        except Exception as e:
            pass
        
        return contracts
    
    def is_vulnerable_contract(self, address: str) -> bool:
        """Quick check if contract might be vulnerable"""
        try:
            # Get code
            code = subprocess.check_output([
                "cast", "code", address, "--rpc-url", self.historical_rpc
            ]).decode().strip()
            
            if len(code) < 100:  # Not a contract or too small
                return False
            
            # Check for vulnerable selectors
            for selector in self.vuln_selectors.keys():
                if selector in code.lower():
                    return True
            
            return False
            
        except:
            return False
    
    def analyze_contract(self, address: str) -> Dict:
        """Detailed analysis of contract"""
        info = {
            "address": address,
            "vulnerable_functions": [],
            "has_balance": False,
            "tokens": [],
            "is_verified": False
        }
        
        try:
            # Get code
            code = subprocess.check_output([
                "cast", "code", address, "--rpc-url", self.historical_rpc
            ]).decode().strip()
            
            # Find vulnerable functions
            for selector, name in self.vuln_selectors.items():
                if selector in code.lower():
                    info["vulnerable_functions"].append(name)
            
            # Check balance
            balance = subprocess.check_output([
                "cast", "balance", address, "--rpc-url", self.historical_rpc
            ]).decode().strip()
            
            if int(balance) > 0:
                info["has_balance"] = True
                info["balance_eth"] = int(balance) / 1e18
            
            # Try to find associated tokens by checking common slots
            tokens = self.find_contract_tokens(address)
            info["tokens"] = tokens
            
        except:
            pass
        
        return info
    
    def find_contract_tokens(self, address: str) -> List[str]:
        """Find tokens associated with contract"""
        tokens = []
        
        # Check first 10 storage slots for token addresses
        for slot in range(10):
            try:
                value = subprocess.check_output([
                    "cast", "storage", address, str(slot),
                    "--rpc-url", self.historical_rpc
                ]).decode().strip()
                
                # Check if it looks like an address
                if len(value) == 66 and value.startswith("0x000000000000000000000000"):
                    potential_addr = "0x" + value[-40:]
                    
                    # Verify it's a token by checking for symbol
                    try:
                        subprocess.check_output([
                            "cast", "call", potential_addr, "symbol()(string)",
                            "--rpc-url", self.historical_rpc
                        ])
                        tokens.append(potential_addr)
                    except:
                        pass
                        
            except:
                pass
        
        return tokens
    
    def fuzz_contract(self, contract_info: Dict, block: int) -> Dict:
        """Fuzz a contract with ItyFuzz"""
        result = {
            "address": contract_info["address"],
            "status": "pending",
            "profit": 0,
            "vulnerabilities": []
        }
        
        # Build command
        cmd = [
            self.ityfuzz_path,
            "-t", contract_info["address"],
            "-c", "BSC",
            "--onchain-block-number", str(block),
            "-f", "-i", "-p",
            "--run-forever", "60"  # 1 minute
        ]
        
        # Add standard tokens
        cmd.extend(["-t", self.wbnb])
        cmd.extend(["-t", self.busd])
        cmd.extend(["-t", self.usdt])
        
        # Add contract-specific tokens
        for token in contract_info.get("tokens", [])[:3]:
            cmd.extend(["-t", token])
        
        # Set environment
        env = os.environ.copy()
        env["ETH_RPC_URL"] = self.public_rpc
        env["RUST_LOG"] = "info"
        
        print(f"\n🔍 Fuzzing {contract_info['address']}...")
        print(f"   Functions: {', '.join(contract_info.get('vulnerable_functions', []))}")
        
        try:
            # Run fuzzer
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            stdout, stderr = process.communicate(timeout=70)
            
            output = stdout.decode() + stderr.decode()
            
            # Parse results
            if "Anyone can earn" in output:
                profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', output)
                if profit_match:
                    result["profit"] = float(profit_match.group(1))
                    result["status"] = "VULNERABLE"
                    
                    # Save log
                    log_file = f"vuln_{contract_info['address']}_{int(time.time())}.log"
                    with open(log_file, "w") as f:
                        f.write(output)
                    result["log_file"] = log_file
                    
                    print(f"   🚨 VULNERABLE! Profit: {result['profit']} ETH")
            else:
                result["status"] = "clean"
                print(f"   ✅ Clean")
                
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
    print("=== Smart Contract Hunter ===\n")
    
    hunter = SmartContractHunter()
    
    # Get block ranges
    (start_block, end_block), current_block = hunter.get_block_range()
    
    print(f"\nScanning blocks {start_block} to {end_block}")
    print(f"Will fuzz at block {current_block - 1}\n")
    
    # Find contracts
    print("🔍 Hunting for contracts...")
    all_contracts = []
    
    # Parallel block scanning
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for block in range(start_block, end_block + 1):
            future = executor.submit(hunter.find_contracts_in_block, block)
            futures.append((block, future))
        
        for block, future in futures:
            contracts = future.result()
            if contracts:
                print(f"  Block {block}: Found {len(contracts)} potential targets")
                all_contracts.extend(contracts)
    
    print(f"\n📊 Found {len(all_contracts)} potential vulnerable contracts")
    
    # Analyze contracts
    print("\n📋 Analyzing contracts...")
    targets = []
    
    for contract in all_contracts[:50]:  # Limit analysis
        info = hunter.analyze_contract(contract["address"])
        if info["vulnerable_functions"]:
            targets.append(info)
            print(f"  ✓ {info['address']}: {', '.join(info['vulnerable_functions'][:3])}")
            if info["has_balance"]:
                print(f"    💰 Balance: {info['balance_eth']:.4f} ETH")
    
    print(f"\n🎯 {len(targets)} contracts ready for fuzzing")
    
    # Fuzz contracts
    print("\n🚀 Starting fuzzing campaign...")
    vulnerabilities = []
    
    for i, target in enumerate(targets[:10]):  # Limit to 10
        print(f"\n[{i+1}/10] {target['address']}")
        result = hunter.fuzz_contract(target, current_block - 1)
        
        if result["status"] == "VULNERABLE":
            vulnerabilities.append(result)
    
    # Generate report
    report = {
        "scan_time": datetime.now().isoformat(),
        "blocks_scanned": {
            "start": start_block,
            "end": end_block
        },
        "fuzzing_block": current_block - 1,
        "contracts_found": len(all_contracts),
        "contracts_analyzed": len(targets),
        "contracts_fuzzed": min(10, len(targets)),
        "vulnerabilities": vulnerabilities
    }
    
    # Save report
    report_file = f"hunt_report_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"📊 HUNT COMPLETE")
    print(f"{'='*50}")
    print(f"Contracts found: {len(all_contracts)}")
    print(f"Contracts analyzed: {len(targets)}")
    print(f"Contracts fuzzed: {min(10, len(targets))}")
    print(f"Vulnerabilities found: {len(vulnerabilities)}")
    
    if vulnerabilities:
        total_profit = sum(v["profit"] for v in vulnerabilities)
        print(f"\n💰 Total potential profit: {total_profit:.4f} ETH")
        print(f"\n🚨 Vulnerable contracts:")
        for vuln in vulnerabilities:
            print(f"  {vuln['address']}: {vuln['profit']:.4f} ETH")
    
    print(f"\n📄 Report saved to: {report_file}")

if __name__ == "__main__":
    main()