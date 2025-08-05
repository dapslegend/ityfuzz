use std::collections::HashMap;

use bytes::Bytes;
use itertools::Itertools;
use revm_primitives::Bytecode;
use tracing::debug;

use crate::{
    evm::{
        input::{ConciseEVMInput, EVMInput, EVMInputT},
        oracle::{EVMBugResult},
        types::{EVMAddress, EVMFuzzState, EVMOracleCtx, EVMQueueExecutor, EVMU256, EVMU512},
        vm::EVMState,
    },
    generic_vm::vm_state::VMStateT,
    input::VMInputT,
    oracle::{Oracle, OracleCtx},
    state::HasExecutionResult,
};

/// Oracle that detects when a contract's balance is drained
pub struct BalanceDrainOracle {
    /// Track initial balances of contracts
    initial_balances: std::cell::RefCell<HashMap<EVMAddress, EVMU256>>,
    /// Addresses of target contracts to monitor
    target_addresses: Vec<EVMAddress>,
}

impl BalanceDrainOracle {
    pub fn new() -> Self {
        Self {
            initial_balances: std::cell::RefCell::new(HashMap::new()),
            target_addresses: Vec::new(),
        }
    }
    
    pub fn add_target(&mut self, addr: EVMAddress) {
        self.target_addresses.push(addr);
    }
}

impl Oracle<EVMState, EVMAddress, Bytecode, Bytes, EVMAddress, EVMU256, Vec<u8>, EVMInput, EVMFuzzState, ConciseEVMInput, EVMQueueExecutor> 
    for BalanceDrainOracle 
{
    fn transition(&self, _ctx: &mut EVMOracleCtx<'_>, _stage: u64) -> u64 {
        0
    }

    fn oracle(&self, ctx: &mut EVMOracleCtx<'_>, _stage: u64) -> Vec<u64> {
        let mut bugs = vec![];
        
        // Get pre and post states
        let pre_state = ctx.fuzz_state.get_execution_result().new_state.state.clone();
        let post_state = unsafe {
            ctx.post_state
                .as_any()
                .downcast_ref_unchecked::<EVMState>()
        };
        
        // Get the contract being called
        let target = ctx.input.get_contract();
        
        // Get balances from state
        let pre_balance = pre_state.balance.get(&target).cloned().unwrap_or(EVMU256::ZERO);
        let post_balance = post_state.balance.get(&target).cloned().unwrap_or(EVMU256::ZERO);
        
        // Check if balance decreased
        if post_balance < pre_balance {
                let loss = pre_balance - post_balance;
                
                // If loss is more than 0.0001 ETH, check for profit
                if loss > EVMU256::from(100_000_000_000_000u128) { // > 0.0001 ETH
                    debug!(
                        "Balance drain detected! Contract {:?} lost {} wei ({} ETH)",
                        target,
                        loss,
                        loss / EVMU256::from(1_000_000_000_000_000_000u128)
                    );
                    
                    // Check if attacker profited
                    let caller = ctx.input.get_caller();
                    let caller_pre = pre_state.balance.get(&caller).cloned().unwrap_or(EVMU256::ZERO);
                    let caller_post = post_state.balance.get(&caller).cloned().unwrap_or(EVMU256::ZERO);
                    
                    if caller_post > caller_pre {
                        let profit = caller_post - caller_pre;
                        
                        let bug_idx = 0x42424242; // Unique bug ID for balance drain
                        
                        EVMBugResult::new(
                            "Balance Drain".to_string(),
                            bug_idx,
                            format!(
                                "Contract {:?} balance drained by {} ETH! Attacker {:?} profited {} ETH",
                                target,
                                loss / EVMU256::from(1_000_000_000_000_000_000u128),
                                caller,
                                profit / EVMU256::from(1_000_000_000_000_000_000u128)
                            ),
                            ConciseEVMInput::from_input(ctx.input, ctx.fuzz_state.get_execution_result()),
                            None,
                            Some(format!("{:?}", target)),
                        );
                        
                        bugs.push(bug_idx);
                    }
                }
            }
        
        bugs
    }
}