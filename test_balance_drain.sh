#!/bin/bash

echo "🚀 Testing ItyFuzz with Balance Drain Oracle"
echo "=========================================="
echo ""

# Cleanup
pkill anvil 2>/dev/null
pkill ityfuzz 2>/dev/null
sleep 2

# Start Anvil
echo "🔗 Starting Anvil..."
anvil --port 8545 --chain-id 31337 > /tmp/anvil.log 2>&1 &
ANVIL_PID=$!
sleep 3

# Deploy
echo "📄 Deploying VulnerableVault..."
CONTRACT=$(forge create VulnerableVault.sol:VulnerableVault \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast 2>&1 | grep "Deployed to:" | cut -d' ' -f3)

echo "✅ Contract: $CONTRACT"

# Deposit 
echo "💰 Depositing 1 ETH..."
cast send $CONTRACT --value 1ether \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 > /dev/null

BLOCK=$(cast block-number --rpc-url http://localhost:8545)

# Run with balance drain oracle
echo ""
echo "🎯 Running ItyFuzz with Balance Drain Oracle..."
echo "  - Detects when contract balance decreases"
echo "  - Checks if attacker profits"
echo "  - Works for ANY fund loss pattern"
echo ""

timeout 90s ./target/release/ityfuzz evm \
    -t "$CONTRACT" \
    --onchain-block-number "$BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --onchain-chain-id 31337 \
    --detectors "erc20,balance_drain" \
    --work-dir "backtest_results/balance_drain" \
    > backtest_results/balance_drain.log 2>&1 &

PID=$!

# Monitor
echo "⏳ Monitoring..."
for i in {1..90}; do
    if grep -q "objectives: [1-9]\|Balance Drain\|balance drained" backtest_results/balance_drain.log 2>/dev/null; then
        echo ""
        echo "🎉 🎉 🎉 FUND LOSS DETECTED after ${i}s! 🎉 🎉 🎉"
        echo ""
        grep -B5 -A15 "Balance Drain\|balance drained\|objectives:" backtest_results/balance_drain.log | head -30
        kill $PID 2>/dev/null
        break
    fi
    
    if [ $((i % 10)) -eq 0 ]; then
        EXEC=$(grep "executions:" backtest_results/balance_drain.log 2>/dev/null | tail -1 | grep -oE "executions: [0-9]+" | grep -oE "[0-9]+")
        OBJECTIVES=$(grep "objectives:" backtest_results/balance_drain.log 2>/dev/null | tail -1 | grep -oE "objectives: [0-9]+" | grep -oE "[0-9]+")
        echo "[${i}s] Executions: ${EXEC:-0} | Objectives: ${OBJECTIVES:-0}"
    fi
    
    sleep 1
done

# Final check
if ! grep -q "objectives: [1-9]\|Balance Drain" backtest_results/balance_drain.log 2>/dev/null; then
    echo ""
    echo "❌ No fund loss detected"
    tail -20 backtest_results/balance_drain.log
fi

# Cleanup
kill $ANVIL_PID 2>/dev/null
echo ""
echo "✅ Test complete!"