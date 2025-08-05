#!/bin/bash

echo "🐅 TIGER MODE - Ultra Aggressive ItyFuzz 🐅"
echo "=========================================="
echo ""
echo "Tiger tweaks:"
echo "  🔥 0.000001 ETH threshold (catch EVERYTHING)"
echo "  🔥 Each oracle runs separately"  
echo "  🔥 15 second timeouts"
echo "  🔥 Maximum parallelism"
echo ""

# TIGER settings
export RUST_LOG=error
export RAYON_NUM_THREADS=32
TIMEOUT=15  # 15 second timeout as requested

# Configuration
API_KEY="${BSC_ETHERSCAN_API_KEY}"
RPC_URL="https://rpc.ankr.com/bsc"

# Create results directory
mkdir -p "backtest_results/tiger"

# Tiger function - aggressive and fast
tiger_hunt() {
    local name=$1
    local target=$2
    local block=$3
    local oracle=$4
    
    echo -n "🐅 $name [$oracle]: "
    
    # Quick strike with timeout
    timeout $TIMEOUT ./target/release/ityfuzz evm \
        -t "$target" \
        -c bsc \
        --onchain-block-number "$block" \
        -f \
        --panic-on-bug \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$RPC_URL" \
        --detectors "$oracle" \
        --work-dir "backtest_results/tiger/${name}_${oracle//,/_}" \
        > "backtest_results/tiger/${name}_${oracle//,/_}.log" 2>&1
    
    # Quick check
    if grep -q "Found vulnerabilities" "backtest_results/tiger/${name}_${oracle//,/_}.log" 2>/dev/null; then
        PROFIT=$(grep -oE "[0-9]+\.[0-9]+ ETH" "backtest_results/tiger/${name}_${oracle//,/_}.log" | head -1)
        echo "✅ CAUGHT! ${PROFIT:-found}"
    else
        echo "❌ missed"
    fi
}

echo "🐅 TIGER HUNT BEGINS!"
echo ""

# Test configurations
TESTS=(
    "BEGO,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972,22315679"
    "BBOX,0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c,23106506"
    "FAPEN,0xf3f1abae8bfeca054b330c379794a7bf84988228,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0xf3F1aBae8BfeCA054B330C379794A7bf84988228,28637846"
    "SEAMAN,0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e,23467515"
)

# All oracle types
ORACLES=(
    "erc20"
    "reentrancy"
    "erc20,reentrancy"
    "arbitrary_call"
    "typed_bug"
    "erc20,balance_drain"
    "all"
)

# Run tests in parallel batches
for test_data in "${TESTS[@]}"; do
    IFS=',' read -r name addresses block <<< "$test_data"
    # Remove name from addresses
    target="${test_data#*,}"
    target="${target%,*}"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎯 Hunting: $name"
    
    # Run all oracles in parallel for this target
    for oracle in "${ORACLES[@]}"; do
        tiger_hunt "$name" "$target" "$block" "$oracle" &
    done
    
    # Wait for this batch to complete
    wait
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐅 TIGER HUNT COMPLETE!"
echo ""

# Count kills
KILLS=0
for log in backtest_results/tiger/*.log; do
    if [ -f "$log" ] && grep -q "Found vulnerabilities" "$log" 2>/dev/null; then
        KILLS=$((KILLS + 1))
    fi
done

echo "🏆 Total kills: $KILLS"
echo ""

# Show successful hunts
echo "Successful hunts:"
for log in backtest_results/tiger/*.log; do
    if [ -f "$log" ] && grep -q "Found vulnerabilities" "$log" 2>/dev/null; then
        name=$(basename "$log" .log)
        profit=$(grep -oE "[0-9]+\.[0-9]+ ETH" "$log" | head -1)
        echo "  ✅ $name: ${profit:-found}"
    fi
done

echo ""
echo "🐅 The tiger is satisfied! 🐅"