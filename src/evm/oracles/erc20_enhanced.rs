// Enhanced ERC20 Oracle with Sanity Checks

use crate::evm::types::{EVMU256, EVMU512};

/// Maximum reasonable profit in ETH (prevents false positives)
const MAX_REASONABLE_PROFIT: u128 = 1000_000_000_000_000_000_000_000; // 1000 ETH

/// Suspicious profit threshold requiring extra validation
const SUSPICIOUS_PROFIT_THRESHOLD: u128 = 100_000_000_000_000_000_000_000; // 100 ETH

/// Minimum profit to report (0.01 ETH)
const MIN_PROFIT_THRESHOLD: u128 = 10_000_000_000_000_000_000; // 0.01 ETH

/// Check if a profit amount is reasonable
pub fn is_reasonable_profit(profit: EVMU512) -> bool {
    // If profit > 1000 ETH, it's likely a false positive
    if profit > EVMU512::from(MAX_REASONABLE_PROFIT) {
        return false;
    }
    
    // If profit < 0.01 ETH, ignore it
    if profit < EVMU512::from(MIN_PROFIT_THRESHOLD) {
        return false;
    }
    
    true
}

/// Enhanced profit validation
pub fn validate_profit(
    earned: EVMU512,
    owed: EVMU512,
    initial_balance: EVMU256,
) -> Option<(EVMU512, bool)> {
    if earned <= owed {
        return None;
    }
    
    let profit = earned - owed;
    
    // Basic sanity check
    if !is_reasonable_profit(profit) {
        return None;
    }
    
    // Check if profit is suspicious
    let is_suspicious = profit > EVMU512::from(SUSPICIOUS_PROFIT_THRESHOLD);
    
    // Additional validation for suspicious profits
    if is_suspicious {
        // Check if initial balance could support this profit
        // (You can't extract more than what was there)
        let max_possible = EVMU512::from(initial_balance) * EVMU512::from(10u128); // 10x leverage max
        if profit > max_possible {
            return None;
        }
    }
    
    Some((profit, is_suspicious))
}

/// Calculate confidence score for a vulnerability
pub fn calculate_confidence(profit: EVMU512, execution_steps: usize) -> u8 {
    let mut confidence = 100u8;
    
    // Lower confidence for very high profits
    if profit > EVMU512::from(SUSPICIOUS_PROFIT_THRESHOLD) {
        confidence -= 30;
    }
    
    // Lower confidence for very simple exploits (might be missing steps)
    if execution_steps < 3 {
        confidence -= 20;
    }
    
    // Lower confidence for very complex exploits (might be unrealistic)
    if execution_steps > 10 {
        confidence -= 10;
    }
    
    confidence
}

/// Enhanced oracle check with false positive prevention
pub fn enhanced_oracle_check(
    earned: EVMU512,
    owed: EVMU512,
    initial_balance: EVMU256,
    execution_steps: usize,
) -> Option<(EVMU512, u8, String)> {
    // Validate profit
    let (profit, is_suspicious) = validate_profit(earned, owed, initial_balance)?;
    
    // Calculate confidence
    let confidence = calculate_confidence(profit, execution_steps);
    
    // Generate warning message if needed
    let warning = if is_suspicious {
        " [⚠️ REQUIRES MANUAL VERIFICATION]"
    } else if confidence < 70 {
        " [LOW CONFIDENCE]"
    } else {
        ""
    };
    
    // Convert profit to ETH for display
    let profit_eth = profit / EVMU512::from(1_000_000_000_000_000_000_000_000_u128);
    
    let message = format!(
        "Profit: {} ETH (Confidence: {}%){}",
        profit_eth,
        confidence,
        warning
    );
    
    Some((profit, confidence, message))
}