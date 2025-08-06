#!/bin/bash

echo "=== Testing ItyFuzz ABI Issue ==="
echo "Running for 10 seconds with the ci detector"
echo ""

# Check if ityfuzz exists
if [ -f "./target/debug/ityfuzz" ]; then
    ITYFUZZ="./target/debug/ityfuzz"
    echo "✅ Using debug build: $ITYFUZZ"
elif [ -f "./target/release/ityfuzz" ]; then
    ITYFUZZ="./target/release/ityfuzz"
    echo "✅ Using release build: $ITYFUZZ"
else
    echo "❌ ItyFuzz binary not found!"
    exit 1
fi

# Use the BEGO contract that we know works
CONTRACT="0x68Cc90351a79A4c10078FE021bE430b7a12aaA09"
TOKEN1="0x88503F48e437a377f1aC2892cBB3a5b09949faDd"
TOKEN2="0xc342774492b54ce5F8ac662113ED702Fc1b34972"
TARGETS="$CONTRACT,$TOKEN1,$TOKEN2"
BLOCK="22315679"
API_KEY="SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
RPC_URL="https://bsc-dataseed.binance.org/"

# Create work directory
WORK_DIR="test_abi_$(date +%s)"
mkdir -p "$WORK_DIR"

echo "🔧 Configuration:"
echo "  Contract: $CONTRACT (BEGO)"
echo "  Tokens: $TOKEN1, $TOKEN2"
echo "  Block: $BLOCK"
echo "  Work dir: $WORK_DIR"
echo ""

# Run with explicit parameters and timeout of 10 seconds
echo "🚀 Running ItyFuzz with all detectors for 10 seconds..."
echo ""

# Export variables and run
export RUST_LOG=error
export RUST_BACKTRACE=1

timeout 10 \
$ITYFUZZ evm \
    -t "$TARGETS" \
    -c bsc \
    --onchain-block-number "$BLOCK" \
    -f \
    --panic-on-bug \
    --detectors "all" \
    --work-dir "$WORK_DIR" \
    --onchain-etherscan-api-key "$API_KEY" \
    --onchain-url "$RPC_URL" \
    2>&1 | tee "test_abi_${WORK_DIR}.log"

echo ""
echo "📊 Test complete. Checking for ABI errors..."
grep -i "abi\|parse\|error" "test_abi_${WORK_DIR}.log" | head -10

echo ""
echo "🔍 Checking if vulnerability was found..."
grep -i "anyone can earn\|vulnerability\|found" "test_abi_${WORK_DIR}.log" | head -5

echo ""
echo "📝 Full log saved to: test_abi_${WORK_DIR}.log"
echo "📁 Work directory: $WORK_DIR"