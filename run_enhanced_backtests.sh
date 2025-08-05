#!/bin/bash

echo "🚀 Running BSC Backtests with Enhanced ItyFuzz"
echo "============================================="
echo ""
echo "Features:"
echo "  ✅ 400x performance optimization"
echo "  ✅ Lowered profit threshold (0.0001 ETH)"
echo "  ✅ Enhanced reentrancy detection"
echo "  ✅ Balance drain oracle"
echo ""

# Configuration
API_KEY="${BSC_ETHERSCAN_API_KEY}"
RPC_URL="https://rpc.ankr.com/bsc"

# Test function
test_vulnerability() {
    local name=$1
    local target=$2
    local block=$3
    local expected_time=$4
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 Testing $name"
    echo "   Target: $target"
    echo "   Block: $block"
    echo "   Expected: $expected_time"
    echo ""
    
    # Create output directory
    mkdir -p "backtest_results/enhanced"
    
    # Run the test
    START_TIME=$(date +%s)
    
    timeout 300s ./target/release/ityfuzz evm \
        -t "$target" \
        -c bsc \
        --onchain-block-number "$block" \
        -f \
        --panic-on-bug \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$RPC_URL" \
        --detectors "erc20,balance_drain" \
        --work-dir "backtest_results/enhanced/${name}" \
        > "backtest_results/enhanced/${name}.log" 2>&1
    
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    # Check results
    if grep -q "Fund Loss\|typed_bug\|Balance Drain\|objectives: [1-9]" "backtest_results/enhanced/${name}.log"; then
        echo "✅ FOUND vulnerability in ${ELAPSED}s (expected: $expected_time)"
        echo ""
        echo "Bug details:"
        grep -A10 "Fund Loss\|typed_bug\|Balance Drain" "backtest_results/enhanced/${name}.log" | head -15
    else
        echo "❌ No vulnerability found in ${ELAPSED}s"
        echo "Final stats:"
        tail -5 "backtest_results/enhanced/${name}.log" | grep -E "Stats|exec/sec"
    fi
    
    echo ""
}

# Run tests
echo "Starting backtests..."
echo ""

# BEGO - Fund Loss (18s)
test_vulnerability "BEGO" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972" \
    "22315679" \
    "18s"

# RES02 - Reentrancy (141s)
test_vulnerability "RES02" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5c811d550E421bcc37cb2097AF5b40Eb62Cf6d7A,0xA0ED3C520dC0632657AD2EaaF19E26C4fD431a84" \
    "23695904" \
    "141s"

# LPC - Fund Loss (135s)
test_vulnerability "LPC" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x55d398326f99059fF775485246999027B3197955,0x2dEc3B6AdFCCE085F31C0fdba870Fb4344d35EF7,0x9ca1c80b7B4789382d3081b77a5add91fD638407" \
    "16008280" \
    "135s"

# Seaman - Access Control (43s)
test_vulnerability "Seaman" \
    "0x6bc9b4976ba6f8C9574326375204eE469993D038,0x7B86b0836f3454e50C6F6a190cd692bB17da1928" \
    "22142525" \
    "43s"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary"
echo ""

# Count successes
SUCCESS_COUNT=$(grep -l "FOUND vulnerability" backtest_results/enhanced/*.log 2>/dev/null | wc -l)
TOTAL_COUNT=4

echo "✅ Vulnerabilities found: $SUCCESS_COUNT/$TOTAL_COUNT"
echo ""

# Show performance stats
echo "Performance stats:"
for log in backtest_results/enhanced/*.log; do
    if [ -f "$log" ]; then
        name=$(basename "$log" .log)
        rate=$(grep "exec/sec" "$log" | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        if [ -n "$rate" ]; then
            echo "  $name: ${rate} exec/sec"
        fi
    fi
done

echo ""
echo "✅ Backtest complete!"