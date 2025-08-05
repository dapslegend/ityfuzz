#!/bin/bash

echo "🚀 Testing Improved ItyFuzz with Enhanced Oracles"
echo "================================================"
echo ""

# Start Anvil
echo "🔗 Starting Anvil..."
anvil --port 8545 --chain-id 31337 --accounts 10 --balance 10000 > /tmp/anvil_test.log 2>&1 &
ANVIL_PID=$!

sleep 5

# Deploy vulnerable contract
echo "📄 Deploying VulnerableVault..."
DEPLOY_OUTPUT=$(forge create /workspace/VulnerableVault.sol:VulnerableVault \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast 2>&1)

CONTRACT=$(echo "$DEPLOY_OUTPUT" | grep -oE "Deployed to: 0x[a-fA-F0-9]{40}" | cut -d' ' -f3)
echo "✅ Contract deployed at: $CONTRACT"

# Deposit funds
echo "💰 Depositing 10 ETH..."
cast send $CONTRACT --value 10ether \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 > /dev/null

BLOCK=$(cast block-number --rpc-url http://localhost:8545)
echo "📦 Starting at block: $BLOCK"
echo ""

# Run improved ItyFuzz
echo "🎯 Running Improved ItyFuzz (5 minute test)..."
echo "Features:"
echo "  - ✅ Lowered profit threshold (0.0001 ETH)"
echo "  - ✅ Enhanced reentrancy detection with profit tracking"
echo "  - ✅ Aggressive performance optimizations"
echo ""

cd /workspace
timeout 300s ./target/release/ityfuzz evm \
    -t "$CONTRACT" \
    --onchain-block-number "$BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --onchain-chain-id 31337 \
    --work-dir "backtest_results/improved_test" \
    2>&1 | tee "backtest_results/improved_test.log" &

ITYFUZZ_PID=$!

# Monitor progress
echo "⏳ Monitoring..."
START_TIME=$(date +%s)

while kill -0 $ITYFUZZ_PID 2>/dev/null; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    # Check for vulnerabilities
    if grep -q "Reentrancy vulnerability\|Fund Loss\|PROFITABLE" "backtest_results/improved_test.log" 2>/dev/null; then
        echo ""
        echo "🎉 VULNERABILITY FOUND after $((ELAPSED / 60))m $((ELAPSED % 60))s!"
        echo ""
        grep -A20 "vulnerability\|Fund Loss\|PROFITABLE" "backtest_results/improved_test.log" | head -30
        kill $ITYFUZZ_PID 2>/dev/null
        break
    fi
    
    # Show stats every 30s
    if [ $((ELAPSED % 30)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        EXEC=$(grep "executions:" backtest_results/improved_test.log 2>/dev/null | tail -1 | grep -oE "executions: [0-9]+" | grep -oE "[0-9]+")
        RATE=$(grep "exec/sec" backtest_results/improved_test.log 2>/dev/null | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?")
        if [ -n "$EXEC" ]; then
            echo "[$((ELAPSED / 60))m $((ELAPSED % 60))s] Executions: $EXEC | Rate: ${RATE:-0} exec/sec"
        fi
    fi
    
    sleep 1
done

# Final check
echo ""
if ! grep -q "vulnerability\|Fund Loss" "backtest_results/improved_test.log" 2>/dev/null; then
    echo "❌ No vulnerability found in 5 minutes"
    echo ""
    echo "Final stats:"
    tail -20 backtest_results/improved_test.log | grep -E "Stats|objectives|Coverage" | tail -5
else
    echo "✅ Test completed successfully!"
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
kill $ANVIL_PID 2>/dev/null
pkill anvil 2>/dev/null
echo "✅ Done!"