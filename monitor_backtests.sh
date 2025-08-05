#!/bin/bash

echo "📊 Monitoring Comprehensive Backtests"
echo "===================================="
echo ""

while true; do
    clear
    echo "📊 Backtest Progress Monitor"
    echo "============================"
    echo "Time: $(date)"
    echo ""
    
    # Check each test
    for name in BEGO RES02 LPC AES Novo HEALTH Seaman CFC ROI; do
        if [ -f "backtest_results/comprehensive/${name}.log" ]; then
            # Check if vulnerability found
            if grep -q "Found vulnerabilities\|objectives: [1-9]" "backtest_results/comprehensive/${name}.log" 2>/dev/null; then
                echo "✅ $name: VULNERABILITY FOUND!"
                grep "Fund Loss\|Reentrancy\|typed_bug" "backtest_results/comprehensive/${name}.log" | head -1
            else
                # Show progress
                EXEC=$(grep "executions:" "backtest_results/comprehensive/${name}.log" 2>/dev/null | tail -1 | grep -oE "executions: [0-9]+" | grep -oE "[0-9]+")
                RATE=$(grep "exec/sec" "backtest_results/comprehensive/${name}.log" 2>/dev/null | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
                if [ -n "$EXEC" ]; then
                    echo "⏳ $name: Running... (${EXEC:-0} execs, ${RATE:-0} exec/sec)"
                else
                    echo "⏸️  $name: Not started yet"
                fi
            fi
        else
            echo "⏸️  $name: Waiting..."
        fi
    done
    
    echo ""
    echo "Press Ctrl+C to stop monitoring"
    sleep 5
done