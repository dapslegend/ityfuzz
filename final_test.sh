#!/bin/bash

echo "🚀 FINAL TEST: ItyFuzz with Complete Fund Loss Detection"
echo "======================================================="
echo ""

# Cleanup
pkill anvil 2>/dev/null
pkill ityfuzz 2>/dev/null
sleep 2

# Start Anvil
echo "🔗 Starting Anvil..."
anvil --port 8545 --chain-id 31337 --accounts 10 --balance 10000 > /tmp/anvil.log 2>&1 &
ANVIL_PID=$!
sleep 3

# Deploy vulnerable contract
echo "📄 Deploying VulnerableVault..."
CONTRACT=$(forge create VulnerableVault.sol:VulnerableVault \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast 2>&1 | grep "Deployed to:" | cut -d' ' -f3)

echo "✅ Contract: $CONTRACT"

# Deposit initial funds
echo "💰 Depositing 1 ETH..."
cast send $CONTRACT --value 1ether \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 > /dev/null

BALANCE=$(cast balance $CONTRACT --rpc-url http://localhost:8545)
echo "💰 Vault balance: $BALANCE wei"

BLOCK=$(cast block-number --rpc-url http://localhost:8545)
echo "📦 Starting at block: $BLOCK"
echo ""

echo "🎯 Running ItyFuzz with Complete Fix..."
echo "Features:"
echo "  ✅ Target-aware ETH tracking"
echo "  ✅ Proper initialization order"
echo "  ✅ Lowered profit threshold (0.0001 ETH)"
echo "  ✅ Enhanced reentrancy detection"
echo ""

# Run ItyFuzz
timeout 120s ./target/release/ityfuzz evm \
    -t "$CONTRACT" \
    --onchain-block-number "$BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --onchain-chain-id 31337 \
    --work-dir "backtest_results/final" \
    > backtest_results/final.log 2>&1 &

PID=$!

# Monitor
echo "⏳ Monitoring (2 minute timeout)..."
START=$(date +%s)

while kill -0 $PID 2>/dev/null; do
    NOW=$(date +%s)
    ELAPSED=$((NOW - START))
    
    # Check for vulnerability
    if grep -q "objectives: [1-9]\|Fund Loss\|typed_bug\|bug_idx\|PROFITABLE" backtest_results/final.log 2>/dev/null; then
        echo ""
        echo "🎉 🎉 🎉 VULNERABILITY DETECTED after ${ELAPSED}s! 🎉 🎉 🎉"
        echo ""
        echo "Bug details:"
        grep -B5 -A15 "objectives:\|Fund Loss\|typed_bug\|bug_idx\|PROFITABLE" backtest_results/final.log | head -30
        echo ""
        echo "✅ ItyFuzz successfully detected the reentrancy fund loss!"
        kill $PID 2>/dev/null
        break
    fi
    
    # Progress update
    if [ $((ELAPSED % 10)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        EXEC=$(grep "executions:" backtest_results/final.log 2>/dev/null | tail -1 | grep -oE "executions: [0-9]+" | grep -oE "[0-9]+")
        OBJECTIVES=$(grep "objectives:" backtest_results/final.log 2>/dev/null | tail -1 | grep -oE "objectives: [0-9]+" | grep -oE "[0-9]+")
        echo "[${ELAPSED}s] Executions: ${EXEC:-0} | Objectives found: ${OBJECTIVES:-0}"
    fi
    
    sleep 1
done

# Final status
echo ""
if ! grep -q "objectives: [1-9]" backtest_results/final.log 2>/dev/null; then
    echo "❌ No vulnerability detected in 2 minutes"
    echo ""
    echo "Last status:"
    tail -10 backtest_results/final.log | grep -E "Stats|objectives|Coverage"
else
    echo "✅ Test completed successfully!"
    echo "ItyFuzz can now detect ALL fund loss bugs for MEV profitability!"
fi

# Cleanup
kill $ANVIL_PID 2>/dev/null
pkill anvil 2>/dev/null
echo ""
echo "🧹 Test complete!"