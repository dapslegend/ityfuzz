#!/usr/bin/env python3
"""
Analyze all vulnerability patterns for maximum extraction potential
"""

import re
import os
from collections import defaultdict

class VulnerabilityAnalyzer:
    def __init__(self):
        self.patterns = {
            'swap_drain': r'Router\.swapExactETHForTokens.*?value: 0\}',
            'reentrancy': r'reentrancy|reentrant',
            'flashloan': r'flashloan|flash',
            'direct_call': r'(0x[a-fA-F0-9]{40})\.call\{value: (\d+)\}',
            'approve': r'approve\(.*?\)',
            'transfer': r'transfer\(.*?\)',
            'balance': r'balance|drain'
        }
        
    def analyze_file(self, filepath):
        """Analyze a single log file"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Skip if no vulnerability
            if "Found vulnerabilities!" not in content:
                return None
                
            # Extract vulnerability info
            vuln_match = re.search(r"Found vulnerabilities!.*?\[Fund Loss\]: Anyone can earn ([\d.]+) ETH", content, re.DOTALL)
            if not vuln_match:
                return None
                
            profit = float(vuln_match.group(1))
            
            # Find trace section
            trace_start = content.find("================ Trace ================")
            trace_end = content.find("\n\n", trace_start + 50) if trace_start != -1 else -1
            trace = content[trace_start:trace_end] if trace_start != -1 else ""
            
            # Analyze pattern
            pattern_type = self.identify_pattern(trace, content)
            transactions = self.extract_transactions(trace)
            
            return {
                'file': os.path.basename(filepath),
                'profit': profit,
                'pattern': pattern_type,
                'transactions': transactions,
                'trace': trace[:500] if trace else "No trace"
            }
            
        except Exception as e:
            return None
            
    def identify_pattern(self, trace, content):
        """Identify the vulnerability pattern"""
        patterns_found = []
        
        for pattern_name, pattern_regex in self.patterns.items():
            if re.search(pattern_regex, trace + content[:1000], re.IGNORECASE):
                patterns_found.append(pattern_name)
                
        # Special pattern detection
        if "value: 0}" in trace and "swapExactETHForTokens" in trace:
            return "swap_drain_combo"
        elif len(patterns_found) > 1 and 'reentrancy' in patterns_found:
            return "reentrancy_exploit"
        elif 'flashloan' in patterns_found:
            return "flashloan_exploit"
        elif patterns_found:
            return patterns_found[0]
        else:
            return "unknown"
            
    def extract_transactions(self, trace):
        """Extract transaction details from trace"""
        transactions = []
        
        # Extract swaps
        swap_pattern = r'swapExactETHForTokens\{value: ([\d.]+) ether\}'
        for match in re.finditer(swap_pattern, trace):
            transactions.append({
                'type': 'swap',
                'value': float(match.group(1))
            })
            
        # Extract direct calls
        call_pattern = r'(0x[a-fA-F0-9]{40})\.(\w+)(?:\{value: (\d+)\})?'
        for match in re.finditer(call_pattern, trace):
            transactions.append({
                'type': 'call',
                'target': match.group(1),
                'function': match.group(2),
                'value': int(match.group(3)) if match.group(3) else 0
            })
            
        return transactions

def main():
    print("=== Comprehensive Vulnerability Analysis ===\n")
    
    analyzer = VulnerabilityAnalyzer()
    
    # Find all interesting vulnerabilities
    test_files = [
        "./backtest_results/corrected_oracle_tests/SEAMAN_erc20.log",
        "./backtest_results/simple/BBOX.log",
        "./backtest_results/beast/LPC_all.log",
        "./backtest_results/beast/FAPEN_erc20_reentrancy.log",
        "./backtest_results/enhanced/RES02.log",
        "./backtest_results/beast/SEAMAN_erc20_reentrancy.log",
    ]
    
    # Group by pattern type
    patterns = defaultdict(list)
    
    for filepath in test_files:
        if os.path.exists(filepath):
            result = analyzer.analyze_file(filepath)
            if result:
                patterns[result['pattern']].append(result)
    
    # Add some BEGO files for comparison
    bego_files = [
        "./bego_test_extended.log",
        "./backtest_results/simple/BEGO.log"
    ]
    
    for filepath in bego_files:
        if os.path.exists(filepath):
            result = analyzer.analyze_file(filepath)
            if result:
                patterns[result['pattern']].append(result)
    
    # Print analysis by pattern type
    for pattern_type, vulns in patterns.items():
        print(f"\n{'='*60}")
        print(f"Pattern Type: {pattern_type.upper()}")
        print('='*60)
        
        total_profit = sum(v['profit'] for v in vulns)
        print(f"Total instances: {len(vulns)}")
        print(f"Total profit: {total_profit:,.2f} ETH")
        print(f"Average profit: {total_profit/len(vulns):,.2f} ETH")
        
        # Sort by profit
        vulns.sort(key=lambda x: x['profit'], reverse=True)
        
        print("\nTop vulnerabilities:")
        for v in vulns[:3]:
            print(f"\n  {v['file']}:")
            print(f"    Profit: {v['profit']:,.2f} ETH")
            print(f"    Transactions: {len(v['transactions'])}")
            
            # Show transaction summary
            if v['transactions']:
                swap_count = sum(1 for t in v['transactions'] if t['type'] == 'swap')
                call_count = sum(1 for t in v['transactions'] if t['type'] == 'call')
                total_value = sum(t.get('value', 0) for t in v['transactions'] if t['type'] == 'swap')
                
                print(f"    Swaps: {swap_count}, Calls: {call_count}")
                print(f"    Total swap value: {total_value:,.2f} ETH")
                
                # Maximum extraction estimate
                if pattern_type == "swap_drain_combo" and total_value > 0:
                    estimated_max = v['profit'] * 10  # Could do 10x input
                    print(f"    💡 Max extraction estimate: {estimated_max:,.2f} ETH (10x input)")
                elif pattern_type == "reentrancy_exploit":
                    estimated_max = v['profit'] * 5  # Reentrancy can be called multiple times
                    print(f"    💡 Max extraction estimate: {estimated_max:,.2f} ETH (5x calls)")
                elif pattern_type == "flashloan_exploit":
                    estimated_max = v['profit'] * 100  # Flashloans provide huge capital
                    print(f"    💡 Max extraction estimate: {estimated_max:,.2f} ETH (100x capital)")
    
    # Overall summary
    print(f"\n{'='*60}")
    print("MAXIMUM EXTRACTION STRATEGIES BY PATTERN")
    print('='*60)
    
    print("""
1. **Swap-Drain Combo** (like BEGO):
   - Increase initial swap amount 10-1000x
   - Keep drain transaction the same
   - Potential: 10-1000x profit increase
   
2. **Reentrancy Exploits**:
   - Call vulnerable function multiple times
   - Each call extracts value
   - Potential: 5-10x profit increase
   
3. **Flashloan Exploits**:
   - Borrow massive capital (millions)
   - Execute exploit with borrowed funds
   - Potential: 100-1000x profit increase
   
4. **Direct Call/Balance Drains**:
   - Find maximum withdrawable amount
   - May combine with other techniques
   - Potential: 2-10x profit increase
""")
    
    # Find specific interesting patterns
    print(f"\n{'='*60}")
    print("SPECIFIC VULNERABILITY ANALYSIS")
    print('='*60)
    
    # Analyze SEAMAN
    seaman_file = "./backtest_results/corrected_oracle_tests/SEAMAN_erc20.log"
    if os.path.exists(seaman_file):
        print("\n📍 SEAMAN Vulnerability:")
        with open(seaman_file, 'r') as f:
            content = f.read()
        
        profit_match = re.search(r"Anyone can earn ([\d.]+) ETH", content)
        if profit_match:
            profit = float(profit_match.group(1))
            print(f"   Reported profit: {profit:,.2f} ETH")
            
            # Look for trace
            if "Trace ====" in content:
                trace_start = content.find("Trace ====")
                trace_snippet = content[trace_start:trace_start+500]
                
                # Count transactions
                tx_count = trace_snippet.count("└─[1]") + trace_snippet.count("├─[1]")
                print(f"   Transaction count: {tx_count}")
                print(f"   💡 With optimization: ~{profit * 10:,.2f} ETH possible")
    
    # Analyze LPC
    lpc_file = "./backtest_results/beast/LPC_all.log"
    if os.path.exists(lpc_file):
        print("\n📍 LPC Vulnerability:")
        with open(lpc_file, 'r') as f:
            content = f.read()
        
        profit_match = re.search(r"Anyone can earn ([\d.]+) ETH", content)
        if profit_match:
            profit = float(profit_match.group(1))
            print(f"   Reported profit: {profit:,.2f} ETH")
            print(f"   💡 Small but could be multiplied with flashloans")

if __name__ == "__main__":
    main()