#!/bin/bash

echo "=== Corrected MEV Scanner ==="
echo "Running with proper contract addresses included"
echo ""

# Kill any existing processes
pkill -f "ityfuzz" || true
sleep 2

# Create directories
mkdir -p mev/work_dirs
mkdir -p mev/vulnerability_logs
mkdir -p mev/logs

# Function to run ityfuzz with correct parameters
run_test() {
    local name=$1
    local contract=$2
    local tokens=$3
    local block=$4
    local detector=$5
    
    echo "🐅 Testing $name with $detector at block $block..."
    
    # Combine contract and tokens
    local targets="$contract,$tokens"
    
    # Run with 120 second timeout
    timeout 120 ./target/debug/ityfuzz evm \
        -t "$targets" \
        -c bsc \
        --onchain-block-number "$block" \
        -f \
        --panic-on-bug \
        --onchain-etherscan-api-key "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP" \
        --onchain-url "https://bsc-dataseed.binance.org/" \
        --detectors "$detector" \
        --work-dir "mev/work_dirs/${name}_${detector}_${block}" \
        > "mev/logs/${name}_${detector}_${block}.log" 2>&1
    
    # Check for vulnerabilities
    if grep -q "Anyone can earn" "mev/logs/${name}_${detector}_${block}.log"; then
        PROFIT=$(grep -oE "[0-9]+\.[0-9]+ ETH" "mev/logs/${name}_${detector}_${block}.log" | head -1)
        echo "  ✅ VULNERABILITY FOUND! $PROFIT"
        cp "mev/logs/${name}_${detector}_${block}.log" "mev/vulnerability_logs/"
    else
        echo "  ❌ No vulnerability found"
    fi
}

# Test configurations with CORRECT addresses
echo "📊 Running tests with corrected configurations..."
echo ""

# BEGO - Include the actual contract address
run_test "BEGO" \
    "0x68Cc90351a79A4c10078FE021bE430b7a12aaA09" \
    "0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c" \
    "22315679" \
    "erc20"

# BBOX - Include the actual contract address
run_test "BBOX" \
    "0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c" \
    "23106506" \
    "all"

echo ""
echo "✅ Tests complete! Check mev/vulnerability_logs/ for results"