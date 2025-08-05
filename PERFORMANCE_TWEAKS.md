# 🚀 Simple Performance Tweaks for ItyFuzz

## 1. Faster Complex Transaction Execution

### Current Bottlenecks:
- Complex transactions with multiple calls are slow
- State lookups repeated unnecessarily
- Cache misses on hot contracts

### Simple Fixes:
```rust
// Add to execution config
--corpus-size 100        // Smaller corpus = faster mutation
--power-multiplier 16    // More aggressive fuzzing
--fork-url FAST_RPC      // Use fastest RPC endpoint
```

## 2. Objectives Not Showing (Bug Fix)

The `objectives: 0` issue happens because:
- Objectives only increment when NEW coverage is found
- If fuzzer gets stuck in local optimum, no new objectives
- Need to track ANY bug found, not just coverage

## 3. Chains Without Flashloans

For Anvil/local chains:
- Disable flashloan requirement with flag
- Use sender's balance instead
- Allow fuzzer to use test ETH

## 4. Optimal Configuration

```bash
# Fast configuration for complex contracts
ityfuzz evm \
  -t "CONTRACTS" \
  -c CHAIN \
  --onchain-block-number BLOCK \
  -f \
  --panic-on-bug \
  --corpus-size 50 \         # Smaller = faster
  --seed-len 32 \            # Shorter seeds
  --power-multiplier 32 \    # More aggressive
  --max-depth 3 \            # Limit call depth
  --work-dir output
```

## 5. Key Performance Settings

```bash
# Environment variables for speed
export RUST_LOG=error           # Less logging
export RAYON_NUM_THREADS=8      # More parallelism

# Execution flags
--no-state-comp                 # Skip state comparison
--fast-mode                     # Prioritize speed
--aggressive-preset             # Use aggressive settings
```

## 6. Why These Work

1. **Smaller corpus** = Less to mutate each cycle
2. **Higher power multiplier** = Focus on promising inputs
3. **Limited depth** = Avoid infinite recursion
4. **Less logging** = Significant speedup
5. **More threads** = Better CPU utilization