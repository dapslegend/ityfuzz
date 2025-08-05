#!/bin/bash

echo "🐅 TIGER MODE - Ultra Aggressive ItyFuzz 🐅"
echo "=========================================="
echo ""
echo "Tiger tweaks:"
echo "  🔥 Running with proper flags from documentation"
echo "  🔥 Each test runs separately"  
echo "  🔥 30 second timeouts (more realistic)"
echo ""

# TIGER settings
export BSC_ETHERSCAN_API_KEY="${BSC_ETHERSCAN_API_KEY:-TR24XDQF35QCNK9PZBV8XEH2XRSWTPWFWT}"
export RUST_LOG=error
TIMEOUT=30  # More realistic timeout

# Create results directory
mkdir -p "backtest_results/tiger_proper"

# Tiger function
run_test() {
    local name=$1
    local target=$2
    local block=$3
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎯 Hunting: $name"
    echo "   Target: $target"
    echo "   Block: $block"
    echo -n "   Status: "
    
    # Run with timeout
    timeout $TIMEOUT ityfuzz evm \
        -t "$target" \
        -c bsc \
        --onchain-block-number "$block" \
        -f -i -p \
        --onchain-etherscan-api-key "$BSC_ETHERSCAN_API_KEY" \
        > "backtest_results/tiger_proper/${name}.log" 2>&1
    
    # Check results
    if grep -q "Found vulnerabilities" "backtest_results/tiger_proper/${name}.log" 2>/dev/null; then
        echo "✅ CAUGHT!"
        # Extract details
        grep -A5 "Found vulnerabilities" "backtest_results/tiger_proper/${name}.log" | head -10
    elif grep -q "thread 'main' panicked" "backtest_results/tiger_proper/${name}.log" 2>/dev/null; then
        echo "❌ ERROR"
        grep -A2 "thread 'main' panicked" "backtest_results/tiger_proper/${name}.log"
    else
        echo "❌ missed"
    fi
    echo ""
}

echo "🐅 TIGER HUNT BEGINS!"
echo ""

# Run tests based on documentation
run_test "SEAMAN" \
    "0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e" \
    "23467515"

run_test "RES02" \
    "0x55d398326f99059fF775485246999027B3197955,0xD7B7218D778338Ea05f5Ecce82f86D365E25dBCE,0x05ba2c512788bd95cd6D61D3109c53a14b01c82A,0x1B214e38C5e861c56e12a69b6BAA0B45eFe5C8Eb,0xecCD8B08Ac3B587B7175D40Fb9C60a20990F8D21,0xeccd8b08ac3b587b7175d40fb9c60a20990f8d21,0x04C0f31C0f59496cf195d2d7F1dA908152722DE7,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c" \
    "21948016"

run_test "LPC" \
    "0x1e813fa05739bf145c1f182cb950da7af046778d,0x1E813fA05739Bf145c1F182CB950dA7af046778d,0x2ecD8Ce228D534D8740617673F31b7541f6A0099,0xcfb7909b7eb27b71fdc482a2883049351a1749d7" \
    "19852596"

run_test "BEGO" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972" \
    "22315679"

run_test "BBOX" \
    "0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c" \
    "23106506"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐅 TIGER HUNT COMPLETE!"
echo ""

# Count successful hunts
KILLS=0
for log in backtest_results/tiger_proper/*.log; do
    if [ -f "$log" ] && grep -q "Found vulnerabilities" "$log" 2>/dev/null; then
        KILLS=$((KILLS + 1))
    fi
done

echo "🏆 Total kills: $KILLS"
echo ""
echo "🐅 The tiger is satisfied! 🐅"