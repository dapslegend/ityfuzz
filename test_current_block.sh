#!/bin/bash

echo "Testing ItyFuzz at current block..."

# Get current block
CURRENT_BLOCK=$(cast block-number --rpc-url https://bsc-dataseed.binance.org/)
echo "Current BSC block: $CURRENT_BLOCK"

# CAKE token - should exist at current block
TARGET="0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
TOKENS="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"  # WBNB

# Create work directory
WORK_DIR="test_work_current_$(date +%s)"
mkdir -p "$WORK_DIR"

echo ""
echo "Running ItyFuzz..."
echo "Target: $TARGET (CAKE token)"
echo "Block: $CURRENT_BLOCK"
echo "Work dir: $WORK_DIR"
echo ""

# Run with timeout
timeout 60 ./target/debug/ityfuzz evm \
    -t "$TARGET,$TOKENS" \
    -c bsc \
    --onchain-block-number "$CURRENT_BLOCK" \
    -f \
    --detectors "all" \
    --work-dir "$WORK_DIR" \
    --onchain-etherscan-api-key "6J26IP7U4YSMEUFVWQWJJRMIT2XNBY2VPU" \
    --onchain-url "https://bsc-dataseed.binance.org/" \
    2>&1 | tee test_current_output.log

echo ""
echo "Checking results..."

if grep -q "Found vulnerabilities" test_current_output.log; then
    echo "✅ Vulnerability found!"
    grep -A5 "Found vulnerabilities" test_current_output.log
elif grep -q "Anyone can earn" test_current_output.log; then
    echo "✅ Vulnerability found!"
    grep "Anyone can earn" test_current_output.log
else
    echo "❌ No vulnerability found"
fi

echo ""
echo "Log saved to: test_current_output.log"
echo "Work dir: $WORK_DIR"