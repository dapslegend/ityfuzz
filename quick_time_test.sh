#!/bin/bash

# Configuration
API_KEY="SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
RPC_URL="https://rpc.ankr.com/bsc"

echo "🚀 QUICK TIME TEST: Testing detection times"
echo ""

# Test function
quick_test() {
    local name=$1
    local target=$2
    local block=$3
    local time_limit=$4
    
    echo "Testing $name with ${time_limit}s limit..."
    
    timeout ${time_limit}s ./target/release/ityfuzz evm \
        -t "$target" \
        -c bsc \
        --onchain-block-number "$block" \
        -f \
        --panic-on-bug \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$RPC_URL" \
        --detectors all \
        --work-dir "backtest_results/${name}_quick_${time_limit}s" \
        > "backtest_results/${name}_quick_${time_limit}s.log" 2>&1
    
    if grep -q "Found vulnerabilities" "backtest_results/${name}_quick_${time_limit}s.log" 2>/dev/null; then
        echo "✅ $name: FOUND in ${time_limit}s!"
        grep -A3 "Found vulnerabilities" "backtest_results/${name}_quick_${time_limit}s.log" | head -5
        grep "run time:" "backtest_results/${name}_quick_${time_limit}s.log" | tail -1
        grep "exec/sec" "backtest_results/${name}_quick_${time_limit}s.log" | tail -1
    else
        echo "❌ $name: Not found in ${time_limit}s"
        grep "exec/sec" "backtest_results/${name}_quick_${time_limit}s.log" 2>/dev/null | tail -1
    fi
    echo ""
}

# Test EGD-Finance first (expected to be fast - 2s)
echo "=== Testing EGD-Finance (expected: ~2s) ==="
for time in 5 10 20; do
    quick_test "EGD-Finance" \
        "0x55d398326f99059fF775485246999027B3197955,0x202b233735bF743FA31abb8f71e641970161bF98,0xa361433E409Adac1f87CDF133127585F8a93c67d,0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE,0x34Bd6Dba456Bc31c2b3393e499fa10bED32a9370,0xc30808d9373093fbfcec9e026457c6a9dab706a7,0x34bd6dba456bc31c2b3393e499fa10bed32a9370,0x93c175439726797dcee24d08e4ac9164e88e7aee" \
        20245522 \
        $time
done

# Test SEAMAN (expected: ~3s)
echo "=== Testing SEAMAN (expected: ~3s) ==="
for time in 5 10 20 30; do
    quick_test "SEAMAN" \
        "0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e" \
        23467515 \
        $time
done

# Test BBOX (expected: ~4s)
echo "=== Testing BBOX (expected: ~4s) ==="
quick_test "BBOX" \
    "0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c" \
    23106506 \
    10

echo "📊 Quick test completed!"