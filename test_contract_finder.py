#!/usr/bin/env python3
"""Test contract finding from blockchain"""

import subprocess
import json

# Test getting a recent block
historical_rpc = "http://159.198.35.169:8545"

# Get latest block
latest = int(subprocess.check_output([
    "cast", "block-number", "--rpc-url", historical_rpc
]).decode().strip())

print(f"Latest block: {latest}")

# Get a block with transactions
for block_num in range(latest - 5, latest + 1):
    print(f"\nChecking block {block_num}...")
    
    cmd = ["cast", "block", str(block_num), "--json", "--rpc-url", historical_rpc]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        block_data = json.loads(result.stdout)
        tx_count = len(block_data.get("transactions", []))
        print(f"  Transactions: {tx_count}")
        
        if tx_count > 0:
            # Check first few transactions
            for i, tx in enumerate(block_data["transactions"][:3]):
                # Transaction data is already parsed if it's a dict
                if isinstance(tx, dict):
                    tx_data = tx
                    tx_hash = tx_data.get("hash", "unknown")
                else:
                    tx_hash = tx
                    # Get transaction details
                    tx_cmd = ["cast", "tx", tx_hash, "--json", "--rpc-url", historical_rpc]
                    tx_result = subprocess.run(tx_cmd, capture_output=True, text=True)
                    
                    if tx_result.returncode != 0:
                        continue
                    tx_data = json.loads(tx_result.stdout)
                
                print(f"\n  Transaction {i+1}: {tx_hash}")
                to_addr = tx_data.get("to")
                from_addr = tx_data.get("from")
                
                print(f"    From: {from_addr}")
                print(f"    To: {to_addr}")
                
                # Check if 'to' is a contract
                if to_addr and to_addr != "0x0000000000000000000000000000000000000000":
                    code_result = subprocess.run([
                        "cast", "code", to_addr, "--rpc-url", historical_rpc
                    ], capture_output=True, text=True)
                    
                    if code_result.returncode == 0:
                        code = code_result.stdout.strip()
                        if len(code) > 10:
                            print(f"    ✅ TO ADDRESS IS A CONTRACT! Code length: {len(code)}")
                        else:
                            print(f"    ❌ To address is EOA")
                
                # Check for contract creation
                if not to_addr or to_addr == "0x0000000000000000000000000000000000000000":
                    print("    🔍 Checking for contract creation...")
                    receipt_cmd = ["cast", "receipt", tx_hash, "--json", "--rpc-url", historical_rpc]
                    receipt_result = subprocess.run(receipt_cmd, capture_output=True, text=True)
                    
                    if receipt_result.returncode == 0:
                        receipt = json.loads(receipt_result.stdout)
                        contract_addr = receipt.get("contractAddress")
                        if contract_addr and contract_addr != "0x0000000000000000000000000000000000000000":
                            print(f"    🎉 CONTRACT CREATED: {contract_addr}")