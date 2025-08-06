# ItyFuzz Auto-Fuzzing System Summary

## Overview

The system automatically finds and fuzzes ALL smart contracts on BSC, with each project saving its work directory for MEV exploitation.

## Key Components

### 1. **universal_contract_fuzzer.py**
The main fuzzing engine that:
- Finds contracts from multiple sources (historical RPC blocks, Etherscan API v2)
- Discovers associated tokens automatically
- Fuzzes each contract for 1 minute using ItyFuzz
- Saves work directories for vulnerable contracts
- Generates detailed reports

### 2. **run_continuous_fuzzing.sh**
Bash script for continuous operation:
- Runs fuzzing rounds every 30 minutes
- Organizes logs and vulnerabilities
- Tracks total vulnerabilities found

## How It Works

### Contract Discovery
1. **Block Scanning**: Scans recent blocks from historical RPC
2. **Etherscan API v2**: Gets verified contracts (chainId 56)
3. **No Pre-filtering**: Fuzzes ALL contracts - lets ItyFuzz detect vulnerabilities

### Token Discovery
- **Storage Slot Analysis**: Checks first 20 storage slots for token addresses
- **Etherscan Token Transfers**: Finds tokens the contract has interacted with
- **Common Tokens**: Always includes WBNB, BUSD, USDT, USDC, DAI

### Fuzzing Strategy
- **Historical RPC** (159.198.35.169:8545): For finding and analyzing contracts
- **Public RPC** (bsc-dataseed.binance.org): For fuzzing at current block
- **Work Directory**: Each contract gets unique directory preserving corpus/findings

## Directory Structure
```
work_dirs/
├── {contract_address}_{block}_{timestamp}/
│   ├── corpus/              # ItyFuzz corpus
│   ├── logs/                # Fuzzing logs
│   └── vulnerability_metadata.json  # MEV metadata

vulnerability_logs/
├── vuln_{address}_{timestamp}.log  # Full vulnerability details

fuzzing_logs/
├── universal_fuzz_report_{timestamp}.json  # Summary reports
```

## Running the System

### One-time Run (20 minutes):
```bash
python3 universal_contract_fuzzer.py
```

### Continuous Fuzzing:
```bash
./run_continuous_fuzzing.sh
```

## Key Features

1. **No Manual Vulnerability Detection**: ItyFuzz handles all detection
2. **Automatic Token Discovery**: Multiple methods to find associated tokens
3. **Work Directory Preservation**: Each vulnerable contract's state saved for MEV
4. **Parallel Scanning**: Multi-threaded block scanning for efficiency
5. **Comprehensive Logging**: All findings saved with metadata

## MEV Integration

When a vulnerability is found:
1. Full log saved to `vulnerability_logs/`
2. Work directory preserved with corpus
3. Metadata file created with:
   - Contract address
   - Block number
   - Profit potential
   - Associated tokens
   - Timestamp

This allows MEV bots to:
- Re-run specific test cases
- Analyze exact vulnerability conditions
- Execute profitable transactions

## Current Status

The system is fully operational and can:
- Find contracts from blockchain data
- Discover associated tokens automatically
- Fuzz with ItyFuzz for vulnerability detection
- Preserve all data needed for MEV exploitation

Each fuzzing session runs for the specified duration (default 20 minutes), testing as many contracts as possible within that timeframe.