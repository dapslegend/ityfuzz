#!/bin/bash
# Simulate maximum profit extraction from ItyFuzz logs using Forge

echo "=== ItyFuzz Maximum Profit Simulator ==="
echo

# Check if foundry is installed
if ! command -v forge &> /dev/null; then
    echo "❌ Foundry not installed!"
    echo "Install with: curl -L https://foundry.paradigm.xyz | bash"
    exit 1
fi

# Check arguments
if [ $# -lt 1 ]; then
    echo "Usage: $0 <logfile> [block_number]"
    echo "Example: $0 bego_test_extended.log 22315679"
    exit 1
fi

LOGFILE=$1
BLOCK=${2:-""}

# Run the simulator
echo "📊 Analyzing vulnerability in $LOGFILE..."
echo

if [ -n "$BLOCK" ]; then
    python3 forge_mev_executor.py "$LOGFILE" --block "$BLOCK"
else
    python3 forge_mev_executor.py "$LOGFILE"
fi

echo
echo "✅ Simulation complete!"
echo
echo "Check mev_report.md for detailed results"