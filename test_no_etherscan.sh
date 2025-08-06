#!/bin/bash

echo "Testing ItyFuzz without Etherscan API..."

# Get current block
CURRENT_BLOCK=$(cast block-number --rpc-url https://bsc-dataseed.binance.org/)
echo "Current BSC block: $CURRENT_BLOCK"

# PancakeSwap Router - well-known contract
TARGET="0x10ED43C718714eb63d5aA57B78B54704E256024E"
TOKENS="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56"  # WBNB,BUSD

# Create work directory
WORK_DIR="test_work_no_api_$(date +%s)"
mkdir -p "$WORK_DIR"

echo ""
echo "Running ItyFuzz..."
echo "Target: $TARGET (PancakeSwap Router)"
echo "Block: $CURRENT_BLOCK"
echo "Work dir: $WORK_DIR"
echo ""

# Set environment
export RUST_LOG=error
export RAYON_NUM_THREADS=32

# Run with timeout
timeout 60 ./target/debug/ityfuzz evm \
    -t "$TARGET,$TOKENS" \
    -c bsc \
    --onchain-block-number "$CURRENT_BLOCK" \
    -f \
    --detectors "all" \
    --work-dir "$WORK_DIR" \
    --onchain-url "https://bsc-dataseed.binance.org/" \
    2>&1 | tee test_no_etherscan.log

echo ""
echo "Checking results..."

if grep -q "Found vulnerabilities" test_no_etherscan.log; then
    echo "✅ Vulnerability found!"
    grep -A5 "Found vulnerabilities" test_no_etherscan.log
elif grep -q "Anyone can earn" test_no_etherscan.log; then
    echo "✅ Vulnerability found!"
    grep "Anyone can earn" test_no_etherscan.log
elif grep -q "succeeded" test_no_etherscan.log; then
    echo "✅ Fuzzing completed successfully"
else
    echo "❌ Fuzzing failed or no vulnerability found"
fi

echo ""
echo "Log saved to: test_no_etherscan.log"
echo "Work dir: $WORK_DIR"