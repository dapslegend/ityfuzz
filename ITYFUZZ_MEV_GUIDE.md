# ItyFuzz MEV Bot Guide

This guide explains how to convert ItyFuzz vulnerability findings into executable MEV transactions.

## Overview

ItyFuzz finds vulnerabilities, but the output needs to be converted into actual transactions. This toolkit provides:

1. **Log Parser** - Extracts vulnerability details from ItyFuzz logs
2. **Transaction Simulator** - Simulates exploits using Anvil fork
3. **MEV Bot** - Executes profitable vulnerabilities on-chain

## Found Vulnerabilities Summary

From the logs, we found multiple vulnerabilities with profits ranging from 0.004 ETH to 357,564 ETH:

### Major Findings:
- **BEGO**: Up to 357,564.692 ETH profit
- **SEAMAN**: Up to 30,179.434 ETH profit  
- **BBOX**: Various smaller profits
- **LPC**: 0.307 ETH profit
- **FAPEN**: Small profits

## Installation

```bash
# Install Python dependencies
pip install -r requirements_mev.txt

# Install Foundry (for Anvil)
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Make scripts executable
chmod +x ityfuzz_mev_bot.py ityfuzz_simulator.py
```

## Usage

### 1. Parse ItyFuzz Logs

The MEV bot can parse ItyFuzz logs to extract vulnerability details:

```bash
# Parse and simulate only
python ityfuzz_mev_bot.py bego_test_extended.log --min-profit 1.0

# Parse and execute (BE CAREFUL!)
python ityfuzz_mev_bot.py bego_test_extended.log --execute --private-key YOUR_KEY
```

### 2. Simulate with Anvil

For accurate simulation using a forked blockchain:

```bash
# Simulate BEGO vulnerability
python ityfuzz_simulator.py bego_test_extended.log --chain bsc --block 22315679

# The simulator will:
# 1. Fork BSC at block 22315679
# 2. Execute the exact transaction sequence
# 3. Calculate actual profit after gas costs
```

### 3. Understanding ItyFuzz Output

ItyFuzz vulnerabilities follow this pattern:

```
😊😊 Found vulnerabilities!

================ Description ================
[Fund Loss]: Anyone can earn 357564.692 ETH by interacting with the provided contracts

================ Trace ================
[Sender] 0x68Dd4F5AC792eAaa5e36f4f4e0474E0625dc9024
   ├─[1] Router.swapExactETHForTokens{value: 2199.9978 ether}(0, path:(WETH → 0xc342774492b54ce5F8ac662113ED702Fc1b34972), address(this), block.timestamp);
   └─[1] Router.swapExactETHForTokens{value: 0}(0, path:(WETH → 0xc342774492b54ce5F8ac662113ED702Fc1b34972), address(this), block.timestamp);
```

### 4. Transaction Structure

The exploit typically involves:

1. **Swap transactions** via DEX routers (Uniswap, PancakeSwap)
2. **Direct contract calls** to vulnerable contracts
3. **Specific sequences** that trigger the vulnerability

### 5. Example: BEGO Vulnerability

The BEGO vulnerability on BSC involves:
- Contract: 0x88503F48e437a377f1aC2892cBB3a5b09949faDd (Router/Pair)
- Token: 0xc342774492b54ce5F8ac662113ED702Fc1b34972
- Action: Two swaps that drain funds

```python
# Transactions extracted:
1. Router.swapExactETHForTokens(value=2199.9978 ETH, path=[WBNB, TOKEN])
2. Router.swapExactETHForTokens(value=0 ETH, path=[WBNB, TOKEN])
```

## Safety Considerations

⚠️ **WARNING**: These are real vulnerabilities on mainnet. Consider:

1. **Legal implications** - Exploiting vulnerabilities may be illegal
2. **Ethical considerations** - Notify projects before exploiting
3. **Technical risks** - Transactions may fail or be front-run
4. **Financial risks** - You may lose funds if simulation is inaccurate

## Best Practices

1. **Always simulate first** using Anvil fork
2. **Start with small amounts** to test
3. **Use flashloans** when possible to minimize capital requirements
4. **Monitor mempool** for competing transactions
5. **Use private mempools** (Flashbots) to avoid front-running

## Advanced Features

### Custom Router Addresses

Edit the router mappings in the scripts:

```python
self.routers = {
    "bsc": {
        "PancakeSwap": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
        "Your_Router": "0x..."
    }
}
```

### Flashloan Integration

For capital-efficient execution:

```python
# Wrap exploit in flashloan
flashloan_provider = "0x..."  # AAVE, DyDx, etc.
amount_to_borrow = Web3.to_wei(1000, 'ether')
```

### MEV Bundle Construction

For Ethereum mainnet using Flashbots:

```python
bundle = [
    flashloan_tx,
    exploit_tx_1,
    exploit_tx_2,
    repay_flashloan_tx
]
```

## Troubleshooting

### Common Issues:

1. **"No vulnerability found"** - Check log format matches expected pattern
2. **"Simulation failed"** - Verify block number and RPC endpoint
3. **"Not profitable"** - Gas costs may exceed profit on small vulnerabilities
4. **"Transaction reverted"** - Contract state may have changed

### Debug Mode:

```bash
# Enable debug logging
export PYTHONPATH=.
export LOG_LEVEL=DEBUG
python ityfuzz_mev_bot.py --debug
```

## Real Transaction Examples

From the logs, here are actual profitable transactions found:

1. **BEGO (357,564 ETH)**:
   - Swap 2199.9978 ETH through router
   - Follow with 0 ETH swap to trigger vulnerability

2. **SEAMAN (30,179 ETH)**:
   - Complex sequence involving multiple addresses
   - Requires specific contract state

3. **Small Profits**:
   - Many vulnerabilities yield < 1 ETH
   - May not be profitable after gas costs

## Conclusion

ItyFuzz is incredibly powerful at finding vulnerabilities, and this toolkit helps convert those findings into actionable MEV opportunities. Always:

1. Verify findings through simulation
2. Consider ethical implications
3. Account for gas costs and MEV competition
4. Test thoroughly before mainnet execution

Remember: With great power comes great responsibility. Use these tools ethically and legally.