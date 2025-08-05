#!/bin/bash

echo "🚀 Starting long-running vulnerability detection test..."
echo "⏱️  Test duration: 15 minutes"
echo ""

# Start Anvil
echo "🔗 Starting Anvil..."
anvil --port 8545 --chain-id 31337 --accounts 10 --balance 10000 --gas-limit 30000000 > anvil_long.log 2>&1 &
ANVIL_PID=$!

sleep 5

# Deploy contract
echo "📄 Deploying VulnerableVault..."
DEPLOY_OUTPUT=$(forge create /workspace/VulnerableVault.sol:VulnerableVault \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast \
    2>&1)

CONTRACT_ADDRESS=$(echo "$DEPLOY_OUTPUT" | grep -oE "Deployed to: 0x[a-fA-F0-9]{40}" | cut -d' ' -f3)
echo "✅ Contract deployed at: $CONTRACT_ADDRESS"

# Deposit funds
echo "💰 Depositing funds..."
cast send $CONTRACT_ADDRESS --value 10ether \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 > /dev/null

cast send $CONTRACT_ADDRESS --value 5ether \
    --rpc-url http://localhost:8545 \
    --private-key 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d > /dev/null

cast send $CONTRACT_ADDRESS --value 3ether \
    --rpc-url http://localhost:8545 \
    --private-key 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a > /dev/null

VAULT_BALANCE=$(cast balance $CONTRACT_ADDRESS --rpc-url http://localhost:8545)
echo "🏦 Vault balance: $VAULT_BALANCE (18 ETH)"

SCAN_BLOCK=$(cast block-number --rpc-url http://localhost:8545)
echo "📦 Starting block: $SCAN_BLOCK"

echo ""
echo "========================================="
echo "🎯 Running ItyFuzz for extended period"
echo "========================================="
echo "Contract: $CONTRACT_ADDRESS"
echo "Duration: 15 minutes"
echo ""

# Run ItyFuzz
cd /workspace
./target/release/ityfuzz evm \
    -t "$CONTRACT_ADDRESS" \
    --onchain-block-number "$SCAN_BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --onchain-chain-id 31337 \
    --work-dir "backtest_results/vulnerable_vault_long" \
    2>&1 | tee "backtest_results/vulnerable_vault_long.log" &

ITYFUZZ_PID=$!

# Monitor progress
echo "⏳ Monitoring progress..."
echo ""

START_TIME=$(date +%s)
LAST_EXEC=0
LAST_TIME=$START_TIME

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - START_TIME))
    
    # Check if found vulnerability
    if grep -q "Found vulnerabilities\|Fund Loss\|Reentrancy\|typed_bug" "backtest_results/vulnerable_vault_long.log" 2>/dev/null; then
        echo ""
        echo "🎉 VULNERABILITY FOUND after $((ELAPSED / 60))m $((ELAPSED % 60))s!"
        sleep 2
        echo ""
        grep -A30 "Found vulnerabilities\|================ Description" "backtest_results/vulnerable_vault_long.log" | head -50
        break
    fi
    
    # Show progress every 30 seconds
    if [ $((ELAPSED % 30)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        # Get current stats
        CURRENT_EXEC=$(grep "executions:" "backtest_results/vulnerable_vault_long.log" 2>/dev/null | tail -1 | grep -oE "executions: [0-9]+" | grep -oE "[0-9]+" | tail -1)
        EXEC_RATE=$(grep "exec/sec" "backtest_results/vulnerable_vault_long.log" 2>/dev/null | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        COVERAGE=$(grep "Instruction Covered" "backtest_results/vulnerable_vault_long.log" 2>/dev/null | tail -1 | grep -oE "[0-9]+\.[0-9]+%" | head -1)
        CORPUS=$(grep "corpus:" "backtest_results/vulnerable_vault_long.log" 2>/dev/null | tail -1 | grep -oE "corpus: [0-9]+" | grep -oE "[0-9]+" | tail -1)
        
        if [ -n "$CURRENT_EXEC" ] && [ "$CURRENT_EXEC" != "$LAST_EXEC" ]; then
            TIME_DIFF=$((CURRENT_TIME - LAST_TIME))
            EXEC_DIFF=$((CURRENT_EXEC - LAST_EXEC))
            
            echo "[$((ELAPSED / 60))m $((ELAPSED % 60))s] Executions: $CURRENT_EXEC | Rate: ${EXEC_RATE:-0} exec/sec | Coverage: ${COVERAGE:-0%} | Corpus: ${CORPUS:-0}"
            
            LAST_EXEC=$CURRENT_EXEC
            LAST_TIME=$CURRENT_TIME
        fi
    fi
    
    # Stop after 15 minutes
    if [ $ELAPSED -ge 900 ]; then
        echo ""
        echo "⏱️  Time limit reached (15 minutes)"
        break
    fi
    
    sleep 1
done

# Final check
if ! grep -q "Found vulnerabilities" "backtest_results/vulnerable_vault_long.log" 2>/dev/null; then
    echo ""
    echo "❌ No vulnerability found after 15 minutes"
    echo ""
    echo "Final statistics:"
    grep "Stats" "backtest_results/vulnerable_vault_long.log" | tail -5
    echo ""
    echo "Coverage achieved:"
    grep "Coverage Summary" -A5 "backtest_results/vulnerable_vault_long.log" | tail -10
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
kill $ITYFUZZ_PID 2>/dev/null
kill $ANVIL_PID 2>/dev/null
pkill anvil 2>/dev/null
echo "✅ Test completed!"