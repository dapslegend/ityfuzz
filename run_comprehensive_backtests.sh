#!/bin/bash

echo "🚀 Comprehensive BSC Backtests with ALL Detectors"
echo "================================================="
echo ""
echo "Configuration:"
echo "  ✅ ALL detectors enabled"
echo "  ✅ Extended timeouts (5 minutes each)"
echo "  ✅ Enhanced ItyFuzz with optimizations"
echo ""

# Configuration
API_KEY="${BSC_ETHERSCAN_API_KEY}"
RPC_URL="https://rpc.ankr.com/bsc"

# Create results directory
mkdir -p "backtest_results/comprehensive"

# Test function with enhanced monitoring
test_vulnerability() {
    local name=$1
    local target=$2
    local block=$3
    local expected_type=$4
    local timeout=${5:-300}  # Default 5 minutes
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 Testing $name"
    echo "   Target: $target"
    echo "   Block: $block"
    echo "   Expected: $expected_type"
    echo "   Timeout: ${timeout}s"
    echo ""
    
    # Run the test
    START_TIME=$(date +%s)
    
    timeout ${timeout}s ./target/release/ityfuzz evm \
        -t "$target" \
        -c bsc \
        --onchain-block-number "$block" \
        -f \
        --panic-on-bug \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$RPC_URL" \
        --detectors "all" \
        --work-dir "backtest_results/comprehensive/${name}" \
        > "backtest_results/comprehensive/${name}.log" 2>&1 &
    
    PID=$!
    
    # Monitor progress
    echo "⏳ Monitoring..."
    FOUND=false
    
    while kill -0 $PID 2>/dev/null; do
        CURRENT_TIME=$(date +%s)
        ELAPSED=$((CURRENT_TIME - START_TIME))
        
        # Check for any vulnerability
        if grep -q "Found vulnerabilities\|objectives: [1-9]\|Fund Loss\|Reentrancy\|Balance Drain\|Access Control\|Arbitrary" "backtest_results/comprehensive/${name}.log" 2>/dev/null; then
            FOUND=true
            echo ""
            echo "✅ VULNERABILITY FOUND in ${ELAPSED}s!"
            kill $PID 2>/dev/null
            break
        fi
        
        # Progress update every 10 seconds
        if [ $((ELAPSED % 10)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
            RATE=$(grep "exec/sec" "backtest_results/comprehensive/${name}.log" 2>/dev/null | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
            printf "\r[%3ds] Rate: %-8s" $ELAPSED "${RATE:-...}"
        fi
        
        sleep 1
    done
    
    wait $PID 2>/dev/null
    END_TIME=$(date +%s)
    TOTAL_ELAPSED=$((END_TIME - START_TIME))
    
    echo ""
    
    # Check final results
    if [ "$FOUND" = true ] || grep -q "Found vulnerabilities\|objectives: [1-9]" "backtest_results/comprehensive/${name}.log" 2>/dev/null; then
        echo "✅ SUCCESS: Found vulnerability in ${TOTAL_ELAPSED}s"
        echo ""
        echo "Details:"
        grep -B5 -A20 "Found vulnerabilities\|Fund Loss\|Reentrancy\|Balance Drain\|typed_bug" "backtest_results/comprehensive/${name}.log" | head -30
    else
        echo "❌ No vulnerability found in ${TOTAL_ELAPSED}s"
        echo "Final stats:"
        tail -5 "backtest_results/comprehensive/${name}.log" | grep -E "Stats|exec/sec|corpus|objectives"
    fi
    
    echo ""
}

# Run all tests
echo "Starting comprehensive backtests..."
echo ""

# BEGO - Fund Loss (previously 18s)
test_vulnerability "BEGO" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972" \
    "22315679" \
    "Fund Loss"

# RES02 - Reentrancy (previously 141s)
test_vulnerability "RES02" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5c811d550E421bcc37cb2097AF5b40Eb62Cf6d7A,0xA0ED3C520dC0632657AD2EaaF19E26C4fD431a84" \
    "23695904" \
    "Reentrancy"

# LPC - Fund Loss (previously 135s)
test_vulnerability "LPC" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x55d398326f99059fF775485246999027B3197955,0x2dEc3B6AdFCCE085F31C0fdba870Fb4344d35EF7,0x9ca1c80b7B4789382d3081b77a5add91fD638407" \
    "16008280" \
    "Fund Loss"

# AES - Price Manipulation (50s)
test_vulnerability "AES" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0xdDc0CFF76bcC0ee14c3e73aF630C029fe020F907" \
    "15307521" \
    "Price Manipulation"

# Novo - Reentrancy (49s)
test_vulnerability "Novo" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0xB76a913e21bA068468215B0e35C892542b2Fa9C2" \
    "28073403" \
    "Reentrancy"

# HEALTH - Access Control (170s)
test_vulnerability "HEALTH" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x32B166e082993Af6598a89397E82e123ca44e74E,0xF375709DbdE84D800642168c2e8bA751368e8D32" \
    "18170716" \
    "Access Control"

# Seaman - Access Control (43s) - Give it more time
test_vulnerability "Seaman" \
    "0x6bc9b4976ba6f8C9574326375204eE469993D038,0x7B86b0836f3454e50C6F6a190cd692bB17da1928" \
    "22142525" \
    "Access Control" \
    "600"  # 10 minutes

# CFC - Fund Loss (181s)
test_vulnerability "CFC" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x55d398326f99059fF775485246999027B3197955,0x4Ad2A83dF23e5F5e1C31C73bcbAD70a45f6C9479" \
    "27012846" \
    "Fund Loss"

# ROI - Incorrect Calculation (12s)
test_vulnerability "ROI" \
    "0x4cbd19b3Db72E713cD32Ce1De5be01b3B4dCa0EA,0xF8c76eEa8cBb03A65F07ACD4027540B5059B8fC0" \
    "29135693" \
    "Incorrect Calculation"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Final Summary"
echo ""

# Count successes
SUCCESS_COUNT=0
TOTAL_COUNT=0

for log in backtest_results/comprehensive/*.log; do
    if [ -f "$log" ]; then
        TOTAL_COUNT=$((TOTAL_COUNT + 1))
        if grep -q "Found vulnerabilities\|objectives: [1-9]" "$log" 2>/dev/null; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            name=$(basename "$log" .log)
            echo "✅ $name: FOUND"
        else
            name=$(basename "$log" .log)
            echo "❌ $name: Not found"
        fi
    fi
done

echo ""
echo "Total: $SUCCESS_COUNT/$TOTAL_COUNT vulnerabilities detected"
echo ""

# Show performance comparison
echo "Performance stats:"
for log in backtest_results/comprehensive/*.log; do
    if [ -f "$log" ]; then
        name=$(basename "$log" .log)
        rate=$(grep "exec/sec" "$log" | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        if [ -n "$rate" ]; then
            echo "  $name: ${rate} exec/sec"
        fi
    fi
done

echo ""
echo "✅ Comprehensive backtest complete!"
echo "📝 Logs saved in: backtest_results/comprehensive/"