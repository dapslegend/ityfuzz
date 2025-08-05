#!/bin/bash

# BSC Backtest Runner with AGGRESSIVE optimized ityfuzz
# Maximum runtime: 60 seconds for MEV safety

API_KEY="SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
RPC_URL="http://159.198.35.169:8545"

# Set environment variables for RPC
export ETH_RPC_URL=$RPC_URL
export BSC_RPC_URL=$RPC_URL
export BSC_ETHERSCAN_API_KEY=$API_KEY

# Rate limiting prevention
export RPC_RETRY_DELAY=100  # ms between retries
export RPC_MAX_RETRIES=5
export RPC_RATE_LIMIT_DELAY=50  # ms between requests

echo "🚀 Running AGGRESSIVE BSC Backtest with optimized ityfuzz..."
echo "⏱️  Maximum runtime: 60 seconds"
echo "🔧 RPC: ${RPC_URL}"
echo "🎯 Focus: PROFITABLE PATHS & EXPLOITS"
echo ""

# Test BEGO - Fund Loss (should find in ~20s, but we found it in 21s)
echo "📊 Testing BEGO exploit (Fund Loss) - 30s timeout..."
timeout 30s ./target/release/ityfuzz evm \
    -t 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972 \
    -c bsc \
    --onchain-url ${RPC_URL} \
    --onchain-block-number 22315679 \
    -f \
    --panic-on-bug \
    -d all \
    --onchain-etherscan-api-key ${API_KEY} \
    2>&1 | tee bego_aggressive.log

if grep -q "Fund Loss" bego_aggressive.log; then
    echo "✅ BEGO exploit found!"
    grep -A5 "Fund Loss" bego_aggressive.log
else
    echo "❌ BEGO exploit not found within time limit"
fi

echo ""

# Test LPC - Fund Loss (should find in ~4s)
echo "📊 Testing LPC exploit (Fund Loss) - 10s timeout..."
timeout 10s ./target/release/ityfuzz evm \
    -t 0x1e813fa05739bf145c1f182cb950da7af046778d,0x1E813fA05739Bf145c1F182CB950dA7af046778d,0x2ecD8Ce228D534D8740617673F31b7541f6A0099,0xcfb7909b7eb27b71fdc482a2883049351a1749d7 \
    -c bsc \
    --onchain-url ${RPC_URL} \
    --onchain-block-number 19852596 \
    -f \
    --panic-on-bug \
    -d all \
    --onchain-etherscan-api-key ${API_KEY} \
    2>&1 | tee lpc_aggressive.log

if grep -q "Fund Loss" lpc_aggressive.log; then
    echo "✅ LPC exploit found!"
    grep -A5 "Fund Loss" lpc_aggressive.log
else
    echo "❌ LPC exploit not found within time limit"
fi

echo ""

# Test RES02 - Price Manipulation (should find in ~2s)
echo "📊 Testing RES02 exploit (Price Manipulation) - 10s timeout..."
timeout 10s ./target/release/ityfuzz evm \
    -t 0x55d398326f99059fF775485246999027B3197955,0xD7B7218D778338Ea05f5Ecce82f86D365E25dBCE,0x05ba2c512788bd95cd6D61D3109c53a14b01c82A,0x1B214e38C5e861c56e12a69b6BAA0B45eFe5C8Eb,0xecCD8B08Ac3B587B7175D40Fb9C60a20990F8D21,0xeccd8b08ac3b587b7175d40fb9c60a20990f8d21,0x04C0f31C0f59496cf195d2d7F1dA908152722DE7,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c \
    -c bsc \
    --onchain-url ${RPC_URL} \
    --onchain-block-number 21948016 \
    -f \
    --panic-on-bug \
    -d all \
    --onchain-etherscan-api-key ${API_KEY} \
    2>&1 | tee res02_aggressive.log

if grep -q "Price Manipulation" res02_aggressive.log; then
    echo "✅ RES02 exploit found!"
    grep -A5 "Price Manipulation" res02_aggressive.log
else
    echo "❌ RES02 exploit not found within time limit"
fi

echo ""

# Test SEAMAN - Fund Loss (should find in ~3s)
echo "📊 Testing SEAMAN exploit (Fund Loss) - 10s timeout..."
timeout 10s ./target/release/ityfuzz evm \
    -t 0x55d398326f99059fF775485246999027B3197955,0x6bc9b4976ba6f8C9574326375204eE469993D038,0x6637914482670f91F43025802b6755F27050b0a6,0xDB95FBc5532eEb43DeEd56c8dc050c930e31017e \
    -c bsc \
    --onchain-url ${RPC_URL} \
    --onchain-block-number 23467515 \
    -f \
    --panic-on-bug \
    -d all \
    --onchain-etherscan-api-key ${API_KEY} \
    2>&1 | tee seaman_aggressive.log

if grep -q "Fund Loss" seaman_aggressive.log; then
    echo "✅ SEAMAN exploit found!"
    grep -A5 "Fund Loss" seaman_aggressive.log
else
    echo "❌ SEAMAN exploit not found within time limit"
fi

echo ""
echo "🏁 AGGRESSIVE Backtest completed!"
echo "📈 Performance Summary:"
grep "exec/sec" *_aggressive.log | tail -5