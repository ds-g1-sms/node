#!/usr/bin/env bash

# Load Performance Benchmark Script for Distributed Chat System
# 
# This script performs comprehensive load testing on the demo deployment,
# simulating multiple concurrent users sending messages across nodes and
# measuring various performance metrics.
#
# Usage:
#   ./benchmark-load.sh [options]
#
# Options:
#   -c, --clients NUM       Number of concurrent clients (default: 10)
#   -m, --messages NUM      Messages per client (default: 100)
#   -r, --rooms NUM         Number of rooms to test (default: 3)
#   -d, --duration SEC      Test duration in seconds (default: 60)
#   -o, --output FILE       Output file for results (default: benchmark-results.json)
#   -v, --verbose           Verbose output
#   -h, --help              Show this help message

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$DEMO_DIR/../.." && pwd)"

# Default configuration
NUM_CLIENTS=10
MESSAGES_PER_CLIENT=100
NUM_ROOMS=3
TEST_DURATION=60
OUTPUT_FILE="$DEMO_DIR/benchmark-results.json"
VERBOSE=false

# Node addresses
NODE_IPS=("192.168.56.101" "192.168.56.102" "192.168.56.103")
WEBSOCKET_PORT=8080

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--clients)
                NUM_CLIENTS="$2"
                shift 2
                ;;
            -m|--messages)
                MESSAGES_PER_CLIENT="$2"
                shift 2
                ;;
            -r|--rooms)
                NUM_ROOMS="$2"
                shift 2
                ;;
            -d|--duration)
                TEST_DURATION="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

show_help() {
    cat << EOF
Load Performance Benchmark Script for Distributed Chat System

Usage: $0 [options]

Options:
  -c, --clients NUM       Number of concurrent clients (default: 10)
  -m, --messages NUM      Messages per client (default: 100)
  -r, --rooms NUM         Number of rooms to test (default: 3)
  -d, --duration SEC      Test duration in seconds (default: 60)
  -o, --output FILE       Output file for results (default: benchmark-results.json)
  -v, --verbose           Verbose output
  -h, --help              Show this help message

Examples:
  $0                                    # Run with defaults
  $0 -c 50 -m 200 -d 120               # 50 clients, 200 msgs each, 2 min test
  $0 -c 20 -r 5 -o results.json        # 20 clients across 5 rooms
EOF
}

# Check if Python benchmark script exists, create if needed
create_python_benchmark() {
    local python_script="$DEMO_DIR/scripts/benchmark_client.py"
    
    cat > "$python_script" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""
Load benchmark client for distributed chat system.
Simulates concurrent users sending messages and measures performance.
"""

import asyncio
import json
import time
import sys
import statistics
from datetime import datetime
from typing import List, Dict, Any
import websockets
from websockets.exceptions import WebSocketException

class BenchmarkClient:
    """Single benchmark client that connects and sends messages"""
    
    def __init__(self, client_id: int, node_url: str, room_id: str, 
                 num_messages: int, username: str):
        self.client_id = client_id
        self.node_url = node_url
        self.room_id = room_id
        self.num_messages = num_messages
        self.username = username
        self.ws = None
        
        # Metrics
        self.messages_sent = 0
        self.messages_received = 0
        self.errors = 0
        self.latencies = []
        self.start_time = None
        self.end_time = None
        
    async def connect(self):
        """Connect to node"""
        try:
            self.ws = await websockets.connect(self.node_url, ping_interval=None)
            return True
        except Exception as e:
            print(f"Client {self.client_id}: Connection failed: {e}", file=sys.stderr)
            self.errors += 1
            return False
    
    async def join_room(self):
        """Join the test room"""
        try:
            join_msg = {
                "type": "join_room",
                "room_id": self.room_id,
                "username": self.username
            }
            await self.ws.send(json.dumps(join_msg))
            
            # Wait for join confirmation
            response = await asyncio.wait_for(self.ws.recv(), timeout=5.0)
            return True
        except Exception as e:
            print(f"Client {self.client_id}: Join room failed: {e}", file=sys.stderr)
            self.errors += 1
            return False
    
    async def send_messages(self):
        """Send test messages"""
        self.start_time = time.time()
        
        for i in range(self.num_messages):
            try:
                msg_start = time.time()
                
                message = {
                    "type": "send_message",
                    "room_id": self.room_id,
                    "content": f"Benchmark message {i} from client {self.client_id}"
                }
                
                await self.ws.send(json.dumps(message))
                self.messages_sent += 1
                
                # Calculate send latency
                latency = (time.time() - msg_start) * 1000  # ms
                self.latencies.append(latency)
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.01)
                
            except Exception as e:
                print(f"Client {self.client_id}: Send failed: {e}", file=sys.stderr)
                self.errors += 1
        
        self.end_time = time.time()
    
    async def receive_messages(self, timeout: float = 5.0):
        """Receive messages for a period"""
        try:
            end_time = time.time() + timeout
            while time.time() < end_time:
                try:
                    msg = await asyncio.wait_for(
                        self.ws.recv(), 
                        timeout=max(0.1, end_time - time.time())
                    )
                    self.messages_received += 1
                except asyncio.TimeoutError:
                    break
        except Exception as e:
            pass  # Receiving is best-effort
    
    async def disconnect(self):
        """Disconnect from server"""
        try:
            if self.ws:
                await self.ws.close()
        except:
            pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        
        return {
            "client_id": self.client_id,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "errors": self.errors,
            "duration_seconds": duration,
            "throughput_msg_per_sec": self.messages_sent / duration if duration > 0 else 0,
            "avg_latency_ms": statistics.mean(self.latencies) if self.latencies else 0,
            "min_latency_ms": min(self.latencies) if self.latencies else 0,
            "max_latency_ms": max(self.latencies) if self.latencies else 0,
            "median_latency_ms": statistics.median(self.latencies) if self.latencies else 0,
            "p95_latency_ms": statistics.quantiles(self.latencies, n=20)[18] if len(self.latencies) > 20 else 0,
            "p99_latency_ms": statistics.quantiles(self.latencies, n=100)[98] if len(self.latencies) > 100 else 0,
        }

async def run_benchmark(num_clients: int, messages_per_client: int, 
                       node_urls: List[str], room_prefix: str, num_rooms: int):
    """Run the benchmark with multiple concurrent clients"""
    
    print(f"Starting benchmark with {num_clients} clients", file=sys.stderr)
    print(f"Messages per client: {messages_per_client}", file=sys.stderr)
    print(f"Nodes: {node_urls}", file=sys.stderr)
    print(f"Rooms: {num_rooms}", file=sys.stderr)
    
    start_time = time.time()
    
    # Create clients distributed across nodes and rooms
    clients = []
    for i in range(num_clients):
        node_url = node_urls[i % len(node_urls)]
        room_id = f"{room_prefix}_room_{i % num_rooms}"
        username = f"bench_user_{i}"
        
        client = BenchmarkClient(i, node_url, room_id, messages_per_client, username)
        clients.append(client)
    
    # Phase 1: Connect all clients
    print("Phase 1: Connecting clients...", file=sys.stderr)
    connect_tasks = [client.connect() for client in clients]
    connect_results = await asyncio.gather(*connect_tasks, return_exceptions=True)
    connected_clients = [c for c, r in zip(clients, connect_results) if r is True]
    print(f"Connected: {len(connected_clients)}/{num_clients}", file=sys.stderr)
    
    # Phase 2: Join rooms
    print("Phase 2: Joining rooms...", file=sys.stderr)
    join_tasks = [client.join_room() for client in connected_clients]
    await asyncio.gather(*join_tasks, return_exceptions=True)
    
    # Phase 3: Send messages concurrently
    print("Phase 3: Sending messages...", file=sys.stderr)
    send_tasks = [client.send_messages() for client in connected_clients]
    await asyncio.gather(*send_tasks, return_exceptions=True)
    
    # Phase 4: Receive messages for a bit
    print("Phase 4: Receiving messages...", file=sys.stderr)
    recv_tasks = [client.receive_messages(timeout=3.0) for client in connected_clients]
    await asyncio.gather(*recv_tasks, return_exceptions=True)
    
    # Phase 5: Disconnect
    print("Phase 5: Disconnecting...", file=sys.stderr)
    disconnect_tasks = [client.disconnect() for client in connected_clients]
    await asyncio.gather(*disconnect_tasks, return_exceptions=True)
    
    end_time = time.time()
    
    # Collect metrics
    all_metrics = [client.get_metrics() for client in clients]
    
    # Aggregate metrics
    total_messages_sent = sum(m["messages_sent"] for m in all_metrics)
    total_messages_received = sum(m["messages_received"] for m in all_metrics)
    total_errors = sum(m["errors"] for m in all_metrics)
    total_duration = end_time - start_time
    
    all_latencies = []
    for client in clients:
        all_latencies.extend(client.latencies)
    
    results = {
        "benchmark_config": {
            "num_clients": num_clients,
            "messages_per_client": messages_per_client,
            "num_rooms": num_rooms,
            "nodes": node_urls,
            "timestamp": datetime.now().isoformat()
        },
        "summary": {
            "total_duration_seconds": total_duration,
            "total_messages_sent": total_messages_sent,
            "total_messages_received": total_messages_received,
            "total_errors": total_errors,
            "overall_throughput_msg_per_sec": total_messages_sent / total_duration if total_duration > 0 else 0,
            "clients_connected": len(connected_clients),
            "success_rate": (total_messages_sent - total_errors) / total_messages_sent if total_messages_sent > 0 else 0
        },
        "latency_stats": {
            "avg_latency_ms": statistics.mean(all_latencies) if all_latencies else 0,
            "min_latency_ms": min(all_latencies) if all_latencies else 0,
            "max_latency_ms": max(all_latencies) if all_latencies else 0,
            "median_latency_ms": statistics.median(all_latencies) if all_latencies else 0,
            "p95_latency_ms": statistics.quantiles(all_latencies, n=20)[18] if len(all_latencies) > 20 else 0,
            "p99_latency_ms": statistics.quantiles(all_latencies, n=100)[98] if len(all_latencies) > 100 else 0,
            "stdev_latency_ms": statistics.stdev(all_latencies) if len(all_latencies) > 1 else 0
        },
        "per_client_metrics": all_metrics
    }
    
    return results

if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) < 5:
        print("Usage: benchmark_client.py <num_clients> <messages_per_client> <num_rooms> <node_url1> [node_url2] ...", file=sys.stderr)
        sys.exit(1)
    
    num_clients = int(sys.argv[1])
    messages_per_client = int(sys.argv[2])
    num_rooms = int(sys.argv[3])
    node_urls = sys.argv[4:]
    
    room_prefix = f"benchmark_{int(time.time())}"
    
    # Run benchmark
    results = asyncio.run(run_benchmark(num_clients, messages_per_client, node_urls, room_prefix, num_rooms))
    
    # Output results as JSON
    print(json.dumps(results, indent=2))
PYTHON_EOF
    
    chmod +x "$python_script"
    log_success "Created Python benchmark client: $python_script"
}

# Check system prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if services are running
    if ! vagrant ssh node1 -c "docker service ls --filter name=chat-demo 2>/dev/null" > /dev/null 2>&1; then
        log_error "Chat services are not running. Please run deploy-demo.sh first."
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not found"
        exit 1
    fi
    
    # Check websockets library
    if ! python3 -c "import websockets" 2>/dev/null; then
        log_warning "websockets library not found, installing..."
        pip3 install websockets --user || {
            log_error "Failed to install websockets library"
            exit 1
        }
    fi
    
    log_success "Prerequisites check passed"
}

# Test connectivity to nodes
test_connectivity() {
    log_info "Testing connectivity to nodes..."
    
    local all_reachable=true
    for node_ip in "${NODE_IPS[@]}"; do
        if curl -s --connect-timeout 2 "http://${node_ip}:${WEBSOCKET_PORT}" > /dev/null 2>&1; then
            log_success "Node ${node_ip}:${WEBSOCKET_PORT} is reachable"
        else
            log_warning "Node ${node_ip}:${WEBSOCKET_PORT} is not reachable"
            all_reachable=false
        fi
    done
    
    if [ "$all_reachable" = false ]; then
        log_warning "Some nodes are not reachable. Results may be incomplete."
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Run the benchmark
run_benchmark() {
    log_info "Running load benchmark..."
    log_info "Configuration:"
    log_info "  - Clients: $NUM_CLIENTS"
    log_info "  - Messages per client: $MESSAGES_PER_CLIENT"
    log_info "  - Rooms: $NUM_ROOMS"
    log_info "  - Nodes: ${NODE_IPS[*]}"
    
    # Build node URLs
    local node_urls=()
    for node_ip in "${NODE_IPS[@]}"; do
        node_urls+=("ws://${node_ip}:${WEBSOCKET_PORT}")
    done
    
    local python_script="$DEMO_DIR/scripts/benchmark_client.py"
    local temp_output=$(mktemp)
    
    log_info "Starting benchmark (this may take a few minutes)..."
    echo
    
    # Run the Python benchmark
    # Redirect only stdout (JSON) to temp file, let stderr show progress
    if python3 "$python_script" "$NUM_CLIENTS" "$MESSAGES_PER_CLIENT" "$NUM_ROOMS" "${node_urls[@]}" > "$temp_output"; then
        # Validate JSON output
        if python3 -m json.tool "$temp_output" > /dev/null 2>&1; then
            mv "$temp_output" "$OUTPUT_FILE"
            log_success "Benchmark completed successfully"
            return 0
        else
            log_error "Benchmark produced invalid JSON output"
            if [ "$VERBOSE" = true ]; then
                log_info "Output content:"
                cat "$temp_output"
            fi
            rm -f "$temp_output"
            return 1
        fi
    else
        log_error "Benchmark execution failed"
        if [ -f "$temp_output" ]; then
            if [ "$VERBOSE" = true ]; then
                log_info "Partial output:"
                cat "$temp_output"
            fi
            rm -f "$temp_output"
        fi
        return 1
    fi
}

# Display results
display_results() {
    if [ ! -f "$OUTPUT_FILE" ]; then
        log_error "Results file not found: $OUTPUT_FILE"
        return 1
    fi
    
    log_info "Benchmark Results:"
    echo
    
    # Extract and display key metrics using Python
    python3 << PYTHON_EOF
import json
import sys

try:
    with open("$OUTPUT_FILE", 'r') as f:
        results = json.load(f)
    
    summary = results.get('summary', {})
    latency = results.get('latency_stats', {})
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Duration:        {summary.get('total_duration_seconds', 0):.2f} seconds")
    print(f"Messages Sent:         {summary.get('total_messages_sent', 0):,}")
    print(f"Messages Received:     {summary.get('total_messages_received', 0):,}")
    print(f"Errors:                {summary.get('total_errors', 0):,}")
    print(f"Clients Connected:     {summary.get('clients_connected', 0)}")
    print(f"Success Rate:          {summary.get('success_rate', 0)*100:.2f}%")
    print(f"Overall Throughput:    {summary.get('overall_throughput_msg_per_sec', 0):.2f} msg/sec")
    print()
    print("=" * 70)
    print("LATENCY STATISTICS")
    print("=" * 70)
    print(f"Average:               {latency.get('avg_latency_ms', 0):.2f} ms")
    print(f"Median:                {latency.get('median_latency_ms', 0):.2f} ms")
    print(f"Min:                   {latency.get('min_latency_ms', 0):.2f} ms")
    print(f"Max:                   {latency.get('max_latency_ms', 0):.2f} ms")
    print(f"95th Percentile:       {latency.get('p95_latency_ms', 0):.2f} ms")
    print(f"99th Percentile:       {latency.get('p99_latency_ms', 0):.2f} ms")
    print(f"Std Deviation:         {latency.get('stdev_latency_ms', 0):.2f} ms")
    print("=" * 70)
    print()
    print(f"Full results saved to: $OUTPUT_FILE")
    
except Exception as e:
    print(f"Error displaying results: {e}", file=sys.stderr)
    sys.exit(1)
PYTHON_EOF
}

# Generate HTML report
generate_html_report() {
    local html_file="${OUTPUT_FILE%.json}.html"
    
    log_info "Generating HTML report..."
    
    # Create a temporary Python script for HTML generation
    local temp_py=$(mktemp)
    cat > "$temp_py" << 'PYEND'
import json
import sys
from datetime import datetime

output_file = sys.argv[1]
html_file = sys.argv[2]

with open(output_file, 'r') as f:
    results = json.load(f)

config = results.get('benchmark_config', {})
summary = results.get('summary', {})
latency = results.get('latency_stats', {})

html = """<!DOCTYPE html>
<html><head><title>Benchmark Results</title>
<style>
body{font-family:Arial;margin:20px;background:#f5f5f5}
.container{max-width:1200px;margin:0 auto;background:white;padding:30px;border-radius:8px}
h1{color:#333;border-bottom:3px solid #4CAF50;padding-bottom:10px}
h2{color:#666;margin-top:30px}
table{width:100%;border-collapse:collapse;margin:20px 0}
td{padding:10px;border-bottom:1px solid #ddd}
td:first-child{font-weight:bold;width:250px}
.success{color:#4CAF50}.warning{color:#ff9800}.error{color:#f44336}
</style></head><body><div class="container">
<h1>Load Benchmark Results</h1>
<p>Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
<h2>Configuration</h2><table>
<tr><td>Clients:</td><td>""" + str(config.get('num_clients', 0)) + """</td></tr>
<tr><td>Messages per Client:</td><td>""" + str(config.get('messages_per_client', 0)) + """</td></tr>
<tr><td>Rooms:</td><td>""" + str(config.get('num_rooms', 0)) + """</td></tr>
<tr><td>Nodes:</td><td>""" + ', '.join(config.get('nodes', [])) + """</td></tr>
</table>
<h2>Summary</h2><table>
<tr><td>Duration:</td><td>""" + f"{summary.get('total_duration_seconds', 0):.2f}" + """ seconds</td></tr>
<tr><td>Messages Sent:</td><td>""" + f"{summary.get('total_messages_sent', 0):,}" + """</td></tr>
<tr><td>Throughput:</td><td>""" + f"{summary.get('overall_throughput_msg_per_sec', 0):.2f}" + """ msg/sec</td></tr>
<tr><td>Success Rate:</td><td>""" + f"{summary.get('success_rate', 0)*100:.2f}" + """%</td></tr>
<tr><td>Errors:</td><td>""" + str(summary.get('total_errors', 0)) + """</td></tr>
</table>
<h2>Latency</h2><table>
<tr><td>Average:</td><td>""" + f"{latency.get('avg_latency_ms', 0):.2f}" + """ ms</td></tr>
<tr><td>Median:</td><td>""" + f"{latency.get('median_latency_ms', 0):.2f}" + """ ms</td></tr>
<tr><td>Min:</td><td>""" + f"{latency.get('min_latency_ms', 0):.2f}" + """ ms</td></tr>
<tr><td>Max:</td><td>""" + f"{latency.get('max_latency_ms', 0):.2f}" + """ ms</td></tr>
<tr><td>95th Percentile:</td><td>""" + f"{latency.get('p95_latency_ms', 0):.2f}" + """ ms</td></tr>
<tr><td>99th Percentile:</td><td>""" + f"{latency.get('p99_latency_ms', 0):.2f}" + """ ms</td></tr>
</table>
</div></body></html>"""

with open(html_file, 'w') as f:
    f.write(html)

print(f"HTML report: {html_file}")
PYEND
    
    python3 "$temp_py" "$OUTPUT_FILE" "$html_file"
    rm -f "$temp_py"
    
    log_success "HTML report generated: $html_file"
}

# Main execution
main() {
    cd "$DEMO_DIR"
    
    parse_args "$@"
    
    log_info "=== Load Performance Benchmark ==="
    log_info "Demo directory: $DEMO_DIR"
    echo
    
    create_python_benchmark
    check_prerequisites
    test_connectivity
    
    echo
    if run_benchmark; then
        echo
        display_results
        generate_html_report
        
        echo
        log_success "Benchmark complete!"
        log_info "Results saved to:"
        log_info "  - JSON: $OUTPUT_FILE"
        log_info "  - HTML: ${OUTPUT_FILE%.json}.html"
    else
        log_error "Benchmark failed"
        exit 1
    fi
}

main "$@"
