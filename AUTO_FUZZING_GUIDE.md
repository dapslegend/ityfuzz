# Auto-Fuzzing System Guide

## Overview

This system automatically finds and fuzzes smart contracts on BSC using:
- **Historical RPC** (`http://159.198.35.169:8545`) - For finding contracts and analyzing them
- **Public RPC** (`https://bsc-dataseed.binance.org/`) - For fuzzing at current block
- **Etherscan API v2** - For finding verified contracts (chainId: 56)

## Scripts Created

### 1. `bsc_auto_fuzzer.py`
Uses Etherscan API v2 to find verified contracts with vulnerable functions.

**Features:**
- Fetches verified contracts from Etherscan API v2
- Analyzes ABIs for vulnerable functions (withdraw, skim, harvest, etc.)
- Gets associated tokens from token transfers
- Fuzzes contracts for 1 minute each
- Generates detailed reports

**Usage:**
```bash
python3 bsc_auto_fuzzer.py
```

### 2. `smart_contract_hunter.py`
Scans historical RPC blocks to find contracts with vulnerable selectors.

**Features:**
- Scans recent blocks from historical RPC
- Identifies contracts by checking bytecode for vulnerable selectors
- Analyzes contract storage to find associated tokens
- Fuzzes using public RPC at current block
- Parallel scanning for efficiency

**Usage:**
```bash
python3 smart_contract_hunter.py
```

### 3. `auto_fuzz_contracts.py`
Comprehensive scanner that combines multiple approaches.

**Features:**
- Scans blocks for contract deployments
- Checks for token interfaces and vulnerable functions
- Finds liquidity pairs
- Multi-threaded scanning

## How It Works

### Step 1: Find Contracts
```python
# From historical RPC - get contracts in recent blocks
contracts = scanner.find_contracts_in_block(block_num)

# From Etherscan API v2 - get verified contracts
contracts = finder.get_verified_contracts(page=1, offset=100)
```

### Step 2: Analyze Contracts
```python
# Check for vulnerable functions
vulnerable_selectors = {
    "3ccfd60b": "withdraw()",
    "853828b6": "withdrawAll()",
    "db2e21bc": "emergencyWithdraw()",
    "bc25cf77": "skim(address)",
    "69328dec": "harvest(address,uint256)"
}
```

### Step 3: Find Associated Tokens
```python
# Check storage slots for token addresses
for slot in range(10):
    value = cast_storage(contract, slot)
    if is_token(value):
        tokens.append(value)

# Get tokens from Etherscan transfers
tokens = get_recent_token_transfers(contract)
```

### Step 4: Fuzz with ItyFuzz
```python
# Build command with all necessary tokens
cmd = [
    "./target/debug/cli",
    "-t", contract_address,
    "-t", wbnb_address,
    "-t", token1,
    "-t", token2,
    "-c", "BSC",
    "--onchain-block-number", current_block,
    "-f", "-i", "-p",
    "--run-forever", "60"
]
```

## Key Insights

### 1. Token Association is Critical
ItyFuzz needs to know which tokens a contract interacts with. We find these by:
- Checking storage slots for addresses
- Analyzing token transfer history
- Including common tokens (WBNB, BUSD, USDT)

### 2. Block Number Strategy
- Use historical RPC to find and analyze contracts
- Use public RPC's current block for fuzzing
- This ensures we fuzz against live state

### 3. Vulnerable Function Patterns
Most profitable vulnerabilities have:
- `withdraw()` or `withdrawAll()` functions
- No access control
- Interaction with DEX routers

## Example Output

```
=== Smart Contract Hunter ===

Historical RPC: Block 55442460
Public RPC: Block 56619200

🔍 Hunting for contracts...
  Block 55442360: Found 3 potential targets
  Block 55442361: Found 1 potential targets

📊 Found 4 potential vulnerable contracts

📋 Analyzing contracts...
  ✓ 0x1234...5678: withdraw(), withdrawAll()
    💰 Balance: 10.5432 ETH
  ✓ 0xabcd...ef01: emergencyWithdraw(), skim(address)

🎯 2 contracts ready for fuzzing

🚀 Starting fuzzing campaign...

[1/2] 0x1234...5678
🔍 Fuzzing 0x1234...5678...
   Functions: withdraw(), withdrawAll()
   🚨 VULNERABLE! Profit: 10.5432 ETH

[2/2] 0xabcd...ef01
🔍 Fuzzing 0xabcd...ef01...
   Functions: emergencyWithdraw(), skim(address)
   ✅ Clean

==================================================
📊 HUNT COMPLETE
==================================================
Contracts found: 4
Contracts analyzed: 2
Contracts fuzzed: 2
Vulnerabilities found: 1

💰 Total potential profit: 10.5432 ETH

🚨 Vulnerable contracts:
  0x1234...5678: 10.5432 ETH

📄 Report saved to: hunt_report_1735000000.json
```

## Running Continuous Fuzzing

To continuously hunt for vulnerabilities:

```bash
# Run every hour
while true; do
    python3 smart_contract_hunter.py
    python3 bsc_auto_fuzzer.py
    sleep 3600
done
```

## Safety Notes

1. **Always verify findings** - Re-run fuzzing before executing
2. **Check gas costs** - Some exploits may not be profitable after gas
3. **Use Flashbots/Private mempools** - Avoid frontrunning
4. **Test on fork first** - Use Anvil to verify exploit

## Optimization Tips

1. **Prioritize contracts with balance** - More likely to be profitable
2. **Focus on recent deployments** - Less likely to be already exploited
3. **Check liquidity** - Ensure tokens can be swapped
4. **Monitor gas prices** - Execute when gas is low

This system provides automated vulnerability discovery on BSC, combining multiple data sources to maximize coverage and using ItyFuzz's powerful fuzzing capabilities to find exploitable bugs.