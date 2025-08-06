#!/bin/bash

echo "Testing with known vulnerable BEGO contract..."

# BEGO - known vulnerable
TARGET="0x68Cc90351a79A4c10078FE021bE430b7a12aaA09"
TOKENS="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972"
BLOCK="22315679"

echo "Target: $TARGET"
echo "Block: $BLOCK"
echo "Detectors to test: erc20, reentrancy, arbitrary_call"
echo ""

# Test different detectors
DETECTORS=("erc20" "reentrancy" "arbitrary_call" "typed_bug")

for detector in "${DETECTORS[@]}"; do
    echo "================================"
    echo "Testing detector: $detector"
    echo "================================"
    
    export RUST_LOG=error
    timeout 30 ./target/debug/ityfuzz evm \
        -t "$TARGET,$TOKENS" \
        -c bsc \
        --onchain-block-number "$BLOCK" \
        -f \
        --panic-on-bug \
        --detectors "$detector" \
        --work-dir "test_work_${detector}" \
        --onchain-etherscan-api-key "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP" \
        --onchain-url "https://bsc-dataseed.binance.org/" \
        > "test_${detector}.log" 2>&1
    
    # Check results
    if grep -q "Found vulnerabilities\|Anyone can earn" "test_${detector}.log" 2>/dev/null; then
        echo "✅ VULNERABILITY FOUND with $detector!"
        grep -E "Found vulnerabilities|Anyone can earn" "test_${detector}.log"
        echo "Log saved to: test_${detector}.log"
        break
    else
        echo "❌ No vulnerability with $detector"
        # Check for errors
        if grep -q "panicked\|error" "test_${detector}.log" 2>/dev/null; then
            echo "   ⚠️  Error detected:"
            grep -A2 "panicked\|error" "test_${detector}.log" | head -5
        fi
    fi
    echo ""
done