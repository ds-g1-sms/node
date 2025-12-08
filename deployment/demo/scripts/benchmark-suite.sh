#!/bin/bash

# benchmark-suite.sh - Multi-scenario benchmark suite for load testing
# Runs multiple benchmark configurations and compiles results into a comprehensive report

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
OUTPUT_DIR="${DEMO_DIR}/benchmark-suite-results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SUITE_OUTPUT="${OUTPUT_DIR}/suite-${TIMESTAMP}"
VERBOSE=false
QUICK_MODE=false

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default test scenarios
declare -A SCENARIOS=(
    ["light"]="5 50 2 30"      # clients messages rooms duration
    ["medium"]="10 100 3 60"
    ["heavy"]="20 200 5 90"
    ["stress"]="50 100 3 120"
)

# Quick mode scenarios (shorter durations)
declare -A QUICK_SCENARIOS=(
    ["light"]="5 20 2 15"
    ["medium"]="10 50 3 30"
    ["heavy"]="20 100 5 45"
)

usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Run a comprehensive benchmark suite with multiple test scenarios and compile results.

OPTIONS:
    -o DIR          Output directory (default: ${OUTPUT_DIR})
    -q              Quick mode (shorter test durations)
    -s SCENARIOS    Comma-separated scenario names to run (default: all)
                    Available: light,medium,heavy,stress
    -v              Verbose output
    -h              Show this help message

EXAMPLES:
    # Run full suite
    $0

    # Quick mode for faster results
    $0 -q

    # Run specific scenarios
    $0 -s light,medium

    # Custom output directory with verbose logging
    $0 -o ./my-results -v

SCENARIOS:
    light   - Light load (5 clients, 50 msgs, 2 rooms, 30s)
    medium  - Medium load (10 clients, 100 msgs, 3 rooms, 60s)
    heavy   - Heavy load (20 clients, 200 msgs, 5 rooms, 90s)
    stress  - Stress test (50 clients, 100 msgs, 3 rooms, 120s)

OUTPUT:
    Results are saved in timestamped directory with:
    - Individual JSON results for each scenario
    - Individual HTML reports for each scenario
    - Consolidated suite report (JSON and HTML)
    - Summary statistics and comparisons

EOF
    exit 0
}

log() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*"
    fi
}

# Parse command line arguments
SELECTED_SCENARIOS=""
while getopts "o:qs:vh" opt; do
    case $opt in
        o) OUTPUT_DIR="$OPTARG"; SUITE_OUTPUT="${OUTPUT_DIR}/suite-${TIMESTAMP}" ;;
        q) QUICK_MODE=true ;;
        s) SELECTED_SCENARIOS="$OPTARG" ;;
        v) VERBOSE=true ;;
        h) usage ;;
        *) usage ;;
    esac
done

# Select scenarios based on mode
if [[ "$QUICK_MODE" == "true" ]]; then
    declare -n ACTIVE_SCENARIOS=QUICK_SCENARIOS
    log "Running in QUICK mode (shorter test durations)"
else
    declare -n ACTIVE_SCENARIOS=SCENARIOS
    log "Running in FULL mode"
fi

# Filter scenarios if specified
if [[ -n "$SELECTED_SCENARIOS" ]]; then
    IFS=',' read -ra SELECTED_ARRAY <<< "$SELECTED_SCENARIOS"
    declare -A FILTERED_SCENARIOS
    for scenario in "${SELECTED_ARRAY[@]}"; do
        if [[ -n "${ACTIVE_SCENARIOS[$scenario]:-}" ]]; then
            FILTERED_SCENARIOS[$scenario]="${ACTIVE_SCENARIOS[$scenario]}"
        else
            log_warn "Unknown scenario: $scenario (skipping)"
        fi
    done
    declare -n ACTIVE_SCENARIOS=FILTERED_SCENARIOS
fi

# Create output directory
mkdir -p "$SUITE_OUTPUT"
log "Output directory: $SUITE_OUTPUT"

# Check prerequisites
log "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    log_error "python3 is required but not installed"
    exit 1
fi

if ! "${SCRIPT_DIR}/benchmark-load.sh" -h &> /dev/null; then
    log_error "benchmark-load.sh not found or not executable"
    exit 1
fi

# Array to store results metadata
declare -a RESULTS_METADATA=()

# Run each scenario
SCENARIO_COUNT=0
TOTAL_SCENARIOS="${#ACTIVE_SCENARIOS[@]}"

log ""
log "=========================================="
log "Starting Benchmark Suite"
log "=========================================="
log "Scenarios to run: ${TOTAL_SCENARIOS}"
log "Timestamp: ${TIMESTAMP}"
log ""

for scenario in "${!ACTIVE_SCENARIOS[@]}"; do
    ((SCENARIO_COUNT++))
    
    # Parse scenario parameters
    IFS=' ' read -r clients messages rooms duration <<< "${ACTIVE_SCENARIOS[$scenario]}"
    
    log "=========================================="
    log "Scenario ${SCENARIO_COUNT}/${TOTAL_SCENARIOS}: ${scenario}"
    log "=========================================="
    log "Configuration:"
    log "  - Clients: ${clients}"
    log "  - Messages per client: ${messages}"
    log "  - Rooms: ${rooms}"
    log "  - Duration: ${duration}s"
    log ""
    
    # Output file for this scenario
    SCENARIO_OUTPUT="${SUITE_OUTPUT}/${scenario}.json"
    
    # Run benchmark
    START_TIME=$(date +%s)
    
    if [[ "$VERBOSE" == "true" ]]; then
        "${SCRIPT_DIR}/benchmark-load.sh" \
            -c "$clients" \
            -m "$messages" \
            -r "$rooms" \
            -d "$duration" \
            -o "$SCENARIO_OUTPUT" \
            -v
    else
        "${SCRIPT_DIR}/benchmark-load.sh" \
            -c "$clients" \
            -m "$messages" \
            -r "$rooms" \
            -d "$duration" \
            -o "$SCENARIO_OUTPUT"
    fi
    
    END_TIME=$(date +%s)
    ELAPSED=$((END_TIME - START_TIME))
    
    # Check if benchmark succeeded
    if [[ -f "$SCENARIO_OUTPUT" ]]; then
        log "${GREEN}✓${NC} Scenario '${scenario}' completed successfully (${ELAPSED}s)"
        
        # Store metadata
        RESULTS_METADATA+=("${scenario}:${SCENARIO_OUTPUT}:${clients}:${messages}:${rooms}:${duration}")
    else
        log_error "✗ Scenario '${scenario}' failed"
    fi
    
    log ""
done

log "=========================================="
log "All Scenarios Complete"
log "=========================================="
log ""

# Generate consolidated report
log "Generating consolidated report..."

# Create Python script to compile results
COMPILE_SCRIPT="${SUITE_OUTPUT}/compile_results.py"
cat > "$COMPILE_SCRIPT" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""Compile multiple benchmark results into a consolidated report."""

import json
import sys
from pathlib import Path
from datetime import datetime

def load_result(filepath):
    """Load a single benchmark result."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}", file=sys.stderr)
        return None

def compile_suite_results(metadata_file, output_json, output_html):
    """Compile results from multiple scenarios."""
    
    # Read metadata
    scenarios = []
    with open(metadata_file, 'r') as f:
        for line in f:
            parts = line.strip().split(':')
            if len(parts) >= 6:
                scenarios.append({
                    'name': parts[0],
                    'file': parts[1],
                    'clients': int(parts[2]),
                    'messages': int(parts[3]),
                    'rooms': int(parts[4]),
                    'duration': int(parts[5])
                })
    
    # Load all results
    suite_results = {
        'timestamp': datetime.now().isoformat(),
        'total_scenarios': len(scenarios),
        'scenarios': []
    }
    
    for scenario in scenarios:
        result = load_result(scenario['file'])
        if result:
            suite_results['scenarios'].append({
                'name': scenario['name'],
                'config': {
                    'clients': scenario['clients'],
                    'messages_per_client': scenario['messages'],
                    'rooms': scenario['rooms'],
                    'duration': scenario['duration']
                },
                'results': result
            })
    
    # Save consolidated JSON
    with open(output_json, 'w') as f:
        json.dump(suite_results, f, indent=2)
    
    # Generate HTML report
    generate_html_report(suite_results, output_html)
    
    print(f"Consolidated results saved to:")
    print(f"  JSON: {output_json}")
    print(f"  HTML: {output_html}")

def generate_html_report(suite_results, output_file):
    """Generate HTML report with all scenarios."""
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Benchmark Suite Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; border-bottom: 2px solid #ddd; padding-bottom: 8px; }}
        .summary {{ background: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th {{ background: #4CAF50; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f5f5f5; }}
        .metric {{ font-weight: bold; color: #2196F3; }}
        .scenario {{ background: #fff3e0; padding: 15px; margin: 20px 0; border-left: 4px solid #FF9800; }}
        .config {{ background: #f9f9f9; padding: 10px; margin: 10px 0; border-radius: 4px; }}
        .good {{ color: #4CAF50; }}
        .warn {{ color: #FF9800; }}
        .bad {{ color: #f44336; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Benchmark Suite Report</h1>
        <div class="summary">
            <p><strong>Generated:</strong> {suite_results['timestamp']}</p>
            <p><strong>Total Scenarios:</strong> {suite_results['total_scenarios']}</p>
        </div>
"""
    
    # Add comparison table
    html += """
        <h2>📊 Scenario Comparison</h2>
        <table>
            <tr>
                <th>Scenario</th>
                <th>Clients</th>
                <th>Messages</th>
                <th>Throughput (msg/s)</th>
                <th>Avg Latency (ms)</th>
                <th>P95 Latency (ms)</th>
                <th>Success Rate</th>
            </tr>
"""
    
    for scenario in suite_results['scenarios']:
        name = scenario['name']
        config = scenario['config']
        results = scenario['results']
        
        clients = config['clients']
        messages = config['messages_per_client']
        throughput = results.get('summary', {}).get('throughput', 0)
        avg_latency = results.get('latency', {}).get('average', 0) * 1000
        p95_latency = results.get('latency', {}).get('p95', 0) * 1000
        success_rate = results.get('summary', {}).get('success_rate', 0)
        
        success_class = "good" if success_rate >= 99 else ("warn" if success_rate >= 95 else "bad")
        
        html += f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{clients}</td>
                <td>{messages}</td>
                <td class="metric">{throughput:.2f}</td>
                <td>{avg_latency:.2f}</td>
                <td>{p95_latency:.2f}</td>
                <td class="{success_class}">{success_rate:.2f}%</td>
            </tr>
"""
    
    html += """
        </table>
"""
    
    # Add detailed results for each scenario
    html += """
        <h2>📋 Detailed Results by Scenario</h2>
"""
    
    for scenario in suite_results['scenarios']:
        name = scenario['name']
        config = scenario['config']
        results = scenario['results']
        summary = results.get('summary', {})
        latency = results.get('latency', {})
        
        html += f"""
        <div class="scenario">
            <h3>{name.upper()}</h3>
            <div class="config">
                <strong>Configuration:</strong> {config['clients']} clients × {config['messages_per_client']} messages 
                across {config['rooms']} rooms (max {config['duration']}s)
            </div>
            
            <h4>Summary</h4>
            <table>
                <tr><td>Total Duration</td><td class="metric">{summary.get('total_duration', 0):.2f}s</td></tr>
                <tr><td>Messages Sent</td><td class="metric">{summary.get('messages_sent', 0):,}</td></tr>
                <tr><td>Messages Received</td><td class="metric">{summary.get('messages_received', 0):,}</td></tr>
                <tr><td>Errors</td><td class="metric">{summary.get('errors', 0)}</td></tr>
                <tr><td>Success Rate</td><td class="metric">{summary.get('success_rate', 0):.2f}%</td></tr>
                <tr><td>Throughput</td><td class="metric">{summary.get('throughput', 0):.2f} msg/s</td></tr>
            </table>
            
            <h4>Latency Statistics</h4>
            <table>
                <tr><td>Average</td><td class="metric">{latency.get('average', 0) * 1000:.2f} ms</td></tr>
                <tr><td>Median</td><td class="metric">{latency.get('median', 0) * 1000:.2f} ms</td></tr>
                <tr><td>Min</td><td class="metric">{latency.get('min', 0) * 1000:.2f} ms</td></tr>
                <tr><td>Max</td><td class="metric">{latency.get('max', 0) * 1000:.2f} ms</td></tr>
                <tr><td>95th Percentile</td><td class="metric">{latency.get('p95', 0) * 1000:.2f} ms</td></tr>
                <tr><td>99th Percentile</td><td class="metric">{latency.get('p99', 0) * 1000:.2f} ms</td></tr>
                <tr><td>Std Deviation</td><td class="metric">{latency.get('stddev', 0) * 1000:.2f} ms</td></tr>
            </table>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(output_file, 'w') as f:
        f.write(html)

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: compile_results.py <metadata_file> <output_json> <output_html>")
        sys.exit(1)
    
    compile_suite_results(sys.argv[1], sys.argv[2], sys.argv[3])
PYTHON_EOF

chmod +x "$COMPILE_SCRIPT"

# Create metadata file
METADATA_FILE="${SUITE_OUTPUT}/metadata.txt"
for meta in "${RESULTS_METADATA[@]}"; do
    echo "$meta" >> "$METADATA_FILE"
done

# Run compilation
SUITE_JSON="${SUITE_OUTPUT}/suite-report.json"
SUITE_HTML="${SUITE_OUTPUT}/suite-report.html"

python3 "$COMPILE_SCRIPT" "$METADATA_FILE" "$SUITE_JSON" "$SUITE_HTML"

log ""
log "=========================================="
log "Benchmark Suite Complete!"
log "=========================================="
log ""
log "Results saved to: ${SUITE_OUTPUT}"
log ""
log "Files generated:"
log "  • Suite report (JSON): ${SUITE_JSON}"
log "  • Suite report (HTML): ${SUITE_HTML}"
log "  • Individual scenario results: ${SUITE_OUTPUT}/*.json"
log "  • Individual scenario reports: ${SUITE_OUTPUT}/*.html"
log ""
log "${GREEN}✓${NC} View the HTML report in your browser:"
log "  file://${SUITE_HTML}"
log ""
