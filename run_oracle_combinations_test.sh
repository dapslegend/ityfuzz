#!/bin/bash

echo "🔬 Oracle Combination Testing"
echo "============================"
echo ""
echo "Testing each vulnerability with different oracle combinations"
echo "Timeout: 2 minutes per test"
echo ""

# Configuration
API_KEY="${BSC_ETHERSCAN_API_KEY}"
RPC_URL="https://rpc.ankr.com/bsc"
TIMEOUT=120  # 2 minutes per test

# Create results directory
mkdir -p "backtest_results/oracle_tests"

# Test function
test_with_oracles() {
    local name=$1
    local target=$2
    local block=$3
    local oracles=$4
    local test_name="${name}_${oracles//,/_}"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧪 Testing $name with oracles: $oracles"
    echo "   Addresses: $(echo $target | wc -w) contracts"
    
    # Run the test
    START_TIME=$(date +%s)
    
    timeout ${TIMEOUT}s ./target/release/ityfuzz evm \
        -t "$target" \
        -c bsc \
        --onchain-block-number "$block" \
        -f \
        --panic-on-bug \
        --onchain-etherscan-api-key "$API_KEY" \
        --onchain-url "$RPC_URL" \
        --detectors "$oracles" \
        --work-dir "backtest_results/oracle_tests/${test_name}" \
        > "backtest_results/oracle_tests/${test_name}.log" 2>&1
    
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    # Check results
    if grep -q "Found vulnerabilities\|objectives: [1-9]" "backtest_results/oracle_tests/${test_name}.log" 2>/dev/null; then
        echo "✅ FOUND in ${ELAPSED}s!"
        grep "Fund Loss\|Reentrancy\|typed_bug" "backtest_results/oracle_tests/${test_name}.log" | head -2
    else
        RATE=$(grep "exec/sec" "backtest_results/oracle_tests/${test_name}.log" 2>/dev/null | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        echo "❌ Not found in ${ELAPSED}s (Rate: ${RATE:-0} exec/sec)"
    fi
}

# Define oracle combinations to test
ORACLE_SETS=(
    "erc20"
    "reentrancy"
    "erc20,reentrancy"
    "arbitrary_call"
    "typed_bug"
    "erc20,balance_drain"
    "all"
)

echo "Testing oracle combinations..."
echo ""

# Test 1: BEGO (Fund Loss)
echo "════════════════════════════════════"
echo "📍 BEGO - Fund Loss Test"
echo "════════════════════════════════════"
BEGO_ADDR="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972"
for oracles in "${ORACLE_SETS[@]}"; do
    test_with_oracles "BEGO" "$BEGO_ADDR" "22315679" "$oracles"
done

# Test 2: RES02 (Reentrancy)
echo ""
echo "════════════════════════════════════"
echo "📍 RES02 - Reentrancy Test"
echo "════════════════════════════════════"
RES02_ADDR="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5c811d550E421bcc37cb2097AF5b40Eb62Cf6d7A,0xA0ED3C520dC0632657AD2EaaF19E26C4fD431a84"
for oracles in "${ORACLE_SETS[@]}"; do
    test_with_oracles "RES02" "$RES02_ADDR" "23695904" "$oracles"
done

# Test 3: Seaman (Access Control)
echo ""
echo "════════════════════════════════════"
echo "📍 Seaman - Access Control Test"
echo "════════════════════════════════════"
SEAMAN_ADDR="0x6bc9b4976ba6f8C9574326375204eE469993D038,0x7B86b0836f3454e50C6F6a190cd692bB17da1928"
for oracles in "${ORACLE_SETS[@]}"; do
    test_with_oracles "Seaman" "$SEAMAN_ADDR" "22142525" "$oracles"
done

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Oracle Combination Summary"
echo ""

# Count successes per oracle set
for oracles in "${ORACLE_SETS[@]}"; do
    oracle_name="${oracles//,/_}"
    success_count=$(grep -l "Found vulnerabilities" backtest_results/oracle_tests/*_${oracle_name}.log 2>/dev/null | wc -l)
    echo "Oracle set '$oracles': $success_count/3 vulnerabilities found"
done

echo ""
echo "✅ Testing complete!"
echo "📝 Detailed logs in: backtest_results/oracle_tests/"