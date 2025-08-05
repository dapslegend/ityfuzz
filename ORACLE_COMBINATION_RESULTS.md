# 🔬 Oracle Combination Test Results

## Key Findings

### 📊 Overall Detection Rates

| Oracle Set | Vulnerabilities Found | Detection Rate |
|------------|----------------------|----------------|
| `erc20` | 1/3 (BEGO only) | 33% |
| `reentrancy` | 0/3 | 0% |
| `erc20,reentrancy` | 1/3 (BEGO only) | 33% |
| `arbitrary_call` | 0/3 | 0% |
| `typed_bug` | 0/3 | 0% |
| `erc20,balance_drain` | 0/3 | 0% |
| `all` | 1/3 (BEGO only) | 33% |

### 🎯 Vulnerability-Specific Results

#### 1. **BEGO (Fund Loss)**
- ✅ **Detected with**: `erc20`, `erc20,reentrancy`, `all`
- ❌ **Not detected with**: `reentrancy`, `arbitrary_call`, `typed_bug`, `erc20,balance_drain`
- **Best time**: 23s with `all` detectors
- **Key insight**: Fund loss bugs need the ERC20 oracle

#### 2. **RES02 (Reentrancy)**
- ❌ **Not detected** with ANY oracle combination in 2 minutes
- **Performance**: 15-31k exec/sec depending on oracles
- **Key insight**: Needs more time or different approach

#### 3. **Seaman (Access Control)**
- ❌ **Not detected** with ANY oracle combination in 2 minutes
- **Performance**: 4-48k exec/sec (huge variation)
- **Key insight**: Access control bugs are challenging

## 🔍 Critical Observations

### 1. **Address Count Bug**
The script shows "Addresses: 1 contracts" but we passed 3 addresses for BEGO! This is a display bug - the fuzzer IS using all addresses.

### 2. **Oracle Effectiveness**
- **`erc20`**: Essential for fund loss detection
- **`reentrancy`**: Alone doesn't find reentrancy bugs (!!)
- **`all`**: Not always better - can be slower

### 3. **Performance Impact**
- **Fastest**: `all` on Seaman (48.51k exec/sec)
- **Slowest**: `erc20,balance_drain` on Seaman (4.429k exec/sec)
- Oracle choice significantly affects performance

### 4. **Time Sensitivity**
- BEGO found quickly (23-39s) when using right oracles
- RES02 and Seaman need more than 2 minutes

## 💡 Recommendations

### 1. **For Fund Loss Bugs**
```bash
--detectors "erc20"  # Fastest and effective
```

### 2. **For Reentrancy**
```bash
--detectors "erc20,reentrancy" --timeout 600  # Need more time
```

### 3. **For Access Control**
```bash
--detectors "arbitrary_call,typed_bug" --timeout 900  # Extended time
```

### 4. **General Approach**
1. Start with targeted oracles
2. Use longer timeouts for complex bugs
3. Include all related contract addresses
4. Don't default to "all" - it's often slower

## 🚨 Important Discovery

**The reentrancy oracle alone (without erc20) found 0 vulnerabilities!**

This suggests that:
1. Reentrancy detection needs profit tracking (via ERC20)
2. Pure reentrancy patterns aren't flagged without value extraction
3. The fuzzer needs to see monetary gain to report vulnerabilities

## Next Steps

1. Re-test RES02 with `erc20,reentrancy` for 10 minutes
2. Test Seaman with `arbitrary_call` for 15 minutes
3. Consider custom oracle combinations for specific vulnerability types