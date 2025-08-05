#!/bin/bash

echo "🚀 Optimized ItyFuzz Backtests"
echo "=============================="
echo ""
echo "Using performance optimizations:"
echo "  ✓ Smaller corpus (50)"
echo "  ✓ Higher power multiplier (32)"
echo "  ✓ Reduced logging"
echo "  ✓ More threads"
echo ""

# Performance settings
export RUST_LOG=error
export RAYON_NUM_THREADS=8

# Configuration
API_KEY="${BSC_ETHERSCAN_API_KEY}"
RPC_URL="https://rpc.ankr.com/bsc"  # Fast RPC

# Create results directory
mkdir -p "backtest_results/optimized"

# Test function with optimizations
test_vuln() {
    local name=$1
    local target=$2
    local block=$3
    local expected=$4
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎯 Testing $name"
    echo "   Expected: $expected"
    
    START_TIME=$(date +%s)
    
    timeout 300s ./target/release/ityfuzz evm \
        -t "$target" \
        -c bsc \
        --onchain-block-number "$block" \
        -f \
        --panic-on-bug \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$RPC_URL" \
        --detectors "erc20" \
        --corpus-size 50 \
        --power-multiplier 32 \
        --work-dir "backtest_results/optimized/${name}" \
        > "backtest_results/optimized/${name}.log" 2>&1
    
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    # Check results
    if grep -q "Found vulnerabilities" "backtest_results/optimized/${name}.log" 2>/dev/null; then
        echo "✅ FOUND in ${ELAPSED}s!"
        PROFIT=$(grep -oE "[0-9]+\.[0-9]+ ETH" "backtest_results/optimized/${name}.log" | head -1)
        echo "   Profit: $PROFIT"
        # Check objectives
        OBJ=$(grep "objectives:" "backtest_results/optimized/${name}.log" | tail -1 | grep -oE "objectives: [0-9]+" | grep -oE "[0-9]+$")
        echo "   Objectives: ${OBJ:-0}"
    else
        echo "❌ Not found in ${ELAPSED}s"
        RATE=$(grep "exec/sec" "backtest_results/optimized/${name}.log" | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        echo "   Rate: ${RATE:-0} exec/sec"
    fi
    echo ""
}

echo "Running optimized backtests..."
echo ""

# Test with CORRECT configurations
test_vuln "BEGO" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972" \
    "22315679" \
    "Fund Loss (18s)"

test_vuln "SEAMAN" \
    "0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e" \
    "23467515" \
    "Fund Loss (3s)"

test_vuln "RES02" \
    "0x55d398326f99059fF775485246999027B3197955,0xD7B7218D778338Ea05f5Ecce82f86D365E25dBCE,0x05ba2c512788bd95cd6D61D3109c53a14b01c82A,0x1B214e38C5e861c56e12a69b6BAA0B45eFe5C8Eb,0xecCD8B08Ac3B587B7175D40Fb9C60a20990F8D21,0xeccd8b08ac3b587b7175d40fb9c60a20990f8d21,0x04C0f31C0f59496cf195d2d7F1dA908152722DE7,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c" \
    "21948016" \
    "Price Manipulation (2s)"

test_vuln "EGD" \
    "0x55d398326f99059fF775485246999027B3197955,0x202b233735bF743FA31abb8f71e641970161bF98,0xa361433E409Adac1f87CDF133127585F8a93c67d,0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE,0x34Bd6Dba456Bc31c2b3393e499fa10bED32a9370,0xc30808d9373093fbfcec9e026457c6a9dab706a7,0x34bd6dba456bc31c2b3393e499fa10bed32a9370,0x93c175439726797dcee24d08e4ac9164e88e7aee" \
    "20245522" \
    "Fund Loss (2s)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary"
echo ""

# Performance comparison
echo "Performance Stats:"
for log in backtest_results/optimized/*.log; do
    if [ -f "$log" ]; then
        name=$(basename "$log" .log)
        rate=$(grep "exec/sec" "$log" | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        if [ -n "$rate" ]; then
            echo "  $name: ${rate} exec/sec"
        fi
    fi
done

echo ""
echo "✅ Testing complete!"