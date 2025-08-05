#!/bin/bash

# Configuration
API_KEY="SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
RPC_URL="https://rpc.ankr.com/bsc"  # Ankr RPC works well

echo "🔬 TIME ANALYSIS: Finding min/max detection times for BSC vulnerabilities"
echo "🔧 RPC: ${RPC_URL}"
echo "⚡ Using aggressive ityfuzz optimizations"
echo ""

# Function to test with different time limits
test_vulnerability() {
    local name=$1
    local target=$2
    local block=$3
    local expected_vuln=$4
    local time_limits=(5 10 15 20 30 45 60 90 120 180 300)
    
    echo "================================================================"
    echo "🎯 Testing $name (Block: $block)"
    echo "📋 Expected: $expected_vuln"
    echo "================================================================"
    
    local found=false
    local detection_time=0
    
    for time_limit in "${time_limits[@]}"; do
        if [ "$found" = true ]; then
            break
        fi
        
        echo "⏱️  Testing with ${time_limit}s time limit..."
        
        # Run test
        timeout ${time_limit}s ./target/release/ityfuzz evm \
            -t "$target" \
            -c bsc \
            --onchain-block-number "$block" \
            -f \
            --panic-on-bug \
            --onchain-etherscan-api-key "$API_KEY" \
            --onchain-url "$RPC_URL" \
            --detectors all \
            --work-dir "backtest_results/${name}_${time_limit}s" \
            > "backtest_results/${name}_${time_limit}s.log" 2>&1
        
        # Check if bug was found
        if grep -q "Found vulnerabilities\|Fund Loss\|Price Manipulation" "backtest_results/${name}_${time_limit}s.log" 2>/dev/null; then
            found=true
            detection_time=$time_limit
            
            # Get exact time from log
            actual_time=$(grep -oP "run time: \K[0-9h-]+[0-9m-]+[0-9]+s" "backtest_results/${name}_${time_limit}s.log" | tail -1)
            
            echo "✅ BUG FOUND in time limit: ${time_limit}s"
            echo "📊 Actual detection time: ${actual_time}"
            
            # Show vulnerability details
            grep -A5 "Found vulnerabilities" "backtest_results/${name}_${time_limit}s.log" | head -10
            
            # Show performance
            echo "⚡ Performance:"
            grep "exec/sec" "backtest_results/${name}_${time_limit}s.log" | tail -3
        else
            echo "❌ Not found in ${time_limit}s"
            # Show performance even if not found
            grep "exec/sec" "backtest_results/${name}_${time_limit}s.log" 2>/dev/null | tail -1
        fi
        
        echo ""
    done
    
    if [ "$found" = false ]; then
        echo "❌ $name: NOT FOUND even with 300s (5 min) timeout"
    else
        echo "✅ $name: FOUND with ${detection_time}s time limit"
    fi
    
    echo ""
    echo "----------------------------------------"
    echo ""
}

# Run comprehensive tests
echo "🏃 Running time analysis for all vulnerabilities..."
echo ""

# BEGO - Already confirmed working in 25s
echo "✅ BEGO: Already confirmed - Fund Loss found in 25s (13.80k exec/sec)"
echo ""

# LPC - Fund Loss (expected: ~4s)
test_vulnerability "LPC" \
    "0x1e813fa05739bf145c1f182cb950da7af046778d,0x1E813fA05739Bf145c1F182CB950dA7af046778d,0x2ecD8Ce228D534D8740617673F31b7541f6A0099,0xcfb7909b7eb27b71fdc482a2883049351a1749d7" \
    19852596 \
    "Fund Loss"

# RES02 - Price Manipulation (expected: ~2s)
test_vulnerability "RES02" \
    "0x55d398326f99059fF775485246999027B3197955,0xD7B7218D778338Ea05f5Ecce82f86D365E25dBCE,0x05ba2c512788bd95cd6D61D3109c53a14b01c82A,0x1B214e38C5e861c56e12a69b6BAA0B45eFe5C8Eb,0xecCD8B08Ac3B587B7175D40Fb9C60a20990F8D21,0xeccd8b08ac3b587b7175d40fb9c60a20990f8d21,0x04C0f31C0f59496cf195d2d7F1dA908152722DE7,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c" \
    21948016 \
    "Price Manipulation"

# SEAMAN - Fund Loss (expected: ~3s)
test_vulnerability "SEAMAN" \
    "0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e" \
    23467515 \
    "Fund Loss"

# BIGFI - Price Manipulation (expected: ~8m31s = 511s)
test_vulnerability "BIGFI" \
    "0x55d398326f99059fF775485246999027B3197955,0x28ec0B36F0819ecB5005cAB836F4ED5a2eCa4D13,0xd3d4B46Db01C006Fb165879f343fc13174a1cEeB,0xA269556EdC45581F355742e46D2d722c5F3f551a" \
    26685503 \
    "Price Manipulation"

# Additional fast ones from backtesting.md
# Yyds - Fund Loss (expected: ~4s)
test_vulnerability "Yyds" \
    "0x55d398326f99059fF775485246999027B3197955,0x970A76aEa6a0D531096b566340C0de9B027dd39D,0xB19463ad610ea472a886d77a8ca4b983E4fAf245,0xd5cA448b06F8eb5acC6921502e33912FA3D63b12,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0xe70cdd37667cdDF52CabF3EdabE377C58FaE99e9" \
    21157025 \
    "Fund Loss"

# EGD-Finance - Fund Loss (expected: ~2s)
test_vulnerability "EGD-Finance" \
    "0x55d398326f99059fF775485246999027B3197955,0x202b233735bF743FA31abb8f71e641970161bF98,0xa361433E409Adac1f87CDF133127585F8a93c67d,0x16b9a82891338f9bA80E2D6970FddA79D1eb0daE,0x34Bd6Dba456Bc31c2b3393e499fa10bED32a9370,0xc30808d9373093fbfcec9e026457c6a9dab706a7,0x34bd6dba456bc31c2b3393e499fa10bed32a9370,0x93c175439726797dcee24d08e4ac9164e88e7aee" \
    20245522 \
    "Fund Loss"

echo ""
echo "📊 TIME ANALYSIS SUMMARY"
echo "========================"
echo ""

# Generate summary
for test in BEGO LPC RES02 SEAMAN BIGFI Yyds EGD-Finance; do
    if [ "$test" = "BEGO" ]; then
        echo "✅ BEGO: 25s (confirmed)"
        continue
    fi
    
    # Find the smallest time limit where bug was found
    found_time=""
    for time in 5 10 15 20 30 45 60 90 120 180 300; do
        if [ -f "backtest_results/${test}_${time}s.log" ]; then
            if grep -q "Found vulnerabilities" "backtest_results/${test}_${time}s.log" 2>/dev/null; then
                found_time=$time
                break
            fi
        fi
    done
    
    if [ -n "$found_time" ]; then
        actual_time=$(grep -oP "run time: \K[0-9h-]+[0-9m-]+[0-9]+s" "backtest_results/${test}_${found_time}s.log" 2>/dev/null | tail -1)
        exec_rate=$(grep "exec/sec" "backtest_results/${test}_${found_time}s.log" 2>/dev/null | tail -1 | grep -oP "\d+\.?\d*k?" | tail -1)
        echo "✅ $test: Found in ${found_time}s limit (actual: ${actual_time}, ${exec_rate} exec/sec)"
    else
        echo "❌ $test: Not found even with 300s limit"
    fi
done

echo ""
echo "🎯 Recommendations:"
echo "- Fast detection (<30s): Good for MEV scenarios"
echo "- Medium detection (30-120s): May need optimization"
echo "- Slow detection (>120s): Consider targeted mutations"
echo "- Not found: May need oracle improvements"