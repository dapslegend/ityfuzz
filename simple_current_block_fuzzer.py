#!/usr/bin/env python3
"""
Simple fuzzer that uses current block from public RPC
"""

import subprocess
import os
import time
import json

def get_current_block():
    """Get current block from public RPC"""
    try:
        result = subprocess.run([
            "cast", "block", "--rpc-url", "https://bsc-dataseed.binance.org/", "latest"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Extract block number from output
            for line in result.stdout.split('\n'):
                if line.startswith('number'):
                    return int(line.split()[1])
    except Exception as e:
        print(f"Error getting block: {e}")
    
    return None

def run_fuzzer(contract_address, block_number, timeout=60):
    """Run ityfuzz on a contract for specified timeout"""
    
    # Common BSC tokens to include
    tokens = [
        "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # WBNB
        "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",  # BUSD
        "0x55d398326f99059fF775485246999027B3197955",  # USDT
    ]
    
    # Combine contract and tokens
    targets = ",".join([contract_address] + tokens)
    
    # Setup work directory
    work_dir = f"mev/simple_fuzz_{int(time.time())}"
    os.makedirs(work_dir, exist_ok=True)
    
    # Use debug binary
    ityfuzz = "./target/debug/ityfuzz"
    if not os.path.exists(ityfuzz):
        print(f"Error: {ityfuzz} not found!")
        return False
    
    print(f"\n🚀 Fuzzing {contract_address} at block {block_number}")
    print(f"   Timeout: {timeout} seconds")
    print(f"   Work dir: {work_dir}")
    
    # Run ityfuzz with timeout
    cmd = [
        "timeout", str(timeout),
        ityfuzz, "evm",
        "-t", targets,
        "-c", "bsc",
        "--onchain-block-number", str(block_number),
        "-f",
        "--panic-on-bug",
        "--detectors", "erc20",
        "--work-dir", work_dir,
        "--onchain-etherscan-api-key", "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP",
        "--onchain-url", "https://bsc-dataseed.binance.org/"
    ]
    
    # Set environment
    env = os.environ.copy()
    env["RUST_LOG"] = "error"
    
    # Run the command
    log_file = f"{work_dir}/fuzzing.log"
    with open(log_file, "w") as log:
        result = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
    
    # Check for vulnerabilities
    vuln_found = False
    with open(log_file, "r") as log:
        content = log.read()
        if "Anyone can earn" in content:
            vuln_found = True
            print(f"   ✅ VULNERABILITY FOUND!")
            # Save to vulnerability logs
            os.makedirs("mev/vulnerability_logs", exist_ok=True)
            vuln_log = f"mev/vulnerability_logs/{contract_address}_{int(time.time())}.log"
            with open(vuln_log, "w") as vlog:
                vlog.write(content)
    
    if not vuln_found:
        print(f"   ❌ No vulnerability found")
    
    return vuln_found

def main():
    print("=== Simple Current Block Fuzzer ===")
    
    # Create directories
    os.makedirs("mev", exist_ok=True)
    os.makedirs("mev/logs", exist_ok=True)
    os.makedirs("mev/vulnerability_logs", exist_ok=True)
    
    # Get current block
    block = get_current_block()
    if not block:
        print("❌ Failed to get current block")
        return
    
    print(f"📊 Current BSC block: {block}")
    
    # Test with known contracts at current block
    test_contracts = [
        ("CAKE", "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"),
        ("PancakeRouter", "0x10ED43C718714eb63d5aA57B78B54704E256024E"),
        ("BUSD", "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"),
    ]
    
    # Also check if BEGO is still vulnerable at current block
    test_contracts.append(("BEGO", "0x68Cc90351a79A4c10078FE021bE430b7a12aaA09"))
    
    print(f"\n🔍 Testing {len(test_contracts)} contracts at block {block}")
    
    vulnerabilities_found = 0
    
    for name, address in test_contracts:
        print(f"\n📌 Testing {name} ({address})")
        
        # Run fuzzer for 30 seconds
        if run_fuzzer(address, block, timeout=30):
            vulnerabilities_found += 1
    
    print(f"\n📊 Summary:")
    print(f"   Contracts tested: {len(test_contracts)}")
    print(f"   Vulnerabilities found: {vulnerabilities_found}")
    print(f"   Logs saved in: mev/")

if __name__ == "__main__":
    main()