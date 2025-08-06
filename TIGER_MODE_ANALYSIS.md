# Tiger Mode Analysis

## Key Findings

### 1. ItyFuzz IS Working

When run with the correct parameters, ItyFuzz successfully finds vulnerabilities:
- BEGO vulnerability: 12.037 ETH profit (at block 22315679)
- The debug binary works correctly

### 2. Configuration Differences

The tiger script (`run_tiger_mode.sh`) has a slightly different configuration:

**Tiger Script BEGO Config:**
```bash
# First address is WBNB, not BEGO contract
"0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972"
```

**Working BEGO Config:**
```bash
# First address is BEGO contract
"0x68Cc90351a79A4c10078FE021bE430b7a12aaA09,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972"
```

### 3. Issues Identified

1. **Timeout Too Short**: 15 seconds is not enough for complex fuzzing
2. **RPC Errors**: Using ankr.com RPC sometimes causes issues
3. **Address Order**: The order of addresses matters for vulnerability detection

### 4. Working Command

This command successfully finds the BEGO vulnerability:

```bash
./target/debug/ityfuzz evm \
    -t "0x68Cc90351a79A4c10078FE021bE430b7a12aaA09,0x88503F48e437a377f1aC2892cBB3a5b09949faDd,0xc342774492b54ce5F8ac662113ED702Fc1b34972" \
    -c bsc \
    --onchain-block-number 22315679 \
    -f \
    --panic-on-bug \
    --onchain-etherscan-api-key "SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP" \
    --onchain-url "https://bsc-dataseed.binance.org/" \
    --detectors "erc20" \
    --work-dir "work_dir"
```

### 5. Why Scanner Missed Vulnerabilities

1. **Wrong Target Order**: Tiger script doesn't include vulnerable contract as first target
2. **Timeout Issues**: 15 seconds often kills the process before finding vulnerabilities
3. **RPC Reliability**: ankr.com RPC sometimes fails with "Unexpected RPC error"

### 6. Recommendations

1. **Fix Tiger Script**: Update BEGO configuration to include the actual contract
2. **Increase Timeout**: Use at least 60 seconds for each test
3. **Use Reliable RPC**: Stick with `https://bsc-dataseed.binance.org/`
4. **Include All Targets**: Make sure vulnerable contracts are in the target list

### 7. Other Test Contracts

The other contracts (BBOX, FAPEN, SEAMAN) might have similar configuration issues. Each needs to be verified with the correct target addresses.

## Conclusion

ItyFuzz is working correctly. The issue is with the test configuration in the tiger script. When given the correct addresses and sufficient time, it successfully finds vulnerabilities.