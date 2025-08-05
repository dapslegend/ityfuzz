#!/bin/bash

echo "🔍 Extended Seaman Access Control Bug Test"
echo "========================================="
echo ""
echo "Running for 15 minutes to see if ItyFuzz can detect access control vulnerabilities"
echo ""

# Configuration
API_KEY="${BSC_ETHERSCAN_API_KEY}"
RPC_URL="https://rpc.ankr.com/bsc"

# Create output directory
mkdir -p "backtest_results/extended"

# Seaman contract details
TARGET="0x6bc9b4976ba6f8C9574326375204eE469993D038,0x7B86b0836f3454e50C6F6a190cd692bB17da1928"
BLOCK="22142525"

echo "📊 Contract: Seaman"
echo "🎯 Target: $TARGET"
echo "📦 Block: $BLOCK"
echo "⏱️  Timeout: 15 minutes (900s)"
echo ""

# Run the test
START_TIME=$(date +%s)
echo "🚀 Starting extended test..."

timeout 900s ./target/release/ityfuzz evm \
    -t "$TARGET" \
    -c bsc \
    --onchain-block-number "$BLOCK" \
    -f \
    --panic-on-bug \
    --onchain-etherscan-api-key "$API_KEY" \
    --onchain-url "$RPC_URL" \
    --detectors "all" \
    --work-dir "backtest_results/extended/seaman_long" \
    > "backtest_results/extended/seaman_long.log" 2>&1 &

PID=$!

# Monitor progress
echo "⏳ Monitoring progress..."
echo ""

while kill -0 $PID 2>/dev/null; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    MINUTES=$((ELAPSED / 60))
    SECONDS=$((ELAPSED % 60))
    
    # Check for any bug detection
    if grep -q "Fund Loss\|typed_bug\|Balance Drain\|objectives: [1-9]\|Access Control\|Arbitrary" "backtest_results/extended/seaman_long.log" 2>/dev/null; then
        echo ""
        echo "🎉 VULNERABILITY FOUND after ${MINUTES}m ${SECONDS}s!"
        echo ""
        echo "Bug details:"
        grep -B5 -A20 "Fund Loss\|typed_bug\|Balance Drain\|Access Control\|Arbitrary" "backtest_results/extended/seaman_long.log" | head -50
        kill $PID 2>/dev/null
        break
    fi
    
    # Progress update every 30 seconds
    if [ $((ELAPSED % 30)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        EXEC=$(grep "executions:" "backtest_results/extended/seaman_long.log" 2>/dev/null | tail -1 | grep -oE "executions: [0-9]+" | grep -oE "[0-9]+")
        RATE=$(grep "exec/sec" "backtest_results/extended/seaman_long.log" 2>/dev/null | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        CORPUS=$(grep "corpus:" "backtest_results/extended/seaman_long.log" 2>/dev/null | tail -1 | grep -oE "corpus: [0-9]+" | grep -oE "[0-9]+$")
        OBJECTIVES=$(grep "objectives:" "backtest_results/extended/seaman_long.log" 2>/dev/null | tail -1 | grep -oE "objectives: [0-9]+" | grep -oE "[0-9]+$")
        
        printf "[%2dm %2ds] Executions: %-10s | Rate: %-8s | Corpus: %-4s | Objectives: %s\n" \
            $MINUTES $SECONDS "${EXEC:-0}" "${RATE:-0}" "${CORPUS:-0}" "${OBJECTIVES:-0}"
    fi
    
    sleep 1
done

# Final results
END_TIME=$(date +%s)
TOTAL_ELAPSED=$((END_TIME - START_TIME))
TOTAL_MINUTES=$((TOTAL_ELAPSED / 60))
TOTAL_SECONDS=$((TOTAL_ELAPSED % 60))

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Final Results"
echo ""

if ! grep -q "objectives: [1-9]\|Fund Loss\|typed_bug" "backtest_results/extended/seaman_long.log" 2>/dev/null; then
    echo "❌ No vulnerability detected after ${TOTAL_MINUTES}m ${TOTAL_SECONDS}s"
    echo ""
    echo "Final statistics:"
    tail -10 "backtest_results/extended/seaman_long.log" | grep -E "Stats|Coverage|corpus|objectives"
    
    echo ""
    echo "💡 Analysis:"
    echo "- Access control bugs may need specific oracle configurations"
    echo "- The 'arbitrary_call' detector might help but wasn't sufficient"
    echo "- May need custom oracle for role-based vulnerabilities"
else
    echo "✅ Vulnerability found in ${TOTAL_MINUTES}m ${TOTAL_SECONDS}s!"
    echo ""
    # Show what was found
    grep -A30 "Found vulnerabilities\|Fund Loss\|typed_bug" "backtest_results/extended/seaman_long.log" | head -50
fi

echo ""
echo "📝 Log saved to: backtest_results/extended/seaman_long.log"
echo "✅ Test complete!"