#!/bin/bash

# BSC Backtest Runner with optimized ityfuzz
# Maximum runtime: 60 seconds for MEV safety

API_KEY="SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP"
RPC_URL="http://159.198.35.169:8545"
BACKUP_RPC="https://bsc.publicnode.com"
MAX_TIME=60

echo "🚀 Running BSC Backtest with optimized ityfuzz..."
echo "⏱️  Maximum runtime: ${MAX_TIME} seconds"
echo "🔧 RPC: ${RPC_URL} (backup: ${BACKUP_RPC})"
echo ""

# Test BEGO - Fund Loss (should find in ~20s)
echo "📊 Testing BEGO exploit (Fund Loss)..."
timeout ${MAX_TIME}s ./target/release/ityfuzz evm \
    -t 0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972 \
    -c bsc \
    --onchain-url ${RPC_URL} \
    --onchain-block-number 22315679 \
    -f \
    --panic-on-bug \
    -d all \
    --onchain-etherscan-api-key ${API_KEY} \
    2>&1 | tee bego_test_optimized.log

# Check if bug was found
if grep -q "Fund Loss" bego_test_optimized.log; then
    echo "✅ BEGO exploit found!"
else
    echo "❌ BEGO exploit not found within time limit"
fi

echo ""

# Test LPC - Fund Loss (should find in ~4s)
echo "📊 Testing LPC exploit (Fund Loss)..."
timeout 30s ./target/release/ityfuzz evm \
    -t 0x1e813fa05739bf145c1f182cb950da7af046778d,0x1E813fA05739Bf145c1F182CB950dA7af046778d,0x2ecD8Ce228D534D8740617673F31b7541f6A0099,0xcfb7909b7eb27b71fdc482a2883049351a1749d7 \
    -c bsc \
    --onchain-url ${RPC_URL} \
    --onchain-block-number 19852596 \
    -f \
    --panic-on-bug \
    -d all \
    --onchain-etherscan-api-key ${API_KEY} \
    2>&1 | tee lpc_test_optimized.log

if grep -q "Fund Loss" lpc_test_optimized.log; then
    echo "✅ LPC exploit found!"
else
    echo "❌ LPC exploit not found within time limit"
fi

echo ""

# Test RES02 - Price Manipulation (should find in ~2s)
echo "📊 Testing RES02 exploit (Price Manipulation)..."
timeout 30s ./target/release/ityfuzz evm \
    -t 0x55d398326f99059fF775485246999027B3197955,0xD7B7218D778338Ea05f5Ecce82f86D365E25dBCE,0x05ba2c512788bd95cd6D61D3109c53a14b01c82A,0x1B214e38C5e861c56e12a69b6BAA0B45eFe5C8Eb,0xecCD8B08Ac3B587B7175D40Fb9C60a20990F8D21,0xeccd8b08ac3b587b7175d40fb9c60a20990f8d21,0x04C0f31C0f59496cf195d2d7F1dA908152722DE7,0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c \
    -c bsc \
    --onchain-url ${RPC_URL} \
    --onchain-block-number 21948016 \
    -f \
    --panic-on-bug \
    -d all \
    --onchain-etherscan-api-key ${API_KEY} \
    2>&1 | tee res02_test_optimized.log

if grep -q "Price Manipulation" res02_test_optimized.log; then
    echo "✅ RES02 exploit found!"
else
    echo "❌ RES02 exploit not found within time limit"
fi

echo ""
echo "🏁 Backtest completed! Check logs for details."