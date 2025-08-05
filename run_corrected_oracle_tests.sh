#!/bin/bash

echo "🔬 Corrected Oracle Combination Testing"
echo "======================================"
echo ""
echo "Using CORRECT block numbers and addresses from backtesting.md"
echo "Testing all oracle combinations (2 minutes each)"
echo ""

# Configuration
API_KEY="${BSC_ETHERSCAN_API_KEY}"
RPC_URL="https://rpc.ankr.com/bsc"
TIMEOUT=120  # 2 minutes per test

# Create results directory
mkdir -p "backtest_results/corrected_oracle_tests"

# Test function
test_with_oracles() {
    local name=$1
    local target=$2
    local block=$3
    local oracles=$4
    local test_name="${name}_${oracles//,/_}"
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧪 Testing $name with oracles: $oracles"
    echo "   Block: $block"
    echo "   Addresses: $(echo $target | tr ',' '\n' | wc -l) contracts"
    
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
        --work-dir "backtest_results/corrected_oracle_tests/${test_name}" \
        > "backtest_results/corrected_oracle_tests/${test_name}.log" 2>&1
    
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    # Check results
    if grep -q "Found vulnerabilities\|objectives: [1-9]" "backtest_results/corrected_oracle_tests/${test_name}.log" 2>/dev/null; then
        echo "✅ FOUND in ${ELAPSED}s!"
        VULN_TYPE=$(grep -E "Fund Loss|Reentrancy|typed_bug|Price Manipulation|Access Control" "backtest_results/corrected_oracle_tests/${test_name}.log" | head -1)
        echo "   Type: $VULN_TYPE"
        # Check for different exploit methods
        if grep -q "skim\|mint\|withdraw" "backtest_results/corrected_oracle_tests/${test_name}.log" 2>/dev/null; then
            echo "   Method: $(grep -oE "skim|mint|withdraw" "backtest_results/corrected_oracle_tests/${test_name}.log" | head -1)"
        fi
    else
        RATE=$(grep "exec/sec" "backtest_results/corrected_oracle_tests/${test_name}.log" 2>/dev/null | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
        echo "❌ Not found in ${ELAPSED}s (Rate: ${RATE:-0} exec/sec)"
    fi
}

# Define oracle combinations to test - INCLUDING "all"
ORACLE_SETS=(
    "erc20"
    "reentrancy"
    "erc20,reentrancy"
    "arbitrary_call"
    "typed_bug"
    "erc20,balance_drain"
    "all"
)

echo "Testing oracle combinations with CORRECT configurations..."
echo ""

# Test 1: BEGO (Fund Loss) - CORRECT
echo "════════════════════════════════════"
echo "📍 BEGO - Fund Loss Test"
echo "════════════════════════════════════"
BEGO_ADDR="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972"
BEGO_BLOCK="22315679"
for oracles in "${ORACLE_SETS[@]}"; do
    test_with_oracles "BEGO" "$BEGO_ADDR" "$BEGO_BLOCK" "$oracles"
done

# Test 2: SEAMAN (Fund Loss) - CORRECTED addresses and block!
echo ""
echo "════════════════════════════════════"
echo "📍 SEAMAN - Fund Loss Test (CORRECTED)"
echo "════════════════════════════════════"
SEAMAN_ADDR="0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e"
SEAMAN_BLOCK="23467515"  # CORRECTED!
for oracles in "${ORACLE_SETS[@]}"; do
    test_with_oracles "SEAMAN" "$SEAMAN_ADDR" "$SEAMAN_BLOCK" "$oracles"
done

# Test 3: RES02 (Price Manipulation) - CORRECTED addresses and block!
echo ""
echo "════════════════════════════════════"
echo "📍 RES02 - Price Manipulation Test (CORRECTED)"
echo "════════════════════════════════════"
RES02_ADDR="0x55d398326f99059fF775485246999027B3197955,0xD7B7218D778338Ea05f5Ecce82f86D365E25dBCE,0x05ba2c512788bd95cd6D61D3109c53a14b01c82A,0x1B214e38C5e861c56e12a69b6BAA0B45eFe5C8Eb,0xecCD8B08Ac3B587B7175D40Fb9C60a20990F8D21,0xeccd8b08ac3b587b7175d40fb9c60a20990f8d21,0x04C0f31C0f59496cf195d2d7F1dA908152722DE7,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
RES02_BLOCK="21948016"  # CORRECTED!
for oracles in "${ORACLE_SETS[@]}"; do
    test_with_oracles "RES02" "$RES02_ADDR" "$RES02_BLOCK" "$oracles"
done

# Test 4: LPC (Fund Loss) - For comparison
echo ""
echo "════════════════════════════════════"
echo "📍 LPC - Fund Loss Test"
echo "════════════════════════════════════"
LPC_ADDR="0x1e813fa05739bf145c1f182cb950da7af046778d,0x1E813fA05739Bf145c1F182CB950dA7af046778d,0x2ecD8Ce228D534D8740617673F31b7541f6A0099,0xcfb7909b7eb27b71fdc482a2883049351a1749d7"
LPC_BLOCK="19852596"
for oracles in "${ORACLE_SETS[@]}"; do
    test_with_oracles "LPC" "$LPC_ADDR" "$LPC_BLOCK" "$oracles"
done

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Oracle Combination Summary"
echo ""

# Count successes per oracle set
for oracles in "${ORACLE_SETS[@]}"; do
    oracle_name="${oracles//,/_}"
    success_count=$(grep -l "Found vulnerabilities" backtest_results/corrected_oracle_tests/*_${oracle_name}.log 2>/dev/null | wc -l)
    total_tests=4
    echo "Oracle set '$oracles': $success_count/$total_tests vulnerabilities found"
done

echo ""
echo "🔍 Vulnerability Methods Found:"
grep -h "Method:" backtest_results/corrected_oracle_tests/*.log 2>/dev/null | sort | uniq -c

echo ""
echo "✅ Testing complete!"
echo "📝 Detailed logs in: backtest_results/corrected_oracle_tests/"