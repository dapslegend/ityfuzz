#!/bin/bash

echo "=== MEV Fuzzing Monitor ==="
echo ""

# Check if fuzzing is running
if pgrep -f "python3 universal_contract_fuzzer.py" > /dev/null; then
    echo "✅ Fuzzing is RUNNING"
    echo ""
    
    # Show process info
    echo "Process info:"
    ps aux | grep -E "python3|ityfuzz" | grep -v grep | head -5
    echo ""
else
    echo "❌ Fuzzing is NOT running"
    echo ""
fi

# Count directories and logs
echo "📊 Statistics:"
echo "  Work directories: $(find mev/work_dirs -type d 2>/dev/null | wc -l)"
echo "  Debug logs: $(find mev/logs -name "*.log" 2>/dev/null | wc -l)"
echo "  Vulnerability logs: $(find mev/vulnerability_logs -name "*.log" 2>/dev/null | wc -l)"
echo "  Fuzzing reports: $(find mev/fuzzing_logs -name "*.json" 2>/dev/null | wc -l)"
echo ""

# Show recent vulnerabilities
echo "🚨 Recent vulnerabilities:"
if [ -d "mev/vulnerability_logs" ] && [ "$(ls -A mev/vulnerability_logs 2>/dev/null)" ]; then
    for log in $(ls -t mev/vulnerability_logs/*.log 2>/dev/null | head -5); do
        echo "  - $(basename $log)"
        grep -E "Anyone can earn|profit" "$log" 2>/dev/null | head -1 | sed 's/^/    /'
    done
else
    echo "  None found yet"
fi
echo ""

# Show latest session log
echo "📄 Latest session output:"
if [ -d "mev" ] && [ "$(ls mev/fuzzing_session_*.log 2>/dev/null)" ]; then
    latest_session=$(ls -t mev/fuzzing_session_*.log 2>/dev/null | head -1)
    echo "  File: $(basename $latest_session)"
    echo "  Last 10 lines:"
    tail -10 "$latest_session" | sed 's/^/    /'
else
    echo "  No session logs found"
fi
echo ""

# Check disk usage
echo "💾 Disk usage:"
du -sh mev/* 2>/dev/null | sort -h

echo ""
echo "🔄 Refresh with: ./monitor_mev_fuzzing.sh"