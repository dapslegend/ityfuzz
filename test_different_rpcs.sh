#!/bin/bash

# Different BSC RPC endpoints to test
RPC_ENDPOINTS=(
    "https://bsc-dataseed.binance.org/"
    "https://bsc-dataseed1.defibit.io/"
    "https://bsc-dataseed1.ninicoin.io/"
    "https://bsc.publicnode.com"
    "https://binance.nodereal.io"
    "https://rpc.ankr.com/bsc"
    "https://bscrpc.com"
    "https://bsc-rpc.gateway.pokt.network/"
)

API_KEY="SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"

echo "🔍 Testing different BSC RPC endpoints for BEGO vulnerability..."
echo "Target block: 22315679"
echo ""

# Test each RPC endpoint
for rpc in "${RPC_ENDPOINTS[@]}"; do
    echo "================================================================"
    echo "Testing RPC: $rpc"
    echo "================================================================"
    
    # Create a unique work directory for each test
    work_dir="backtest_results/BEGO_rpc_$(echo $rpc | sed 's/[^a-zA-Z0-9]/_/g')"
    log_file="${work_dir}.log"
    
    # Run the test with timeout
    echo "Running 60-second test..."
    timeout 60s ./target/release/ityfuzz evm \
        -t "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972" \
        -c bsc \
        --onchain-block-number 22315679 \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$rpc" \
        --detectors all \
        --work-dir "$work_dir" \
        2>&1 | tee "$log_file" &
    
    pid=$!
    
    # Monitor for 60 seconds
    for i in {1..60}; do
        if ! kill -0 $pid 2>/dev/null; then
            break
        fi
        
        # Check for bug detection every 10 seconds
        if [ $((i % 10)) -eq 0 ]; then
            if grep -q "typed_bug\|Fund Loss\|vulnerability" "$log_file" 2>/dev/null; then
                echo "✅ BUG FOUND with RPC: $rpc"
                break
            fi
        fi
        sleep 1
    done
    
    # Kill the process if still running
    kill $pid 2>/dev/null
    wait $pid 2>/dev/null
    
    # Check final results
    echo ""
    echo "Results for $rpc:"
    if grep -q "typed_bug\|Fund Loss\|vulnerability" "$log_file" 2>/dev/null; then
        echo "✅ SUCCESS: Bug detected!"
        grep -A5 -B5 "typed_bug\|Fund Loss\|vulnerability" "$log_file" | tail -20
    else
        echo "❌ No bug found"
        # Show performance stats
        grep "exec/sec" "$log_file" 2>/dev/null | tail -3
    fi
    
    # Check for RPC errors
    if grep -q "RPC error\|fail to find block" "$log_file" 2>/dev/null; then
        echo "⚠️  RPC errors detected"
    fi
    
    echo ""
done

echo "🏁 RPC testing completed!"
echo ""
echo "Summary:"
for rpc in "${RPC_ENDPOINTS[@]}"; do
    log_file="backtest_results/BEGO_rpc_$(echo $rpc | sed 's/[^a-zA-Z0-9]/_/g').log"
    if [ -f "$log_file" ]; then
        if grep -q "typed_bug\|Fund Loss\|vulnerability" "$log_file" 2>/dev/null; then
            echo "✅ $rpc - BUG FOUND"
        elif grep -q "RPC error\|fail to find block" "$log_file" 2>/dev/null; then
            echo "⚠️  $rpc - RPC ERRORS"
        else
            echo "❌ $rpc - No bug found"
        fi
    fi
done