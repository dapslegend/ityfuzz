#!/bin/bash
set -e

echo "🚀 Quick Test - Fixed ItyFuzz"

# Start Anvil
anvil --port 8545 --chain-id 31337 > /tmp/anvil.log 2>&1 &
ANVIL_PID=$!
sleep 3

# Deploy
CONTRACT=$(forge create VulnerableVault.sol:VulnerableVault \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast 2>&1 | grep "Deployed to:" | cut -d' ' -f3)

echo "✅ Contract: $CONTRACT"

# Deposit 
cast send $CONTRACT --value 1ether \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 > /dev/null

BLOCK=$(cast block-number --rpc-url http://localhost:8545)

# Run ItyFuzz
echo "🎯 Running ItyFuzz..."
timeout 60s ./target/release/ityfuzz evm \
    -t "$CONTRACT" \
    --onchain-block-number "$BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --onchain-chain-id 31337 \
    --work-dir "backtest_results/quick" \
    > backtest_results/quick.log 2>&1 &

PID=$!

# Monitor
for i in {1..60}; do
    if grep -q "objectives: [1-9]\|Fund Loss\|typed_bug" backtest_results/quick.log 2>/dev/null; then
        echo "🎉 FOUND BUG after ${i}s!"
        grep -B5 -A10 "objectives:\|Fund Loss" backtest_results/quick.log | head -20
        kill $PID 2>/dev/null
        break
    fi
    sleep 1
    if [ $((i % 10)) -eq 0 ]; then
        echo "[$i s] Still searching..."
    fi
done

kill $ANVIL_PID 2>/dev/null
echo "Done!"