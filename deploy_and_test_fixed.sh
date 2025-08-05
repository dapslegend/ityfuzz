#!/bin/bash

echo "🚀 Starting Anvil local blockchain..."

# Kill any existing Anvil instances
pkill anvil 2>/dev/null

# Start Anvil in the background
anvil --port 8545 --chain-id 31337 --accounts 10 --balance 10000 --gas-limit 30000000 > anvil.log 2>&1 &
ANVIL_PID=$!

# Wait for Anvil to start
echo "⏳ Waiting for Anvil to start..."
sleep 5

# Check if Anvil is running
if ! curl -s http://localhost:8545 > /dev/null 2>&1; then
    echo "❌ Anvil failed to start"
    cat anvil.log
    exit 1
fi

echo "✅ Anvil started successfully (PID: $ANVIL_PID)"

# Get the current block number
BLOCK_NUMBER=$(cast block-number --rpc-url http://localhost:8545)
echo "📦 Current block number: $BLOCK_NUMBER"

# Create a simple Forge project structure
mkdir -p /workspace/vault_project/src
cp /workspace/VulnerableVault.sol /workspace/vault_project/src/

# Initialize forge project
cd /workspace/vault_project
forge init --force --no-commit

# Deploy the contract using cast
echo "📄 Deploying VulnerableVault..."

# First compile to get bytecode
cd /workspace
forge build VulnerableVault.sol

# Deploy using cast
BYTECODE=$(forge inspect VulnerableVault.sol:VulnerableVault bytecode)
DEPLOY_TX=$(cast send --create "$BYTECODE" \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --json)

CONTRACT_ADDRESS=$(echo "$DEPLOY_TX" | jq -r '.contractAddress')
echo "✅ Contract deployed at: $CONTRACT_ADDRESS"

# Get account addresses
ACCOUNT1="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
ACCOUNT2="0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

# Deposit some ETH from multiple accounts
echo "💰 Depositing ETH into the vault..."

# Deposit from account 1 (5 ETH)
cast send $CONTRACT_ADDRESS \
    --value 5ether \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    > /dev/null

echo "  ✓ Deposited 5 ETH from account 1"

# Deposit from account 2 (3 ETH)
cast send $CONTRACT_ADDRESS \
    --value 3ether \
    --rpc-url http://localhost:8545 \
    --private-key 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d \
    > /dev/null

echo "  ✓ Deposited 3 ETH from account 2"

# Check vault balance
VAULT_BALANCE_HEX=$(cast balance $CONTRACT_ADDRESS --rpc-url http://localhost:8545)
VAULT_BALANCE_DEC=$(cast --to-dec $VAULT_BALANCE_HEX)
VAULT_BALANCE_ETH=$(echo "scale=2; $VAULT_BALANCE_DEC / 1000000000000000000" | bc -l)
echo "🏦 Vault balance: $VAULT_BALANCE_ETH ETH"

# Get the current block number for ItyFuzz
SCAN_BLOCK=$(cast block-number --rpc-url http://localhost:8545)
echo "🔍 Block number for scanning: $SCAN_BLOCK"

echo ""
echo "========================================="
echo "🎯 Running ItyFuzz to find vulnerability"
echo "========================================="
echo "Contract: $CONTRACT_ADDRESS"
echo "Block: $SCAN_BLOCK"
echo ""

# Run ItyFuzz
cd /workspace
timeout 120s ./target/release/ityfuzz evm \
    -t "$CONTRACT_ADDRESS" \
    --onchain-block-number "$SCAN_BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --work-dir "backtest_results/vulnerable_vault" \
    2>&1 | tee "backtest_results/vulnerable_vault.log"

# Check if vulnerability was found
if grep -q "Found vulnerabilities" "backtest_results/vulnerable_vault.log"; then
    echo ""
    echo "✅ VULNERABILITY FOUND!"
    grep -A10 "Found vulnerabilities" "backtest_results/vulnerable_vault.log"
else
    echo ""
    echo "❌ No vulnerability found in the time limit"
    echo "Last few lines of the log:"
    tail -20 "backtest_results/vulnerable_vault.log"
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
kill $ANVIL_PID 2>/dev/null
pkill anvil 2>/dev/null
echo "✅ Done!"