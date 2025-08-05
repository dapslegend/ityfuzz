#!/bin/bash

echo "🎯 Testing ItyFuzz with Target Tracking"
echo "======================================"

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
echo "💰 Depositing 2 ETH..."
cast send $CONTRACT --value 2ether \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 > /dev/null

BLOCK=$(cast block-number --rpc-url http://localhost:8545)

# Run ItyFuzz
echo ""
echo "🎯 Running ItyFuzz with target tracking..."
echo "  - Only ETH leaving $CONTRACT will be tracked as earned"
echo "  - Deposits won't be double-counted"
echo ""

timeout 90s ./target/release/ityfuzz evm \
    -t "$CONTRACT" \
    --onchain-block-number "$BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --onchain-chain-id 31337 \
    --work-dir "backtest_results/target_tracking" \
    > backtest_results/target_tracking.log 2>&1 &

PID=$!

# Monitor
for i in {1..90}; do
    if grep -q "objectives: [1-9]\|Fund Loss\|typed_bug\|PROFITABLE" backtest_results/target_tracking.log 2>/dev/null; then
        echo ""
        echo "🎉 VULNERABILITY DETECTED after ${i}s!"
        echo ""
        grep -B10 -A20 "objectives:\|Fund Loss\|typed_bug\|PROFITABLE" backtest_results/target_tracking.log | head -40
        kill $PID 2>/dev/null
        break
    fi
    
    if [ $((i % 10)) -eq 0 ]; then
        EXEC=$(grep "executions:" backtest_results/target_tracking.log 2>/dev/null | tail -1 | grep -oE "executions: [0-9]+" | grep -oE "[0-9]+")
        echo "[$i s] Executions: ${EXEC:-0}"
    fi
    
    sleep 1
done

# Final check
if ! grep -q "objectives: [1-9]" backtest_results/target_tracking.log 2>/dev/null; then
    echo ""
    echo "❌ No vulnerability detected"
    tail -20 backtest_results/target_tracking.log
fi

# Cleanup
kill $ANVIL_PID 2>/dev/null
pkill anvil 2>/dev/null
echo ""
echo "✅ Test complete!"