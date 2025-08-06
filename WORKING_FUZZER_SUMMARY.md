# Working ItyFuzz Auto-Fuzzing System

## ✅ Confirmed Working Configuration

### Key Parameters
- **API Key**: `SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP` (working)
- **Binary**: `./target/debug/ityfuzz` (debug version works)
- **Chain**: `bsc` (lowercase)
- **RPC**: `https://bsc-dataseed.binance.org/`

### Correct Command Format
```bash
./target/debug/ityfuzz evm \
    -t "contract1,contract2,token1,token2" \  # All addresses in ONE -t parameter
    -c bsc \                                   # Lowercase
    --onchain-block-number <BLOCK> \
    -f \                                       # Fork mode
    --panic-on-bug \                          # Stop on first bug
    --detectors "erc20" \                     # Run each detector separately
    --work-dir <WORK_DIR> \
    --onchain-etherscan-api-key "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP" \
    --onchain-url "https://bsc-dataseed.binance.org/"
```

## 🎯 Proven Vulnerabilities

### BEGO Contract
- **Address**: 0x68Cc90351a79A4c10078FE021bE430b7a12aaA09
- **Block**: 22315679
- **Detector**: erc20
- **Profit**: 2.813 ETH
- **Status**: ✅ Confirmed working

## 📁 System Components

### 1. `universal_contract_fuzzer.py`
- Finds contracts from blockchain
- Discovers tokens automatically
- **Runs each detector separately** (key fix!)
- Preserves work directories per contract/detector
- Uses correct API key

### 2. Detector Strategy
Run these detectors separately:
- `erc20` - Most effective, finds token vulnerabilities
- `reentrancy` - For reentrancy bugs
- `erc20,reentrancy` - Combined
- `arbitrary_call` - For arbitrary calls
- `typed_bug` - For type confusion
- `erc20,balance_drain` - For balance draining

### 3. Work Directory Structure
```
work_dirs/
├── {address}_{detector}_{block}_{timestamp}/
│   ├── corpus/
│   ├── logs/
│   └── vulnerability_metadata.json
```

## 🚨 Common Issues & Solutions

### 1. ABI Parsing Error
- **Error**: `failed to parse abis file: Error("expected value", line: 1, column: 1)`
- **Solution**: Use the correct API key: `SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP`

### 2. Release Build Fails
- **Error**: Z3 compilation errors
- **Solution**: Use debug build - it works fine for fuzzing

### 3. Index Out of Bounds
- **Error**: `index out of bounds: the len is 0 but the index is 28`
- **Note**: This happens with some contracts at current block, but doesn't affect vulnerability detection at correct blocks

## 🎯 Running the System

### Test a specific contract:
```bash
./test_known_vulnerable.sh
```

### Run full auto-fuzzer:
```bash
python3 universal_contract_fuzzer.py
```

### Continuous fuzzing:
```bash
./run_continuous_fuzzing.sh
```

## ✅ Verification

The system successfully found the BEGO vulnerability:
```
😊😊 Found vulnerabilities! 
[Fund Loss]: Anyone can earn 2.813 ETH by interacting with the provided contracts
```

This confirms that:
1. The fuzzer works correctly
2. The API key is valid
3. The detector logic is correct
4. Work directories are preserved for MEV exploitation