#!/bin/bash

echo "Testing ItyFuzz with working API key..."

# Use CAKE token at current block
TARGET="0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82"
TOKENS="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
CURRENT_BLOCK=$(cast block-number --rpc-url https://bsc-dataseed.binance.org/)

echo "Target: $TARGET (CAKE)"
echo "Block: $CURRENT_BLOCK"
echo ""

# Test with erc20 detector first
export RUST_LOG=error
timeout 30 ./target/debug/ityfuzz evm \
    -t "$TARGET,$TOKENS" \
    -c bsc \
    --onchain-block-number "$CURRENT_BLOCK" \
    -f \
    --panic-on-bug \
    --detectors "erc20" \
    --work-dir "test_work_api" \
    --onchain-etherscan-api-key "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP" \
    --onchain-url "https://bsc-dataseed.binance.org/" \
    2>&1 | tee test_api.log

echo ""
if grep -q "Found vulnerabilities\|Anyone can earn" test_api.log; then
    echo "✅ Success!"
    grep -E "Found vulnerabilities|Anyone can earn" test_api.log
else
    echo "❌ No vulnerability found"
    # Check if it ran successfully
    if grep -q "Fuzzing halted" test_api.log; then
        echo "✓ But fuzzing completed successfully"
    fi
fi