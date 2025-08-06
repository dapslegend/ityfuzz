#!/bin/bash

echo "=== Testing ItyFuzz with BEGO vulnerability ==="
echo ""

# Set up environment
export RUST_LOG=info
export RUST_BACKTRACE=1

# Configuration
WORK_DIR="test_bego_$(date +%s)"
mkdir -p "$WORK_DIR"

echo "📊 Configuration:"
echo "  Work directory: $WORK_DIR"
echo "  Block: 22315679 (vulnerable block)"
echo ""

# Run ityfuzz
echo "🚀 Running ItyFuzz..."

# Use the exact same parameters that worked before
./target/debug/ityfuzz evm \
    -t "0x68Cc90351a79A4c10078FE021bE430b7a12aaA09,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972" \
    -c bsc \
    --onchain-block-number 22315679 \
    -f \
    --panic-on-bug \
    --detectors "erc20" \
    --work-dir "$WORK_DIR" \
    --onchain-etherscan-api-key "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP" \
    --onchain-url "https://bsc-dataseed.binance.org/" \
    2>&1 | tee "${WORK_DIR}/fuzzing.log"

echo ""
echo "📝 Checking results..."
grep -i "anyone can earn" "${WORK_DIR}/fuzzing.log" | head -5

echo ""
echo "✅ Test complete. Log saved to: ${WORK_DIR}/fuzzing.log"