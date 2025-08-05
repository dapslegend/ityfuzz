#!/bin/bash

# Try different public RPC endpoints
RPCS=(
    "https://bsc-dataseed.binance.org/"
    "https://bsc-dataseed1.binance.org/"
    "https://bsc-dataseed2.binance.org/"
    "https://bsc.publicnode.com"
)

API_KEY="SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"

echo "🔍 Testing BBOX with different RPCs..."
echo ""

for rpc in "${RPCS[@]}"; do
    echo "Testing with RPC: $rpc"
    
    timeout 20s ./target/release/ityfuzz evm \
        -t "0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c" \
        -c bsc \
        --onchain-block-number 23106506 \
        -f \
        --panic-on-bug \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$rpc" \
        --detectors all \
        --work-dir "backtest_results/BBOX_rpc_test_$(echo $rpc | sed 's/[^a-zA-Z0-9]/_/g')" \
        > "backtest_results/BBOX_rpc_test_$(echo $rpc | sed 's/[^a-zA-Z0-9]/_/g').log" 2>&1
    
    if grep -q "Found vulnerabilities" "backtest_results/BBOX_rpc_test_$(echo $rpc | sed 's/[^a-zA-Z0-9]/_/g').log" 2>/dev/null; then
        echo "✅ FOUND with $rpc!"
        grep -A5 "Found vulnerabilities" "backtest_results/BBOX_rpc_test_$(echo $rpc | sed 's/[^a-zA-Z0-9]/_/g').log"
        break
    else
        echo "❌ Not found with $rpc"
        # Check for RPC errors
        if grep -q "RPC error\|fetching" "backtest_results/BBOX_rpc_test_$(echo $rpc | sed 's/[^a-zA-Z0-9]/_/g').log" 2>/dev/null; then
            echo "   ⚠️  RPC errors detected"
        fi
    fi
    echo ""
done