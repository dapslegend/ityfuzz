use std::collections::HashMap;
use libafl::schedulers::Scheduler;
use revm_interpreter::Interpreter;
use crate::evm::{
    host::FuzzHost,
    middlewares::middleware::{Middleware, MiddlewareType},
    types::{EVMAddress, EVMFuzzState, EVMU256, EVMU512, convert_u256_to_h160},
    vm::EVMState,
};

/// Tracks ETH balance changes for all addresses to detect profit
pub struct EthBalanceTracker {
    /// Initial balances at the start of execution
    initial_balances: HashMap<EVMAddress, EVMU256>,
    /// Track which addresses are controlled by the fuzzer
    fuzzer_addresses: Vec<EVMAddress>,
}

impl EthBalanceTracker {
    pub fn new() -> Self {
        Self {
            initial_balances: HashMap::new(),
            fuzzer_addresses: vec![
                // Common fuzzer addresses
                EVMAddress::from_slice(&[0x35; 20]),
                EVMAddress::from_slice(&[0xe1; 20]),
                EVMAddress::from_slice(&[0x68; 20]),
                EVMAddress::from_slice(&[0x8e; 20]),
            ],
        }
    }
    
    pub fn add_fuzzer_address(&mut self, addr: EVMAddress) {
        self.fuzzer_addresses.push(addr);
    }
}

impl<SC> Middleware<SC> for EthBalanceTracker
where
    SC: Scheduler<State = EVMFuzzState> + Clone,
{
    unsafe fn on_step(&mut self, interp: &mut Interpreter, host: &mut FuzzHost<SC>, _: &mut EVMFuzzState) {
        // Track balance changes during CALL operations
        match *interp.instruction_pointer {
            0xf1 | 0xf2 => { // CALL, CALLCODE
                let value_transfer = interp.stack.peek(2).unwrap();
                if value_transfer > EVMU256::ZERO {
                    let sender = interp.contract.address;
                    let recipient = convert_u256_to_h160(interp.stack.peek(1).unwrap());
                    
                    // Track all ETH movements
                    // If ETH is leaving a contract and going to a fuzzer address, it's profit
                    if self.fuzzer_addresses.contains(&recipient) {
                        host.evmstate.flashloan_data.earned += EVMU512::from(value_transfer) * EVMU512::from(1_000_000_u128);
                    }
                }
            }
            _ => {}
        }
    }
    
    fn get_type(&self) -> MiddlewareType {
        MiddlewareType::OnChain
    }
}