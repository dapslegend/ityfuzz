pub const DEBUG_PRINT_PERCENT: usize = 8000;

pub const INFANT_STATE_INITIAL_VOTES: usize = 3; // used in fuzzer.rs when infant is added to states
pub const CORPUS_INITIAL_VOTES: usize = 3; // used in fuzzer.rs when infant is added to states
/// used in libafl scheduled mutator (this is at max 1 << MAX_STACK_POW ==
/// 2^MAX_STACK_POW)
pub const MAX_STACK_POW: usize = 7;
pub const MAX_HAVOC_ATTEMPTS: usize = 10;
pub const KNOWN_STATE_MAX_SIZE: usize = 1000;
pub const KNOWN_STATE_SKIP_SIZE: usize = 500;

// src/fuzzer.rs
/// The maximum number of inputs (or VMState) to keep in the corpus before
/// pruning
pub const DROP_THRESHOLD: usize = 300;  // Increased from 200 for better diversity
/// The number of inputs (or VMState) to prune each time the corpus is pruned
pub const PRUNE_AMT: usize = 150;  // Increased from 100
/// If inputs (or VMState) has not been visited this many times, it will be
/// ignored during pruning
pub const VISIT_IGNORE_THRESHOLD: usize = 2;

// src/state.rs
/// Amount of accounts and contracts that can be caller during fuzzing.
/// We will generate random addresses for these accounts and contracts.
pub const ACCOUNT_AMT: u8 = 2;
/// Amount of accounts and contracts that can be caller during fuzzing.
/// We will generate random addresses for these accounts and contracts.
pub const CONTRACT_AMT: u8 = 2;
/// Maximum size of the input data
pub const MAX_INPUT_SIZE: usize = 20;  // Back to original for better coverage

// src/abi.rs
/// Sample will be used to generate a random value with max value
pub const SAMPLE_MAX: u64 = 100;
/// Maximum value of the mutate choice. Related to [SAMPLE_MAX]
pub const MUTATE_CHOICE_MAX: u64 = 80;
/// Maximum value of the expand choice. Related to [SAMPLE_MAX]
pub const EXPAND_CHOICE_MAX: u64 = 90;
/// Maximum value of the random address choice. Related to [SAMPLE_MAX]
pub const RANDOM_ADDRESS_CHOICE: u64 = 90;

// src/evm/corpus_initializer.rs
/// If there are more than 1/UNKNOWN_SIGS_DIVISOR unknown sigs, we will
/// decompile with EVMole
pub const UNKNOWN_SIGS_DIVISOR: usize = 30;

// src/evm/mutator.rs
/// Sample will be used to generate a random value with max value
pub const MUTATOR_SAMPLE_MAX: u64 = 75;  // Balanced between 50 and 100
/// Related to [MUTATOR_SAMPLE_MAX]
pub const EXPLOIT_PRESET_CHOICE: u64 = 20;
/// Related to [MUTATOR_SAMPLE_MAX]
pub const ABI_MUTATE_CHOICE: u64 = 90;  // Slightly less aggressive than 85
/// Related to [MUTATOR_SAMPLE_MAX]
pub const HAVOC_CHOICE: u64 = 70;  // Balanced between 60 and 80
/// Maximum number of iterations to try to find a valid havoc mutation
pub const HAVOC_MAX_ITERS: u64 = 15;  // Balanced between 10 and 20
/// Related to [MUTATOR_SAMPLE_MAX]
pub const MUTATE_CALLER_CHOICE: u64 = 20;
/// Related to [MUTATOR_SAMPLE_MAX]
pub const TURN_TO_STEP_CHOICE: u64 = 60;
/// Related to [MUTATOR_SAMPLE_MAX]
pub const RANDOMNESS_CHOICE: u64 = 30;  // Slightly more randomness than 25
/// Related to [MUTATOR_SAMPLE_MAX]
pub const LIQUIDATE_CHOICE: u64 = 5;
/// Related to [MUTATOR_SAMPLE_MAX]
pub const LIQ_PERCENT_CHOICE: u64 = 80;
pub const LIQ_PERCENT: u64 = 10;
/// Related to [MUTATOR_SAMPLE_MAX] and [LIQUIDATE_CHOICE]
pub const RANDOMNESS_CHOICE_2: u64 = 6;
/// Maximum number of retries to try to find a valid mutation
pub const MUTATION_RETRIES: u32 = 25;  // Balanced between 20 and 30

// src/evm/scheduler.rs
pub const POWER_MULTIPLIER: f64 = 64.0;
pub const MAX_POWER: f64 = 6400.0;
pub const MIN_POWER: f64 = 16.0;

/// The more state change, the more likely a state is interesting
pub const STATE_CHANGE_MULTIPLIER: f64 = 20000.0;  // Back to original

/// The more calls, the more likely a state is interesting
pub const STATE_CHANGE_POWER_MULTIPLIER: f64 = 8.0;  // Back to original
