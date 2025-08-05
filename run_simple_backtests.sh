#!/bin/bash

echo "🚀 Simple ItyFuzz Backtests"
echo "=========================="
echo ""

# Performance settings
export RUST_LOG=warn
export RAYON_NUM_THREADS=8

# Configuration
API_KEY="${BSC_ETHERSCAN_API_KEY}"
RPC_URL="https://rpc.ankr.com/bsc"

# Create results directory
mkdir -p "backtest_results/simple"

# Test function
test_vuln() {
    local name=$1
    local target=$2
    local block=$3
    local expected=$4
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎯 Testing $name"
    echo "   Expected: $expected"
    echo "   Contracts: $(echo $target | tr ',' '\n' | wc -l)"
    
    START_TIME=$(date +%s)
    
    # Simple command with just essential flags
    timeout 180s ./target/release/ityfuzz evm \
        -t "$target" \
        -c bsc \
        --onchain-block-number "$block" \
        -f \
        --panic-on-bug \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$RPC_URL" \
        --work-dir "backtest_results/simple/${name}" \
        > "backtest_results/simple/${name}.log" 2>&1
    
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    # Check results
    if grep -q "Found vulnerabilities" "backtest_results/simple/${name}.log" 2>/dev/null; then
        echo "✅ FOUND in ${ELAPSED}s!"
        # Extract profit
        PROFIT=$(grep -oE "[0-9]+\.[0-9]+ ETH" "backtest_results/simple/${name}.log" | head -1)
        echo "   Profit: ${PROFIT:-unknown}"
        # Extract method
        METHOD=$(grep -E "skim\(|mint\(|withdraw\(" "backtest_results/simple/${name}.log" | head -1 | grep -oE "skim|mint|withdraw")
        [ -n "$METHOD" ] && echo "   Method: $METHOD"
    else
        echo "❌ Not found in ${ELAPSED}s"
        # Show performance
        RATE=$(grep "exec/sec" "backtest_results/simple/${name}.log" | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        [ -n "$RATE" ] && echo "   Rate: ${RATE} exec/sec"
        # Show any errors
        if grep -q "error\|Error\|panic" "backtest_results/simple/${name}.log" 2>/dev/null; then
            echo "   ⚠️  Error detected in log"
        fi
    fi
    echo ""
}

echo "Running simple backtests..."
echo ""

# Test with CORRECT configurations from backtesting.md
test_vuln "BEGO" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972" \
    "22315679" \
    "Fund Loss"

test_vuln "EGD-Finance" \
    "0x55d398326f99059fF775485246999027B3197955,0x202b233735bF743FA31abb8f71e641970161bF98,0xa361433E409Adac1f87CDF133127585F8a93c67d,0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE,0x34Bd6Dba456Bc31c2b3393e499fa10bED32a9370,0xc30808d9373093fbfcec9e026457c6a9dab706a7,0x34bd6dba456bc31c2b3393e499fa10bed32a9370,0x93c175439726797dcee24d08e4ac9164e88e7aee" \
    "20245522" \
    "Fund Loss"

test_vuln "FAPEN" \
    "0xf3f1abae8bfeca054b330c379794a7bf84988228,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0xf3F1aBae8BfeCA054B330C379794A7bf84988228" \
    "28637846" \
    "Fund Loss"

test_vuln "BBOX" \
    "0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c" \
    "23106506" \
    "Price Manipulation"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Summary"
echo ""

# Count successes
SUCCESS=0
TOTAL=0
for log in backtest_results/simple/*.log; do
    if [ -f "$log" ]; then
        TOTAL=$((TOTAL + 1))
        if grep -q "Found vulnerabilities" "$log" 2>/dev/null; then
            SUCCESS=$((SUCCESS + 1))
        fi
    fi
done

echo "Vulnerabilities found: $SUCCESS/$TOTAL"
echo ""

# Performance comparison
echo "Performance Stats:"
for log in backtest_results/simple/*.log; do
    if [ -f "$log" ]; then
        name=$(basename "$log" .log)
        rate=$(grep "exec/sec" "$log" | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        if [ -n "$rate" ]; then
            echo "  $name: ${rate} exec/sec"
        fi
    fi
done

echo ""
echo "✅ Testing complete!"