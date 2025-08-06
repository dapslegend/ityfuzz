#!/bin/bash

echo "=== MEV Continuous Scanner ==="
echo "Starting comprehensive blockchain scanning for vulnerabilities"
echo ""

# Create directories
mkdir -p mev/logs mev/work_dirs mev/vulnerability_logs mev/fuzzing_logs

# Function to run scanners
run_scanners() {
    echo "[$(date)] Starting new scanning round..."
    
    # Run proven scanner (fast, focused on ERC20)
    echo "[$(date)] Running proven MEV scanner..."
    python3 proven_mev_scanner.py 2>&1 | tee -a mev/proven_continuous_$(date +%Y%m%d).log
    
    # Small delay
    sleep 30
    
    # Run individual fuzzer for isolated testing
    echo "[$(date)] Running individual fuzzer..."
    python3 individual_fuzzer.py 2>&1 | tee -a mev/individual_continuous_$(date +%Y%m%d).log
    
    # Check for vulnerabilities
    if grep -q "VULNERABILITY FOUND" mev/vulnerability_logs/*.log 2>/dev/null; then
        echo ""
        echo "🚨🚨🚨 VULNERABILITY DETECTED! 🚨🚨🚨"
        echo "Check mev/vulnerability_logs/ for details"
        echo ""
    fi
    
    # Show statistics
    echo ""
    echo "[$(date)] Statistics:"
    echo "  Work directories: $(find mev/work_dirs -type d 2>/dev/null | wc -l)"
    echo "  Total logs: $(find mev/logs -name "*.log" 2>/dev/null | wc -l)"
    echo "  Vulnerabilities: $(find mev/vulnerability_logs -name "*.log" 2>/dev/null | wc -l)"
    echo ""
}

# Main loop
while true; do
    run_scanners
    
    echo "[$(date)] Waiting 5 minutes before next round..."
    sleep 300
done