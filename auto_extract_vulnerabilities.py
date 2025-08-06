#!/usr/bin/env python3
"""
Automatic Vulnerability Extractor for ItyFuzz Logs
Extracts all vulnerability details and calculates maximum profit potential
"""

import re
import os
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional

class AutoVulnerabilityExtractor:
    """Automatically extract and analyze vulnerabilities from ItyFuzz logs"""
    
    def __init__(self):
        # Regex patterns for extraction
        self.patterns = {
            'vulnerability': r'Found vulnerabilities!.*?\[Fund Loss\]: Anyone can earn ([\d.]+) ETH',
            'trace_section': r'================ Trace ================(.*?)(?:\n\n|\Z)',
            'sender': r'\[Sender\] (0x[a-fA-F0-9]{40})',
            'swap': r'Router\.swapExactETHForTokens\{value: ([\d.]+) ether\}\((.*?)\)',
            'call': r'(0x[a-fA-F0-9]{40})\.(\w+)(?:\{value: ([\d.]+) ether\})?\((.*?)\)',
            'approve': r'approve\((.*?), ([\d.]+)',
            'transfer': r'transfer\((.*?), ([\d.]+)',
            'path': r'path:\((.*?)\)',
            'block': r'block.*?(\d{8,})',
            'contract': r'Contract (0x[a-fA-F0-9]{40})',
        }
        
        # Vulnerability type patterns
        self.vuln_types = {
            'swap_drain': lambda txs: len(txs) >= 2 and any(t['value'] == 0 for t in txs if t['type'] == 'swap'),
            'reentrancy': lambda txs: any('reentrant' in str(t).lower() for t in txs),
            'ownership': lambda txs: any(t.get('function') in ['initOwner', 'setOwner', 'transferOwnership'] for t in txs),
            'approve_exploit': lambda txs: any(t.get('function') == 'approve' for t in txs),
            'direct_drain': lambda txs: any(t.get('function') in ['withdraw', 'retrieve', 'drain'] for t in txs),
        }
        
    def extract_from_file(self, filepath: str) -> Optional[Dict]:
        """Extract vulnerability data from a single log file"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Check if vulnerability exists
            vuln_match = re.search(self.patterns['vulnerability'], content, re.DOTALL)
            if not vuln_match:
                return None
            
            profit = float(vuln_match.group(1))
            
            # Extract trace
            trace_match = re.search(self.patterns['trace_section'], content, re.DOTALL)
            trace = trace_match.group(1) if trace_match else ""
            
            # Extract transactions
            transactions = self._extract_transactions(trace)
            
            # Identify pattern
            pattern = self._identify_pattern(transactions)
            
            # Calculate maximum potential
            max_potential = self._calculate_max_potential(profit, transactions, pattern)
            
            # Extract additional info
            block_match = re.search(self.patterns['block'], content)
            block = int(block_match.group(1)) if block_match else 0
            
            contracts = re.findall(self.patterns['contract'], content)
            
            return {
                'file': os.path.basename(filepath),
                'profit': profit,
                'pattern': pattern,
                'transactions': transactions,
                'transaction_count': len(transactions),
                'max_potential': max_potential,
                'multiplier': max_potential / profit if profit > 0 else 0,
                'block': block,
                'contracts': list(set(contracts)),
                'trace_snippet': trace[:200] + '...' if len(trace) > 200 else trace
            }
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            return None
    
    def _extract_transactions(self, trace: str) -> List[Dict]:
        """Extract all transactions from trace"""
        transactions = []
        
        # Extract swaps
        for match in re.finditer(self.patterns['swap'], trace):
            value = float(match.group(1))
            params = match.group(2)
            
            # Extract path
            path_match = re.search(self.patterns['path'], params)
            path = path_match.group(1) if path_match else ""
            
            transactions.append({
                'type': 'swap',
                'function': 'swapExactETHForTokens',
                'value': value,
                'value_eth': value,
                'path': path,
                'params': params
            })
        
        # Extract other calls
        for match in re.finditer(self.patterns['call'], trace):
            target = match.group(1)
            function = match.group(2)
            value = float(match.group(3)) if match.group(3) else 0
            params = match.group(4)
            
            transactions.append({
                'type': 'call',
                'target': target,
                'function': function,
                'value': value,
                'value_eth': value,
                'params': params
            })
        
        return transactions
    
    def _identify_pattern(self, transactions: List[Dict]) -> str:
        """Identify the vulnerability pattern"""
        # Check each pattern type
        for pattern_name, pattern_check in self.vuln_types.items():
            if pattern_check(transactions):
                return pattern_name
        
        # Special patterns
        if len(transactions) >= 2:
            if transactions[0]['value'] > 0 and transactions[1]['value'] == 0:
                return 'setup_drain'
            elif all(t['value'] == 0 for t in transactions[:2]) and len(transactions) > 2:
                return 'multi_step_drain'
        
        return 'unknown'
    
    def _calculate_max_potential(self, current_profit: float, transactions: List[Dict], pattern: str) -> float:
        """Calculate maximum potential profit based on pattern"""
        
        # Get total input value
        total_input = sum(t['value'] for t in transactions if t['type'] == 'swap' and t['value'] > 0)
        
        if pattern in ['swap_drain', 'setup_drain']:
            # These patterns scale linearly with input
            if total_input > 0:
                efficiency = current_profit / total_input
                # Assume we can do 100x input
                return efficiency * total_input * 100
            else:
                # If no input but profit, it's a pure drain
                return current_profit * 10
                
        elif pattern == 'reentrancy':
            # Reentrancy can be called multiple times
            return current_profit * 10
            
        elif pattern == 'ownership':
            # Limited by contract balance
            return current_profit * 2
            
        elif pattern == 'approve_exploit':
            # Can drain approved amounts
            return current_profit * 50
            
        else:
            # Conservative estimate
            return current_profit * 5
    
    def extract_all(self, directory: str = '.') -> List[Dict]:
        """Extract vulnerabilities from all log files in directory"""
        vulnerabilities = []
        
        # Find all log files
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.log'):
                    filepath = os.path.join(root, file)
                    result = self.extract_from_file(filepath)
                    if result:
                        vulnerabilities.append(result)
        
        return vulnerabilities
    
    def generate_report(self, vulnerabilities: List[Dict]) -> str:
        """Generate a comprehensive report"""
        if not vulnerabilities:
            return "No vulnerabilities found."
        
        # Sort by profit
        vulnerabilities.sort(key=lambda x: x['profit'], reverse=True)
        
        report = []
        report.append("# Automatic Vulnerability Extraction Report")
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total vulnerabilities found: {len(vulnerabilities)}")
        
        # Summary statistics
        total_current = sum(v['profit'] for v in vulnerabilities)
        total_potential = sum(v['max_potential'] for v in vulnerabilities)
        
        report.append(f"\n## Summary")
        report.append(f"- Total current profit: {total_current:,.2f} ETH")
        report.append(f"- Total maximum potential: {total_potential:,.2f} ETH")
        report.append(f"- Average multiplier: {total_potential/total_current:.1f}x")
        
        # Group by pattern
        patterns = {}
        for v in vulnerabilities:
            pattern = v['pattern']
            if pattern not in patterns:
                patterns[pattern] = []
            patterns[pattern].append(v)
        
        report.append(f"\n## Vulnerabilities by Pattern")
        for pattern, vulns in patterns.items():
            report.append(f"\n### {pattern.replace('_', ' ').title()}")
            report.append(f"Count: {len(vulns)}")
            report.append(f"Total profit: {sum(v['profit'] for v in vulns):,.2f} ETH")
            report.append(f"Max potential: {sum(v['max_potential'] for v in vulns):,.2f} ETH")
        
        # Top 10 vulnerabilities
        report.append(f"\n## Top 10 Vulnerabilities")
        for i, v in enumerate(vulnerabilities[:10], 1):
            report.append(f"\n### {i}. {v['file']}")
            report.append(f"- **Profit**: {v['profit']:,.2f} ETH")
            report.append(f"- **Pattern**: {v['pattern']}")
            report.append(f"- **Transactions**: {v['transaction_count']}")
            report.append(f"- **Max Potential**: {v['max_potential']:,.2f} ETH ({v['multiplier']:.1f}x)")
            
            # Show transaction details
            if v['transactions']:
                report.append("- **Transaction Sequence**:")
                for j, tx in enumerate(v['transactions'][:3], 1):
                    if tx['type'] == 'swap':
                        report.append(f"  {j}. Swap {tx['value']} ETH")
                    else:
                        report.append(f"  {j}. {tx['function']}({tx['value']} ETH)")
        
        # Extraction strategies
        report.append(f"\n## Extraction Strategies")
        report.append("```python")
        report.append("# For swap-drain patterns")
        report.append("original_swap = 2200  # ETH")
        report.append("multiplier = 100")
        report.append("new_swap = original_swap * multiplier")
        report.append("expected_profit = original_profit * multiplier")
        report.append("")
        report.append("# For reentrancy")
        report.append("for i in range(10):")
        report.append("    call_vulnerable_function()")
        report.append("")
        report.append("# For flashloan amplification")
        report.append("flashloan(1_000_000 ETH)")
        report.append("execute_exploit(1_000_000 ETH)")
        report.append("repay_loan()")
        report.append("```")
        
        return '\n'.join(report)
    
    def save_json(self, vulnerabilities: List[Dict], filename: str = 'vulnerabilities.json'):
        """Save vulnerabilities to JSON file"""
        # Convert transactions to serializable format
        for v in vulnerabilities:
            v['transactions'] = [
                {k: str(v) if not isinstance(v, (int, float, str, list, dict, type(None))) else v 
                 for k, v in tx.items()} 
                for tx in v['transactions']
            ]
        
        with open(filename, 'w') as f:
            json.dump(vulnerabilities, f, indent=2)
        
        print(f"Saved {len(vulnerabilities)} vulnerabilities to {filename}")

def main():
    """Main function to run automatic extraction"""
    print("=== ItyFuzz Automatic Vulnerability Extractor ===\n")
    
    extractor = AutoVulnerabilityExtractor()
    
    # Extract from current directory and subdirectories
    print("Scanning for vulnerabilities...")
    vulnerabilities = extractor.extract_all('.')
    
    print(f"\nFound {len(vulnerabilities)} vulnerabilities")
    
    if vulnerabilities:
        # Generate report
        report = extractor.generate_report(vulnerabilities)
        
        # Save report
        with open('vulnerability_report.md', 'w') as f:
            f.write(report)
        print("\nReport saved to vulnerability_report.md")
        
        # Save JSON
        extractor.save_json(vulnerabilities, 'vulnerabilities.json')
        
        # Print summary
        total_current = sum(v['profit'] for v in vulnerabilities)
        total_potential = sum(v['max_potential'] for v in vulnerabilities)
        
        print(f"\n=== Summary ===")
        print(f"Total current profit: {total_current:,.2f} ETH")
        print(f"Total maximum potential: {total_potential:,.2f} ETH")
        print(f"Potential increase: {(total_potential/total_current - 1)*100:.1f}%")
        
        # Show top 5
        print(f"\nTop 5 vulnerabilities:")
        for i, v in enumerate(vulnerabilities[:5], 1):
            print(f"{i}. {v['file']}: {v['profit']:,.2f} ETH → {v['max_potential']:,.2f} ETH ({v['multiplier']:.1f}x)")

if __name__ == "__main__":
    main()