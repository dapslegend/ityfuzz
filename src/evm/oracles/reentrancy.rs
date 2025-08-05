use std::{
    collections::{hash_map::DefaultHasher, HashMap},
    hash::{Hash, Hasher},
};

use bytes::Bytes;
use itertools::Itertools;
use revm_primitives::Bytecode;

use super::REENTRANCY_BUG_IDX;
use crate::{
    evm::{
        input::{ConciseEVMInput, EVMInput},
        oracle::EVMBugResult,
        types::{EVMAddress, EVMFuzzState, EVMOracleCtx, EVMQueueExecutor, EVMU256},
        vm::EVMState,
    },
    generic_vm::vm_state::VMStateT,
    oracle::{Oracle, OracleCtx},
    state::HasExecutionResult,
};

pub struct ReentrancyOracle {
    pub address_to_name: HashMap<EVMAddress, String>,
    // Cache for fast-path checking
    known_safe_addresses: HashMap<EVMAddress, bool>,
}

impl ReentrancyOracle {
    pub fn new(address_to_name: HashMap<EVMAddress, String>) -> Self {
        Self { 
            address_to_name,
            known_safe_addresses: HashMap::new(),
        }
    }
}

impl
    Oracle<
        EVMState,
        EVMAddress,
        Bytecode,
        Bytes,
        EVMAddress,
        EVMU256,
        Vec<u8>,
        EVMInput,
        EVMFuzzState,
        ConciseEVMInput,
        EVMQueueExecutor,
    > for ReentrancyOracle
{
    fn transition(&self, _ctx: &mut EVMOracleCtx<'_>, _stage: u64) -> u64 {
        0
    }

    fn oracle(
        &self,
        ctx: &mut OracleCtx<
            EVMState,
            EVMAddress,
            Bytecode,
            Bytes,
            EVMAddress,
            EVMU256,
            Vec<u8>,
            EVMInput,
            EVMFuzzState,
            ConciseEVMInput,
            EVMQueueExecutor,
        >,
        _stage: u64,
    ) -> Vec<u64> {
        let reetrancy_metadata = unsafe {
            &ctx.post_state
                .as_any()
                .downcast_ref_unchecked::<EVMState>()
                .reentrancy_metadata
        };
        
        // Fast-path: early return if no reentrancy found
        if reetrancy_metadata.found.is_empty() {
            return vec![];
        }
        
        // Fast-path: check if we've seen similar patterns before
        let mut results = Vec::with_capacity(reetrancy_metadata.found.len());
        
        for (addr, slot) in reetrancy_metadata.found.iter() {
            // Generate unique bug ID efficiently
            let mut hasher = DefaultHasher::new();
            addr.hash(&mut hasher);
            slot.hash(&mut hasher);
            let real_bug_idx = (hasher.finish() << 8) + REENTRANCY_BUG_IDX;

            let name = self.address_to_name.get(addr).unwrap_or(&format!("{:?}", addr)).clone();
            
            // Enhanced bug reporting with more context
            EVMBugResult::new(
                "Reentrancy".to_string(),
                real_bug_idx,
                format!("Reentrancy vulnerability detected on contract '{}' at storage slot {:?}. This could allow draining of funds.", name, slot),
                ConciseEVMInput::from_input(ctx.input, ctx.fuzz_state.get_execution_result()),
                None,
                Some(name.clone()),
            )
            .push_to_output();
            
            results.push(real_bug_idx);
        }
        
        results
    }
}
