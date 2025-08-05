#!/usr/bin/env python3
"""
Test script to demonstrate maximum extraction from ItyFuzz vulnerabilities
"""

import os
import sys
from ityfuzz_mev_bot import ItyFuzzMEVBot
from eth_account import Account

def test_maximum_extraction():
    """Test maximum extraction on BEGO vulnerability"""
    
    print("=== Testing Maximum Extraction ===\n")
    
    # Configuration
    config = {
        'min_profit_eth': 0.01,  # Low threshold to test everything
        'rpc_urls': {
            'eth': 'https://eth-mainnet.g.alchemy.com/v2/demo',
            'bsc': 'https://bsc-dataseed.binance.org/',
            'polygon': 'https://polygon-rpc.com'
        }
    }
    
    # Create test account
    test_key = Account.create().key.hex()
    
    # Create MEV bot
    bot = ItyFuzzMEVBot(test_key, config)
    
    # Test files
    test_files = [
        'bego_test_extended.log',
        'bego_test_optimized.log',
        'bego_backtest.log'
    ]
    
    results = []
    
    for log_file in test_files:
        if os.path.exists(log_file):
            print(f"\n{'='*60}")
            print(f"Processing: {log_file}")
            print('='*60)
            
            try:
                # Parse the log file
                vulnerabilities = bot.parser.parse_log_file(log_file)
                
                for vuln in vulnerabilities:
                    print(f"\nVulnerability: {vuln.name}")
                    print(f"Reported profit: {vuln.profit_eth} ETH")
                    print(f"Max extractable (from parsing): {vuln.max_extractable_value} ETH")
                    
                    # Calculate potential improvement
                    improvement = vuln.max_extractable_value - vuln.profit_eth
                    if improvement > 0:
                        print(f"🚀 Potential improvement: +{improvement} ETH")
                    
                    results.append({
                        'file': log_file,
                        'name': vuln.name,
                        'reported': vuln.profit_eth,
                        'maximum': vuln.max_extractable_value,
                        'improvement': improvement
                    })
                    
            except Exception as e:
                print(f"Error processing {log_file}: {str(e)}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY - Maximum Extraction Potential")
    print('='*60)
    
    total_reported = 0
    total_maximum = 0
    
    for result in results:
        print(f"\n{result['name']} ({result['file']}):")
        print(f"  Reported: {result['reported']} ETH")
        print(f"  Maximum:  {result['maximum']} ETH")
        if result['improvement'] > 0:
            print(f"  Gain:     +{result['improvement']} ETH ({result['improvement']/result['reported']*100:.1f}% increase)")
        
        total_reported += result['reported']
        total_maximum += result['maximum']
    
    print(f"\n{'='*60}")
    print(f"TOTAL REPORTED: {total_reported} ETH")
    print(f"TOTAL MAXIMUM:  {total_maximum} ETH")
    print(f"TOTAL GAIN:     +{total_maximum - total_reported} ETH")
    
    if total_maximum > total_reported:
        print(f"\n🎯 Maximum extraction techniques can increase profits by {(total_maximum/total_reported - 1)*100:.1f}%!")

def demonstrate_optimization_techniques():
    """Show the optimization techniques used"""
    
    print("\n\n=== Optimization Techniques ===\n")
    
    print("1. **Transaction Amount Optimization**")
    print("   - Tests multiples of original amounts (0.1x to 1000x)")
    print("   - Binary search for optimal swap amounts")
    print("   - Maximizes output while avoiding reverts")
    
    print("\n2. **Sequence Analysis**")
    print("   - Analyzes all transaction sequences in logs")
    print("   - Identifies the most profitable path")
    print("   - Combines transactions for maximum extraction")
    
    print("\n3. **Slippage Tolerance**")
    print("   - Sets amountOutMin to 0 for maximum flexibility")
    print("   - Prevents reverts due to price movements")
    print("   - Allows capturing maximum value")
    
    print("\n4. **Gas Optimization**")
    print("   - Increases gas price for high-value exploits")
    print("   - Ensures transaction inclusion")
    print("   - Balances gas cost vs profit")
    
    print("\n5. **State Manipulation**")
    print("   - Uses Anvil snapshots for testing")
    print("   - Tries multiple configurations")
    print("   - Finds optimal execution parameters")

if __name__ == "__main__":
    test_maximum_extraction()
    demonstrate_optimization_techniques()
    
    print("\n\n💡 TIP: Use the simulator with Anvil for accurate maximum extraction testing:")
    print("   python ityfuzz_simulator.py bego_test_extended.log --chain bsc")