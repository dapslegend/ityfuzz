#!/bin/bash

echo "🚀 Starting extended vulnerability detection test..."

# Kill any existing processes
pkill anvil 2>/dev/null
pkill ityfuzz 2>/dev/null
sleep 2

# Start Anvil
echo "🔗 Starting Anvil..."
anvil --port 8545 --chain-id 31337 --accounts 10 --balance 10000 --gas-limit 30000000 > /tmp/anvil_extended.log 2>&1 &
ANVIL_PID=$!

sleep 5

# Deploy contract
echo "📄 Deploying VulnerableVault..."
DEPLOY_OUTPUT=$(forge create /workspace/VulnerableVault.sol:VulnerableVault \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast 2>&1)

CONTRACT_ADDRESS=$(echo "$DEPLOY_OUTPUT" | grep -oE "Deployed to: 0x[a-fA-F0-9]{40}" | cut -d' ' -f3)

if [ -z "$CONTRACT_ADDRESS" ]; then
    echo "❌ Failed to deploy contract"
    exit 1
fi

echo "✅ Contract deployed at: $CONTRACT_ADDRESS"

# Deposit funds
echo "💰 Depositing 20 ETH total..."
cast send $CONTRACT_ADDRESS --value 10ether --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 > /dev/null

cast send $CONTRACT_ADDRESS --value 10ether --rpc-url http://localhost:8545 \
    --private-key 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d > /dev/null

SCAN_BLOCK=$(cast block-number --rpc-url http://localhost:8545)

echo "📦 Starting at block: $SCAN_BLOCK"
echo "🏦 Vault has 20 ETH"
echo ""

# Run ItyFuzz in background
echo "🎯 Starting ItyFuzz (will run for 30 minutes)..."
cd /workspace

nohup ./target/release/ityfuzz evm \
    -t "$CONTRACT_ADDRESS" \
    --onchain-block-number "$SCAN_BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --onchain-chain-id 31337 \
    --work-dir "backtest_results/vault_extended" \
    > "backtest_results/vault_extended.log" 2>&1 &

ITYFUZZ_PID=$!

echo "✅ ItyFuzz started (PID: $ITYFUZZ_PID)"
echo ""
echo "📊 Monitor progress with:"
echo "   tail -f backtest_results/vault_extended.log"
echo ""
echo "🔍 Check for vulnerabilities with:"
echo "   grep -i 'found\|vulnerability\|reentrancy' backtest_results/vault_extended.log"
echo ""
echo "Contract: $CONTRACT_ADDRESS"
echo "Anvil PID: $ANVIL_PID"
echo "ItyFuzz PID: $ITYFUZZ_PID"