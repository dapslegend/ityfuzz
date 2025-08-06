#!/usr/bin/env python3
"""
Analyze ItyFuzz logs for maximum extraction potential
"""

import re
import os
from typing import List, Dict, Tuple

class SimpleLogAnalyzer:
    """Simple analyzer for ItyFuzz logs without web3 dependency"""
    
    def __init__(self):
        self.vuln_pattern = r"Found vulnerabilities!.*?\[Fund Loss\]: Anyone can earn ([\d.]+) ETH"
        self.swap_pattern = r"Router\.swapExactETHForTokens\{value: ([\d.]+) ether\}"
        self.call_pattern = r"(0x[a-fA-F0-9]+)\.call\{value: (\d+)\}"
        
    def analyze_log(self, filepath: str) -> Dict:
        """Analyze a log file for maximum extraction potential"""
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Find reported vulnerabilities
        vuln_matches = list(re.finditer(self.vuln_pattern, content, re.DOTALL))
        
        results = []
        
        for match in vuln_matches:
            reported_profit = float(match.group(1))
            
            # Find all swap values in the log
            swap_values = []
            for swap_match in re.finditer(self.swap_pattern, content):
                value = float(swap_match.group(1))
                swap_values.append(value)
            
            # Find the trace section
            trace_start = content.find("================ Trace ================", match.start())
            trace_end = content.find("\n\n", trace_start + 50) if trace_start != -1 else match.end() + 2000
            trace_section = content[trace_start:trace_end] if trace_start != -1 else ""
            
            # Extract transaction sequence from trace
            trace_swaps = []
            for swap_match in re.finditer(self.swap_pattern, trace_section):
                value = float(swap_match.group(1))
                trace_swaps.append(value)
            
            # Calculate maximum potential
            max_swap = max(swap_values) if swap_values else 0
            total_trace_value = sum(trace_swaps)
            
            # Estimate maximum extraction
            # If we see a pattern of increasing values, we might be able to push higher
            if trace_swaps and max(trace_swaps) > 0:
                # Conservative estimate: 2x the largest successful swap
                estimated_max = max(trace_swaps) * 2
                
                # If there's a 0 ETH drain transaction, we might extract even more
                if 0 in trace_swaps and len(trace_swaps) > 1:
                    estimated_max = max(trace_swaps) * 10  # More aggressive
            else:
                estimated_max = reported_profit
            
            results.append({
                'reported_profit': reported_profit,
                'trace_swaps': trace_swaps,
                'max_swap_seen': max_swap,
                'total_trace_value': total_trace_value,
                'estimated_max_extraction': estimated_max,
                'improvement_potential': estimated_max - reported_profit
            })
        
        return {
            'file': filepath,
            'vulnerabilities': results
        }
    
    def print_analysis(self, analysis: Dict):
        """Print analysis results"""
        print(f"\n{'='*70}")
        print(f"File: {analysis['file']}")
        print('='*70)
        
        for i, vuln in enumerate(analysis['vulnerabilities']):
            print(f"\nVulnerability #{i+1}:")
            print(f"  Reported profit: {vuln['reported_profit']:,.2f} ETH")
            print(f"  Transaction sequence: {vuln['trace_swaps']}")
            print(f"  Max swap seen in log: {vuln['max_swap_seen']:,.2f} ETH")
            print(f"  Total trace value: {vuln['total_trace_value']:,.2f} ETH")
            print(f"  Estimated max extraction: {vuln['estimated_max_extraction']:,.2f} ETH")
            
            if vuln['improvement_potential'] > 0:
                improvement_pct = (vuln['improvement_potential'] / vuln['reported_profit']) * 100
                print(f"  🚀 Potential improvement: +{vuln['improvement_potential']:,.2f} ETH ({improvement_pct:.1f}% increase)")
            else:
                print(f"  ✓ Already at maximum")

def main():
    """Analyze BSC test results for maximum extraction"""
    print("=== ItyFuzz Maximum Extraction Analysis ===\n")
    
    analyzer = SimpleLogAnalyzer()
    
    # Test files to analyze
    test_files = [
        'bego_test_extended.log',
        'bego_test_optimized.log',
        'bego_backtest.log',
        'bsc_nova_full_test.log',
        'bsc_nova_test.log'
    ]
    
    total_reported = 0
    total_estimated = 0
    
    for log_file in test_files:
        if os.path.exists(log_file):
            try:
                analysis = analyzer.analyze_log(log_file)
                analyzer.print_analysis(analysis)
                
                # Sum totals
                for vuln in analysis['vulnerabilities']:
                    total_reported += vuln['reported_profit']
                    total_estimated += vuln['estimated_max_extraction']
                    
            except Exception as e:
                print(f"\nError analyzing {log_file}: {str(e)}")
    
    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY - Maximum Extraction Potential")
    print('='*70)
    print(f"\nTotal reported profit: {total_reported:,.2f} ETH")
    print(f"Total estimated maximum: {total_estimated:,.2f} ETH")
    print(f"Total potential gain: +{total_estimated - total_reported:,.2f} ETH")
    
    if total_estimated > total_reported:
        gain_pct = ((total_estimated / total_reported) - 1) * 100
        print(f"\n🎯 Maximum extraction could increase profits by {gain_pct:.1f}%!")
    
    print("\n" + "="*70)
    print("EXTRACTION STRATEGIES:")
    print("="*70)
    print("\n1. **Increase Swap Amounts**")
    print("   - If a swap of X ETH works, try 2X, 5X, 10X")
    print("   - Use binary search to find the maximum")
    
    print("\n2. **Optimize Transaction Sequences**")
    print("   - If you see [swap, swap, 0 ETH drain], the drain might work with larger initial swaps")
    print("   - Test different orderings and combinations")
    
    print("\n3. **Remove Slippage Protection**")
    print("   - Set amountOutMin to 0 to accept any output")
    print("   - Prevents reverts and captures maximum value")
    
    print("\n4. **Exploit State Changes**")
    print("   - Each transaction changes contract state")
    print("   - Later transactions might extract more after state changes")

if __name__ == "__main__":
    main()