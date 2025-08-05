#!/usr/bin/env python3
"""
Quick Vulnerability Extractor - Simple tool to extract and maximize profits
Usage: python3 quick_extract.py <logfile>
"""

import re
import sys

def extract_vulnerability(filepath):
    """Extract vulnerability details from a log file"""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find profit
    profit_match = re.search(r'Anyone can earn ([\d.]+) ETH', content)
    if not profit_match:
        print("No vulnerability found!")
        return
    
    profit = float(profit_match.group(1))
    
    # Find trace
    trace_start = content.find("================ Trace ================")
    trace_end = content.find("\n\n", trace_start + 50) if trace_start != -1 else -1
    trace = content[trace_start:trace_end] if trace_start != -1 else "No trace found"
    
    # Extract transactions
    swaps = re.findall(r'swapExactETHForTokens\{value: ([\d.]+) ether\}', trace)
    swap_values = [float(v) for v in swaps]
    
    print(f"\n{'='*60}")
    print(f"VULNERABILITY ANALYSIS: {filepath}")
    print('='*60)
    print(f"\n📊 Current Profit: {profit:,.2f} ETH")
    print(f"\n🔍 Transaction Pattern:")
    
    for i, value in enumerate(swap_values, 1):
        print(f"   {i}. Swap {value} ETH")
    
    # Calculate maximum potential
    if len(swap_values) >= 2 and swap_values[1] == 0:
        # Classic drain pattern
        input_value = swap_values[0]
        efficiency = profit / input_value if input_value > 0 else 0
        
        print(f"\n✅ Pattern: Swap-Drain Combo")
        print(f"   Input: {input_value} ETH")
        print(f"   Output: {profit} ETH")
        print(f"   Efficiency: {efficiency:.1f}x")
        
        print(f"\n🚀 MAXIMUM EXTRACTION POTENTIAL:")
        multipliers = [2, 5, 10, 50, 100, 1000]
        
        for mult in multipliers:
            new_input = input_value * mult
            new_profit = efficiency * new_input
            print(f"   {mult}x input ({new_input:,.0f} ETH) → {new_profit:,.0f} ETH profit")
        
        print(f"\n💰 Recommended Strategy:")
        print(f"   1. Use flashloan to borrow {input_value * 100:,.0f} ETH")
        print(f"   2. Execute: swap({input_value * 100:,.0f} ETH) → drain(0 ETH)")
        print(f"   3. Expected profit: {efficiency * input_value * 100:,.0f} ETH")
        print(f"   4. Repay flashloan + fee")
        print(f"   5. Keep massive profit!")
        
    elif swap_values:
        # Other pattern
        total_input = sum(swap_values)
        
        print(f"\n📈 Pattern: Complex")
        print(f"   Total input: {total_input} ETH")
        print(f"   Profit: {profit} ETH")
        
        if total_input > 0:
            print(f"\n🎯 Potential with 10x input: {profit * 10:,.0f} ETH")
    
    print(f"\n{'='*60}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 quick_extract.py <logfile>")
        print("\nExample: python3 quick_extract.py bego_test_extended.log")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    try:
        extract_vulnerability(filepath)
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()