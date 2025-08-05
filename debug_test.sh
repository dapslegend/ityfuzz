#!/bin/bash

echo "🔍 Debug Test"

# Cleanup
pkill anvil 2>/dev/null
pkill ityfuzz 2>/dev/null
sleep 2

# Start Anvil
anvil --port 8545 --chain-id 31337 > /tmp/anvil.log 2>&1 &
ANVIL_PID=$!
sleep 3

# Deploy
CONTRACT=$(forge create VulnerableVault.sol:VulnerableVault \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast 2>&1 | grep "Deployed to:" | cut -d' ' -f3)

echo "Contract: $CONTRACT"

# Deposit 
cast send $CONTRACT --value 1ether \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 > /dev/null

BLOCK=$(cast block-number --rpc-url http://localhost:8545)

# Run with debug
echo "Running with debug..."
RUST_LOG=debug timeout 30s ./target/release/ityfuzz evm \
    -t "$CONTRACT" \
    --onchain-block-number "$BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --onchain-chain-id 31337 \
    --work-dir "backtest_results/debug" \
    2>&1 | grep -E "target|Target|flashloan|earned|owed" | head -50

kill $ANVIL_PID 2>/dev/null
echo "Done!"