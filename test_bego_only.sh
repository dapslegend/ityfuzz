#!/bin/bash

echo "Testing BEGO vulnerability with exact parameters..."

# Create work directory
WORK_DIR="mev/work_dirs/BEGO_test_$(date +%s)"
mkdir -p "$WORK_DIR"

# Run with exact parameters that worked before
RUST_LOG=error \
RAYON_NUM_THREADS=32 \
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
    2>&1 | tee "mev/logs/BEGO_test_$(date +%s).log"

echo ""
echo "Check the log for 'Anyone can earn' to confirm vulnerability"