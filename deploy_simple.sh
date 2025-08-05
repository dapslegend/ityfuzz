#!/bin/bash

echo "🚀 Starting Anvil local blockchain..."

# Kill any existing Anvil instances
pkill anvil 2>/dev/null

# Start Anvil in the background
anvil --port 8545 --chain-id 31337 --accounts 10 --balance 10000 --gas-limit 30000000 &
ANVIL_PID=$!

# Wait for Anvil to start
echo "⏳ Waiting for Anvil to start..."
sleep 5

echo "✅ Anvil started (PID: $ANVIL_PID)"

# Get the current block number
BLOCK_NUMBER=$(cast block-number --rpc-url http://localhost:8545)
echo "📦 Current block number: $BLOCK_NUMBER"

# Deploy using forge create
echo "📄 Deploying VulnerableVault..."

DEPLOY_OUTPUT=$(forge create /workspace/VulnerableVault.sol:VulnerableVault \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast \
    2>&1)

# Extract contract address from output
CONTRACT_ADDRESS=$(echo "$DEPLOY_OUTPUT" | grep -oE "Deployed to: 0x[a-fA-F0-9]{40}" | cut -d' ' -f3)

if [ -z "$CONTRACT_ADDRESS" ]; then
    echo "❌ Failed to deploy contract"
    echo "$DEPLOY_OUTPUT"
    kill $ANVIL_PID
    exit 1
fi

echo "✅ Contract deployed at: $CONTRACT_ADDRESS"

# Deposit some ETH using direct transfer
echo "💰 Depositing ETH into the vault..."

# Send 5 ETH to the contract (will trigger receive function)
cast send $CONTRACT_ADDRESS \
    --value 5ether \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

echo "  ✓ Deposited 5 ETH from account 1"

# Send 3 ETH from second account
cast send $CONTRACT_ADDRESS \
    --value 3ether \
    --rpc-url http://localhost:8545 \
    --private-key 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d

echo "  ✓ Deposited 3 ETH from account 2"

# Check vault balance
VAULT_BALANCE=$(cast balance $CONTRACT_ADDRESS --rpc-url http://localhost:8545)
echo "🏦 Vault balance: $VAULT_BALANCE"

# Get the current block number for ItyFuzz
SCAN_BLOCK=$(cast block-number --rpc-url http://localhost:8545)
echo "🔍 Block number for scanning: $SCAN_BLOCK"

echo ""
echo "========================================="
echo "🎯 Running ItyFuzz to find vulnerability"
echo "========================================="
echo "Contract: $CONTRACT_ADDRESS"
echo "Block: $SCAN_BLOCK"
echo "Chain: LOCAL (31337)"
echo ""

# Run ItyFuzz with proper configuration for local chain
cd /workspace
./target/release/ityfuzz evm \
    -t "$CONTRACT_ADDRESS" \
    --onchain-block-number "$SCAN_BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --onchain-chain-id 31337 \
    --work-dir "backtest_results/vulnerable_vault" \
    2>&1 | tee "backtest_results/vulnerable_vault.log" &

ITYFUZZ_PID=$!

# Monitor for 2 minutes
echo "⏳ Monitoring for vulnerabilities (2 minutes max)..."
TIMEOUT=120
ELAPSED=0

while [ $ELAPSED -lt $TIMEOUT ]; do
    if grep -q "Found vulnerabilities\|Fund Loss\|Reentrancy" "backtest_results/vulnerable_vault.log" 2>/dev/null; then
        echo ""
        echo "✅ VULNERABILITY FOUND!"
        sleep 2  # Let it write more details
        grep -A20 "Found vulnerabilities\|================ Description" "backtest_results/vulnerable_vault.log" | head -30
        break
    fi
    
    # Show progress
    if [ $((ELAPSED % 10)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        EXEC_RATE=$(grep "exec/sec" "backtest_results/vulnerable_vault.log" 2>/dev/null | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        echo "  Progress: ${ELAPSED}s elapsed, ${EXEC_RATE:-0} exec/sec"
    fi
    
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

# Kill ItyFuzz if still running
kill $ITYFUZZ_PID 2>/dev/null

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo ""
    echo "❌ No vulnerability found in the time limit"
    echo ""
    echo "Last activity:"
    tail -20 "backtest_results/vulnerable_vault.log"
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
kill $ANVIL_PID 2>/dev/null
pkill anvil 2>/dev/null
echo "✅ Done!"