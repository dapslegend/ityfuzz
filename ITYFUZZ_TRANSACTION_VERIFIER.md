# ItyFuzz Transaction Verifier

## Overview
A verification layer that:
1. Decodes ItyFuzz exploit transactions
2. Simulates with REVM before execution
3. Verifies actual profitability from EOA

## Architecture

```rust
use revm::{Database, EVM, Env};
use ethers::types::{Transaction, U256};

pub struct ExploitVerifier {
    fork_url: String,
    block_number: u64,
}

impl ExploitVerifier {
    /// Verify if ItyFuzz exploit is actually profitable
    pub async fn verify_exploit(
        &self,
        ityfuzz_trace: &str,
        from_address: Address,
    ) -> Result<VerificationResult, Error> {
        // 1. Parse ItyFuzz trace
        let transactions = parse_ityfuzz_trace(ityfuzz_trace)?;
        
        // 2. Setup REVM with fork
        let mut evm = EVM::new();
        let db = ForkDatabase::new(&self.fork_url, self.block_number).await?;
        evm.database(db);
        
        // 3. Get initial balance
        let initial_balance = evm.balance(from_address)?;
        
        // 4. Simulate transactions
        let mut total_gas_used = U256::zero();
        for tx in transactions {
            let result = evm.call_raw(
                from_address,
                tx.to,
                tx.data,
                tx.value,
                tx.gas,
                false, // Not a static call
            )?;
            
            if !result.is_success() {
                return Ok(VerificationResult::Failed);
            }
            
            total_gas_used += result.gas_used;
        }
        
        // 5. Calculate final profit
        let final_balance = evm.balance(from_address)?;
        let gas_cost = total_gas_used * evm.env().gas_price;
        
        let net_profit = if final_balance > initial_balance {
            final_balance - initial_balance - gas_cost
        } else {
            U256::zero()
        };
        
        Ok(VerificationResult {
            profitable: net_profit > U256::zero(),
            net_profit,
            gas_used: total_gas_used,
            transactions: transactions.len(),
        })
    }
}

/// Parse ItyFuzz output format
fn parse_ityfuzz_trace(trace: &str) -> Result<Vec<Transaction>, Error> {
    // Parse format like:
    // [Sender] 0x123...
    //    └─[1] Contract.function(args)
    
    let mut transactions = Vec::new();
    // ... parsing logic ...
    Ok(transactions)
}
```

## Integration with ItyFuzz

1. **Capture ItyFuzz output**:
```bash
ityfuzz ... > exploit.trace
```

2. **Verify before execution**:
```rust
let verifier = ExploitVerifier::new(rpc_url, block);
let result = verifier.verify_exploit(&trace, my_address).await?;

if result.profitable && result.net_profit > min_profit {
    execute_exploit(transactions);
}
```

## Benefits
- No more false positives
- Accurate profit calculation
- Gas cost consideration
- Multi-transaction verification
- EOA perspective validation