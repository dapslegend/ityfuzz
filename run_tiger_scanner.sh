#!/bin/bash

echo "=== Running MEV Tiger Scanner ==="
echo ""

# Kill any existing scanners
pkill -f "python3.*mev" || true

# Clear old logs
rm -rf mev/work_dirs/*
rm -rf mev/vulnerability_logs/*
rm -rf mev/fuzzing_logs/*

echo "🧹 Cleaned up old logs"
echo ""

# Run the tiger scanner
python3 mev_tiger_scanner.py