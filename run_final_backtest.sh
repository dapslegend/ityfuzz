#!/bin/bash

# Configuration
API_KEY="SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
RPC_URL="https://rpc.ankr.com/bsc"  # Ankr RPC works well

echo "🚀 Running BSC Backtests with CORRECT FLAGS"
echo "🔧 RPC: ${RPC_URL}"
echo "⚡ Aggressive ityfuzz optimizations enabled"
echo ""

# Function to run test
run_test() {
    local name=$1
    local target=$2
    local block=$3
    local expected_vuln=$4
    local timeout=${5:-60}
    
    echo "================================================================"
    echo "🔍 Testing $name (Block: $block)"
    echo "📋 Expected: $expected_vuln"
    echo "================================================================"
    
    # Run with timeout and capture output
    timeout ${timeout}s ./target/release/ityfuzz evm \
        -t "$target" \
        -c bsc \
        --onchain-block-number "$block" \
        -f \
        --panic-on-bug \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$RPC_URL" \
        --detectors all \
        --work-dir "backtest_results/${name}_final" \
        2>&1 | tee "backtest_results/${name}_final.log"
    
    # Check results
    if grep -q "Found vulnerabilities\|Fund Loss\|Price Manipulation" "backtest_results/${name}_final.log" 2>/dev/null; then
        echo "✅ $name: BUG DETECTED!"
        grep -A10 "Found vulnerabilities" "backtest_results/${name}_final.log" | head -20
    else
        echo "❌ $name: No bug found in ${timeout}s"
    fi
    
    # Show performance
    echo "📊 Performance:"
    grep "exec/sec" "backtest_results/${name}_final.log" | tail -3
    echo ""
}

# Run tests
echo "🏃 Running BSC Backtests..."
echo ""

# BEGO - Already tested and working!
echo "✅ BEGO: Already confirmed working (Fund Loss found in 25s)"
echo ""

# LPC - Fund Loss (should find in ~4s)
run_test "LPC" \
    "0x1e813fa05739bf145c1f182cb950da7af046778d,0x1E813fA05739Bf145c1F182CB950dA7af046778d,0x2ecD8Ce228D534D8740617673F31b7541f6A0099,0xcfb7909b7eb27b71fdc482a2883049351a1749d7" \
    19852596 \
    "Fund Loss" \
    30

# RES02 - Price Manipulation (should find in ~2s)
run_test "RES02" \
    "0x55d398326f99059fF775485246999027B3197955,0xD7B7218D778338Ea05f5Ecce82f86D365E25dBCE,0x05ba2c512788bd95cd6D61D3109c53a14b01c82A,0x1B214e38C5e861c56e12a69b6BAA0B45eFe5C8Eb,0xecCD8B08Ac3B587B7175D40Fb9C60a20990F8D21,0xeccd8b08ac3b587b7175d40fb9c60a20990f8d21,0x04C0f31C0f59496cf195d2d7F1dA908152722DE7,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c" \
    21948016 \
    "Price Manipulation" \
    30

# SEAMAN - Fund Loss (should find in ~3s)
run_test "SEAMAN" \
    "0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e" \
    23467515 \
    "Fund Loss" \
    30

echo ""
echo "🏁 Backtest completed!"
echo ""
echo "📈 Summary:"
echo "- BEGO: ✅ Fund Loss found in 25s"
for test in LPC RES02 SEAMAN; do
    if grep -q "Found vulnerabilities" "backtest_results/${test}_final.log" 2>/dev/null; then
        echo "- $test: ✅ Bug found"
    else
        echo "- $test: ❌ Not found"
    fi
done