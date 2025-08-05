#!/bin/bash

echo "🚀 Testing Fixed ItyFuzz - Should Detect ALL Fund Loss Bugs"
echo "========================================================"
echo ""

# Kill any existing processes
pkill anvil 2>/dev/null
pkill ityfuzz 2>/dev/null
sleep 2

# Start Anvil
echo "🔗 Starting Anvil..."
anvil --port 8545 --chain-id 31337 > /tmp/anvil_fixed.log 2>&1 &
ANVIL_PID=$!
sleep 5

# Deploy vulnerable contract
echo "📄 Deploying VulnerableVault..."
DEPLOY=$(forge create /workspace/VulnerableVault.sol:VulnerableVault \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast 2>&1)

CONTRACT=$(echo "$DEPLOY" | grep -oE "Deployed to: 0x[a-fA-F0-9]{40}" | cut -d' ' -f3)
echo "✅ Contract at: $CONTRACT"

# Deposit initial funds
echo "💰 Depositing 5 ETH..."
cast send $CONTRACT --value 5ether \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 > /dev/null

BLOCK=$(cast block-number --rpc-url http://localhost:8545)
echo "📦 Block: $BLOCK"
echo ""

echo "🎯 Running Fixed ItyFuzz..."
echo "Features:"
echo "  ✅ Track ALL ETH leaving contracts as profit"
echo "  ✅ Lowered threshold (0.0001 ETH)"
echo "  ✅ Enhanced reentrancy detection"
echo ""

cd /workspace
timeout 120s ./target/release/ityfuzz evm \
    -t "$CONTRACT" \
    --onchain-block-number "$BLOCK" \
    -c LOCAL \
    -f \
    --panic-on-bug \
    --onchain-url "http://localhost:8545" \
    --onchain-chain-id 31337 \
    --work-dir "backtest_results/fixed_test" \
    2>&1 | tee "backtest_results/fixed_test.log" &

ITYFUZZ_PID=$!

# Monitor
START=$(date +%s)
echo "⏳ Monitoring (2 minute timeout)..."

while kill -0 $ITYFUZZ_PID 2>/dev/null; do
    NOW=$(date +%s)
    ELAPSED=$((NOW - START))
    
    # Check for any bug found
    if grep -q "Found vulnerabilities\|Fund Loss\|typed_bug\|Reentrancy.*PROFITABLE\|objectives: [1-9]" "backtest_results/fixed_test.log" 2>/dev/null; then
        echo ""
        echo "🎉 BUG FOUND after $((ELAPSED))s!"
        echo ""
        grep -B5 -A20 "Found vulnerabilities\|Fund Loss\|typed_bug\|PROFITABLE\|objectives:" "backtest_results/fixed_test.log" | head -40
        kill $ITYFUZZ_PID 2>/dev/null
        break
    fi
    
    # Show progress
    if [ $((ELAPSED % 10)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        OBJECTIVES=$(grep "objectives:" backtest_results/fixed_test.log 2>/dev/null | tail -1 | grep -oE "objectives: [0-9]+" | grep -oE "[0-9]+")
        EXEC=$(grep "executions:" backtest_results/fixed_test.log 2>/dev/null | tail -1 | grep -oE "executions: [0-9]+" | grep -oE "[0-9]+")
        echo "[$ELAPSED s] Executions: ${EXEC:-0} | Objectives: ${OBJECTIVES:-0}"
    fi
    
    sleep 1
done

# Final check
echo ""
if ! grep -q "objectives: [1-9]\|Fund Loss\|typed_bug" "backtest_results/fixed_test.log" 2>/dev/null; then
    echo "❌ No bug found in 2 minutes"
    tail -10 backtest_results/fixed_test.log
else
    echo "✅ Successfully detected the vulnerability!"
fi

# Cleanup
kill $ANVIL_PID 2>/dev/null
pkill anvil 2>/dev/null
echo "🧹 Done!"