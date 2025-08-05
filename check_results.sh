#!/bin/bash

echo "📊 Comprehensive Backtest Results"
echo "================================"
echo ""

for name in BEGO RES02 LPC AES Novo HEALTH Seaman CFC ROI; do
    if [ -f "backtest_results/comprehensive/${name}.log" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📍 $name"
        
        # Check if vulnerability found
        if grep -q "Found vulnerabilities\|objectives: [1-9]" "backtest_results/comprehensive/${name}.log" 2>/dev/null; then
            echo "✅ VULNERABILITY FOUND!"
            echo ""
            echo "Details:"
            grep -B2 -A10 "Fund Loss\|Reentrancy\|typed_bug\|Balance Drain\|Access Control" "backtest_results/comprehensive/${name}.log" | head -15
        else
            # Check if test completed
            if grep -q "Test aborted" "backtest_results/comprehensive/${name}.log" 2>/dev/null || \
               tail -1 "backtest_results/comprehensive/${name}.log" | grep -q "run time: 0h-4m-5[0-9]s\|run time: 0h-5m" 2>/dev/null; then
                echo "❌ No vulnerability found (test completed)"
                tail -3 "backtest_results/comprehensive/${name}.log" | grep -E "Stats|exec/sec|corpus"
            else
                # Still running
                RUNTIME=$(grep "run time:" "backtest_results/comprehensive/${name}.log" 2>/dev/null | tail -1 | grep -oE "0h-[0-9]+m-[0-9]+s")
                RATE=$(grep "exec/sec" "backtest_results/comprehensive/${name}.log" 2>/dev/null | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
                CORPUS=$(grep "corpus:" "backtest_results/comprehensive/${name}.log" 2>/dev/null | tail -1 | grep -oE "corpus: [0-9]+" | grep -oE "[0-9]+$")
                echo "⏳ Still running... (Runtime: ${RUNTIME:-unknown}, Rate: ${RATE:-0} exec/sec, Corpus: ${CORPUS:-0})"
            fi
        fi
        echo ""
    else
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "📍 $name"
        echo "⏸️  Not started yet"
        echo ""
    fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📈 Summary:"
SUCCESS=$(grep -l "Found vulnerabilities\|objectives: [1-9]" backtest_results/comprehensive/*.log 2>/dev/null | grep -v main.log | wc -l)
TOTAL=$(ls backtest_results/comprehensive/*.log 2>/dev/null | grep -v main.log | wc -l)
echo "Vulnerabilities found: $SUCCESS/$TOTAL"