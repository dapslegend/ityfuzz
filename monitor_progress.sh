#!/bin/bash

echo "📊 Monitoring ItyFuzz progress..."
echo ""

START_TIME=$(date +%s)
FOUND=false

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    # Check if vulnerability found
    if grep -q "Found vulnerabilities\|typed_bug\|Fund Loss" backtest_results/vault_30min.log 2>/dev/null; then
        echo ""
        echo "🎉 VULNERABILITY FOUND after $((ELAPSED / 60))m $((ELAPSED % 60))s!"
        echo ""
        grep -A30 "Found vulnerabilities" backtest_results/vault_30min.log | head -40
        FOUND=true
        break
    fi
    
    # Get stats
    EXEC=$(grep "executions:" backtest_results/vault_30min.log 2>/dev/null | tail -1 | grep -oE "executions: [0-9]+" | grep -oE "[0-9]+")
    RATE=$(grep "exec/sec" backtest_results/vault_30min.log 2>/dev/null | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?")
    CORPUS=$(grep "corpus:" backtest_results/vault_30min.log 2>/dev/null | tail -1 | grep -oE "corpus: [0-9]+" | grep -oE "[0-9]+")
    OBJECTIVES=$(grep "objectives:" backtest_results/vault_30min.log 2>/dev/null | tail -1 | grep -oE "objectives: [0-9]+" | grep -oE "[0-9]+")
    
    # Display progress
    printf "\r[%dm %ds] Executions: %s | Rate: %s exec/sec | Corpus: %s | Objectives: %s" \
        $((ELAPSED / 60)) $((ELAPSED % 60)) \
        "${EXEC:-0}" "${RATE:-0}" "${CORPUS:-0}" "${OBJECTIVES:-0}"
    
    # Check if process is still running
    if ! pgrep -f "ityfuzz.*vault_30min" > /dev/null; then
        echo ""
        echo ""
        echo "Process finished."
        break
    fi
    
    sleep 2
done

if [ "$FOUND" = false ]; then
    echo ""
    echo ""
    echo "Final check..."
    if grep -q "Found vulnerabilities" backtest_results/vault_30min.log 2>/dev/null; then
        echo "✅ Vulnerability found!"
        grep -A20 "Found vulnerabilities" backtest_results/vault_30min.log
    else
        echo "❌ No vulnerability found"
        echo ""
        echo "Final stats:"
        tail -20 backtest_results/vault_30min.log | grep -E "Stats|Coverage|objectives"
    fi
fi