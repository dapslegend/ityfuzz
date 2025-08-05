#!/bin/bash

# Configuration
API_KEY="SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
PUBLIC_RPC="https://bnb.api.onfinality.io/public"
ITYFUZZ_RPC="http://159.198.35.169:8545"

# Set environment variables with public RPC
export ETH_RPC_URL=$PUBLIC_RPC
export BSC_RPC_URL=$PUBLIC_RPC
export BSC_ETHERSCAN_API_KEY=$API_KEY

# RPC handling settings
export RPC_RETRY_DELAY=100
export RPC_MAX_RETRIES=5
export RPC_RATE_LIMIT_DELAY=50

echo "🚀 Running AGGRESSIVE BSC Backtest with optimized ityfuzz..."
echo "⏱️  Maximum runtime: 60 seconds per test"
echo "🔧 ENV RPC: ${PUBLIC_RPC}"
echo "🔧 ITYFUZZ RPC: ${ITYFUZZ_RPC}"
echo "🎯 Focus: PROFITABLE PATHS & EXPLOITS"
echo ""

# Create results directory
mkdir -p backtest_results

# Function to run test with timeout
run_test() {
    local name=$1
    local target=$2
    local block=$3
    local timeout=${4:-60}
    
    echo "================================================================"
    echo "🔍 Testing $name (Block: $block)"
    echo "================================================================"
    
    # Run with timeout and capture output
    timeout ${timeout}s ./target/release/ityfuzz evm \
        -t "$target" \
        -c bsc \
        --onchain-block-number "$block" \
        -o \
        -f \
        --panic-on-bug \
        --detectors all \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$ITYFUZZ_RPC" \
        --work-dir "backtest_results/${name}_aggressive" \
        2>&1 | tee "backtest_results/${name}_aggressive.log" &
    
    local pid=$!
    
    # Monitor progress
    local elapsed=0
    while kill -0 $pid 2>/dev/null && [ $elapsed -lt $timeout ]; do
        sleep 1
        elapsed=$((elapsed + 1))
        if [ $((elapsed % 10)) -eq 0 ]; then
            echo "⏱️  $elapsed seconds elapsed..."
            # Check if bug found
            if grep -q "Found bug\|Fund Loss\|Price Manipulation" "backtest_results/${name}_aggressive.log" 2>/dev/null; then
                echo "🎯 BUG FOUND! Waiting for details..."
            fi
        fi
    done
    
    # Wait for process to finish
    wait $pid
    
    # Check results
    if grep -q "Found bug\|Fund Loss\|Price Manipulation" "backtest_results/${name}_aggressive.log" 2>/dev/null; then
        echo "✅ $name: BUG DETECTED!"
        grep -A5 -B5 "bug\|Fund Loss\|Price Manipulation" "backtest_results/${name}_aggressive.log" | tail -20
    else
        echo "❌ $name: No bug found in ${timeout}s"
    fi
    
    # Show performance metrics
    echo "📊 Performance:"
    grep -E "exec/sec|corpus|coverage" "backtest_results/${name}_aggressive.log" | tail -5
    echo ""
}

# Run all tests from backtesting.md
echo "🏃 Running BSC Backtests with AGGRESSIVE settings..."
echo ""

# BEGO - Block 22315679 (Fund Loss, should find in ~18s)
run_test "BEGO" "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972" 22315679 60

# LPC - Block 19852596 (Fund Loss, should find in ~4s)
run_test "LPC" "0x1e813fa05739bf145c1f182cb950da7af046778d,0x1E813fA05739Bf145c1F182CB950dA7af046778d,0x2ecD8Ce228D534D8740617673F31b7541f6A0099,0xcfb7909b7eb27b71fdc482a2883049351a1749d7" 19852596 60

# RES02 - Block 21948016 (Price Manipulation, should find in ~2s)
run_test "RES02" "0x55d398326f99059fF775485246999027B3197955,0xD7B7218D778338Ea05f5Ecce82f86D365E25dBCE,0x05ba2c512788bd95cd6D61D3109c53a14b01c82A,0x1B214e38C5e861c56e12a69b6BAA0B45eFe5C8Eb,0xecCD8B08Ac3B587B7175D40Fb9C60a20990F8D21,0xeccd8b08ac3b587b7175d40fb9c60a20990f8d21,0x04C0f31C0f59496cf195d2d7F1dA908152722DE7,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c" 21948016 60

# SEAMAN - Block 23467515 (Fund Loss, should find in ~3s)
run_test "SEAMAN" "0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e" 23467515 60

# BIGFI - Block 26685503 (Price Manipulation, should find in ~8m31s)
run_test "BIGFI" "0x55d398326f99059fF775485246999027B3197955,0x28ec0B36F0819ecB5005cAB836F4ED5a2eCa4D13,0xd3d4B46Db01C006Fb165879f343fc13174a1cEeB,0xA269556EdC45581F355742e46D2d722c5F3f551a" 26685503 60

echo ""
echo "🏁 AGGRESSIVE Backtest completed!"
echo ""
echo "📈 Performance Summary:"
grep "exec/sec" backtest_results/*_aggressive.log 2>/dev/null | tail -10

echo ""
echo "🎯 Bug Detection Summary:"
for test in BEGO LPC RES02 SEAMAN BIGFI; do
    if grep -q "Found bug\|Fund Loss\|Price Manipulation" "backtest_results/${test}_aggressive.log" 2>/dev/null; then
        echo "✅ $test: BUG FOUND"
    else
        echo "❌ $test: No bug detected"
    fi
done

echo ""
echo "📊 Detailed logs available in backtest_results/"