# MEV Scanner Status Report

## Current Status ✅ RUNNING

### Active Processes
- `mev_current_block_scanner.py` - Scanning current BSC blocks for contracts and fuzzing them
- `proven_mev_scanner.py` - Also running in background

### Key Points

1. **Historical RPC Issue**: The historical RPC (159.138.42.234:18545) is timing out, so we're using the public BSC RPC instead.

2. **Current Block Scanning**: 
   - Using public RPC: `https://bsc-dataseed.binance.org/`
   - Current BSC block: ~56632071
   - Scanning last 5 blocks for new contracts
   - Fuzzing each contract with 5 detectors: erc20, reentrancy, arbitrary_call, typed_bug, balance_drain

3. **ABI Issue**: The ABI parsing works fine - the previous error was due to:
   - Invalid detector name ("ci" is not valid)
   - Need to use valid detectors: all, erc20, reentrancy, etc.

4. **Directory Structure**:
   ```
   mev/
   ├── work_dirs/          # ItyFuzz working directories
   ├── vulnerability_logs/ # Logs of found vulnerabilities
   ├── fuzzing_logs/      # Detailed fuzzing reports
   └── logs/              # Session logs
   ```

5. **Configuration**:
   - API Key: SCVG9V74WV6VBZN583QZ9D3AW9VF45IMZP (working)
   - Binary: ./target/debug/ityfuzz
   - Timeout: 60 seconds per detector
   - Duration: 20 minutes total

### Known Working Configuration

```bash
./target/debug/ityfuzz evm \
    -t "CONTRACT,TOKEN1,TOKEN2" \
    -c bsc \
    --onchain-block-number BLOCK \
    -f \
    --panic-on-bug \
    --detectors "DETECTOR" \
    --work-dir "WORK_DIR" \
    --onchain-etherscan-api-key "API_KEY" \
    --onchain-url "RPC_URL"
```

### Monitoring

Check scanner output:
```bash
tail -f mev/scanner_output.log
```

Check for vulnerabilities:
```bash
ls -la mev/vulnerability_logs/
```

Check session logs:
```bash
cat mev/logs/session_*.log
```

### Notes

- The BEGO vulnerability (from backtest) is NOT present at current block - it was fixed after block 22315679
- The scanner is continuously finding and fuzzing new contracts from recent blocks
- Each contract is tested with multiple detectors to find different vulnerability types