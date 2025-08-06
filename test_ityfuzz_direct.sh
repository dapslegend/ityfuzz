#!/bin/bash

echo "Testing ItyFuzz directly with BEGO contract..."

# BEGO contract from previous findings
TARGET="0x68Cc90351a79A4c10078FE021bE430b7a12aaA09"
TOKENS="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972"
BLOCK="22315679"

# Create work directory
WORK_DIR="test_work_$(date +%s)"
mkdir -p "$WORK_DIR"

echo "Running ItyFuzz..."
echo "Target: $TARGET"
echo "Block: $BLOCK"
echo "Work dir: $WORK_DIR"
echo ""

# Run with timeout
timeout 30 ./target/debug/ityfuzz evm \
    -t "$TARGET,$TOKENS" \
    -c bsc \
    --onchain-block-number "$BLOCK" \
    -f \
    --panic-on-bug \
    --detectors "all" \
    --work-dir "$WORK_DIR" \
    --onchain-etherscan-api-key "6J26IP7U4YSMEUFVWQWJJRMIT2XNBY2VPU" \
    --onchain-url "https://bsc-dataseed.binance.org/" \
    2>&1 | tee test_output.log

echo ""
echo "Checking results..."

if grep -q "Anyone can earn" test_output.log; then
    echo "✅ Vulnerability found!"
    grep "Anyone can earn" test_output.log
else
    echo "❌ No vulnerability found"
fi

echo ""
echo "Log saved to: test_output.log"
echo "Work dir: $WORK_DIR"