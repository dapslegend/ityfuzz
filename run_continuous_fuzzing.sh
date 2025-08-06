#!/bin/bash

echo "=== Continuous Contract Fuzzing ==="
echo "This will find and fuzz ALL contracts on BSC"
echo "ItyFuzz will detect vulnerabilities automatically"
echo

# Check if ItyFuzz is built
if [ ! -f "./target/debug/ityfuzz" ]; then
    echo "❌ ItyFuzz not found at ./target/debug/ityfuzz"
    echo "Please build ItyFuzz first"
    exit 1
fi

# Check if cast is available
if ! command -v cast &> /dev/null; then
    echo "❌ Foundry not installed!"
    echo "Install with: curl -L https://foundry.paradigm.xyz | bash"
    exit 1
fi

# Create logs directory
mkdir -p fuzzing_logs
mkdir -p vulnerability_logs

# Run continuously
while true; do
    echo
    echo "🔄 Starting new fuzzing round at $(date)"
    echo "================================================"
    
    # Run the universal fuzzer
    python3 universal_contract_fuzzer.py
    
    # Move vulnerability logs to separate folder
    mv vuln_*.log vulnerability_logs/ 2>/dev/null
    
    # Move reports to logs folder
    mv universal_fuzz_report_*.json fuzzing_logs/ 2>/dev/null
    
    # Count vulnerabilities found
    VULN_COUNT=$(ls vulnerability_logs/vuln_*.log 2>/dev/null | wc -l)
    echo
    echo "📊 Total vulnerabilities found so far: $VULN_COUNT"
    
    # Wait before next round
    echo
    echo "⏳ Waiting 30 minutes before next round..."
    echo "   Press Ctrl+C to stop"
    sleep 1800
done