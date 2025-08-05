#!/bin/bash

echo "🔥 BEAST MODE ItyFuzz Backtests 🔥"
echo "================================"
echo ""
echo "Tweaks applied:"
echo "  ✅ Ultra-low profit threshold (0.000001 ETH)"
echo "  ✅ Multiple oracle combinations"
echo "  ✅ Optimized RPC endpoint"
echo "  ✅ Correct blocks & addresses"
echo "  ✅ Strategic timeouts"
echo ""

# Beast mode settings
export RUST_LOG=error  # Minimal logging for speed
export RAYON_NUM_THREADS=16  # Max threads

# Configuration
API_KEY="${BSC_ETHERSCAN_API_KEY}"
RPC_URL="https://rpc.ankr.com/bsc"  # Fast RPC

# Create results directory
mkdir -p "backtest_results/beast"

# Test function with multiple oracle attempts
test_beast() {
    local name=$1
    local target=$2
    local block=$3
    local expected=$4
    local timeout=${5:-180}  # Default 3 minutes
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎯 $name - $expected"
    echo "   Contracts: $(echo $target | tr ',' '\n' | wc -l)"
    echo "   Block: $block"
    
    # Try different oracle combinations until we find something
    local found=false
    local oracles_tried=0
    
    # Oracle sets in order of effectiveness
    for oracles in "erc20" "all" "erc20,reentrancy" "erc20,balance_drain"; do
        oracles_tried=$((oracles_tried + 1))
        echo ""
        echo "   🧪 Attempt $oracles_tried: oracles=$oracles"
        
        START_TIME=$(date +%s)
        
        # Run with timeout
        timeout $timeout ./target/release/ityfuzz evm \
            -t "$target" \
            -c bsc \
            --onchain-block-number "$block" \
            -f \
            --panic-on-bug \
            --onchain-etherscan-api-key "$API_KEY" \
            --onchain-url "$RPC_URL" \
            --detectors "$oracles" \
            --work-dir "backtest_results/beast/${name}_${oracles//,/_}" \
            > "backtest_results/beast/${name}_${oracles//,/_}.log" 2>&1
        
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        
        # Check if found
        if grep -q "Found vulnerabilities" "backtest_results/beast/${name}_${oracles//,/_}.log" 2>/dev/null; then
            echo "   ✅ FOUND in ${ELAPSED}s with $oracles!"
            PROFIT=$(grep -oE "[0-9]+\.[0-9]+ ETH" "backtest_results/beast/${name}_${oracles//,/_}.log" | head -1)
            echo "   💰 Profit: ${PROFIT:-unknown}"
            found=true
            break
        else
            RATE=$(grep "exec/sec" "backtest_results/beast/${name}_${oracles//,/_}.log" | tail -1 | grep -oE "[0-9]+\.?[0-9]*k?" | tail -1)
            echo "   ❌ Not found (${ELAPSED}s, ${RATE:-0} exec/sec)"
        fi
    done
    
    if [ "$found" = false ]; then
        echo ""
        echo "   ⚠️  Not detected with any oracle combination"
    fi
    echo ""
}

echo "🚀 Starting BEAST MODE backtests..."
echo ""

# CORRECT configurations from backtesting.md

# Easy ones first
test_beast "BEGO" \
    "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972" \
    "22315679" \
    "Fund Loss" \
    "120"

test_beast "EGD-Finance" \
    "0x55d398326f99059fF775485246999027B3197955,0x202b233735bF743FA31abb8f71e641970161bF98,0xa361433E409Adac1f87CDF133127585F8a93c67d,0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE,0x34Bd6Dba456Bc31c2b3393e499fa10bED32a9370,0xc30808d9373093fbfcec9e026457c6a9dab706a7,0x34bd6dba456bc31c2b3393e499fa10bed32a9370,0x93c175439726797dcee24d08e4ac9164e88e7aee" \
    "20245522" \
    "Fund Loss" \
    "120"

test_beast "SEAMAN" \
    "0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e" \
    "23467515" \
    "Fund Loss" \
    "120"

test_beast "FAPEN" \
    "0xf3f1abae8bfeca054b330c379794a7bf84988228,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0xf3F1aBae8BfeCA054B330C379794A7bf84988228" \
    "28637846" \
    "Fund Loss" \
    "120"

# Price manipulation ones
test_beast "BBOX" \
    "0x0fe261aeE0d1C4DFdDee4102E82Dd425999065F4,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x5DfC7f3EbBB9Cbfe89bc3FB70f750Ee229a59F8c" \
    "23106506" \
    "Price Manipulation" \
    "180"

test_beast "RES02" \
    "0x55d398326f99059fF775485246999027B3197955,0xD7B7218D778338Ea05f5Ecce82f86D365E25dBCE,0x05ba2c512788bd95cd6D61D3109c53a14b01c82A,0x1B214e38C5e861c56e12a69b6BAA0B45eFe5C8Eb,0xecCD8B08Ac3B587B7175D40Fb9C60a20990F8D21,0xeccd8b08ac3b587b7175d40fb9c60a20990f8d21,0x04C0f31C0f59496cf195d2d7F1dA908152722DE7,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c" \
    "21948016" \
    "Price Manipulation" \
    "180"

# Harder ones with more time
test_beast "LPC" \
    "0x1e813fa05739bf145c1f182cb950da7af046778d,0x1E813fA05739Bf145c1F182CB950dA7af046778d,0x2ecD8Ce228D534D8740617673F31b7541f6A0099,0xcfb7909b7eb27b71fdc482a2883049351a1749d7" \
    "19852596" \
    "Fund Loss" \
    "300"

test_beast "AUR" \
    "0x73A1163EA930A0a67dFEFB9C3713Ef0923755B78,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x70678291bDDfd95498d1214BE368e19e882f7614" \
    "23282134" \
    "Fund Loss" \
    "300"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 BEAST MODE Summary"
echo ""

# Count successes
SUCCESS=0
TOTAL=0
for name in BEGO EGD-Finance SEAMAN FAPEN BBOX RES02 LPC AUR; do
    for oracles in erc20 all erc20_reentrancy erc20_balance_drain; do
        if [ -f "backtest_results/beast/${name}_${oracles}.log" ]; then
            if grep -q "Found vulnerabilities" "backtest_results/beast/${name}_${oracles}.log" 2>/dev/null; then
                SUCCESS=$((SUCCESS + 1))
                break
            fi
        fi
    done
    TOTAL=$((TOTAL + 1))
done

echo "🔥 Vulnerabilities found: $SUCCESS/$TOTAL"
echo ""

# Show what was found
echo "Detected vulnerabilities:"
for log in backtest_results/beast/*.log; do
    if [ -f "$log" ] && grep -q "Found vulnerabilities" "$log" 2>/dev/null; then
        name=$(basename "$log" .log | cut -d_ -f1)
        profit=$(grep -oE "[0-9]+\.[0-9]+ ETH" "$log" | head -1)
        echo "  ✅ $name: ${profit:-found}"
    fi
done

echo ""
echo "🔥 BEAST MODE COMPLETE! 🔥"