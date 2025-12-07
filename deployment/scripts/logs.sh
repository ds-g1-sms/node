#!/bin/bash
# ==============================================================================
# Log Aggregation Script for Distributed Chat System
# ==============================================================================
# This script helps view and aggregate logs from all nodes in the chat system.
#
# Usage:
#   ./logs.sh [OPTIONS]
#
# Options:
#   -s, --stack STACK_NAME   Stack name (default: chat-system)
#   -n, --node NODE_NAME     View logs for specific node only
#   -f, --follow             Follow log output
#   -t, --tail LINES         Number of lines to show (default: 100)
#   -a, --all                Show all logs (no tail limit)
#   -h, --help               Show this help message
#
# ==============================================================================

set -e

# Default configuration
STACK_NAME="chat-system"
NODE_NAME=""
FOLLOW=false
TAIL_LINES=100
SHOW_ALL=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ==============================================================================
# Helper Functions
# ==============================================================================

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
Log Aggregation Script for Distributed Chat System

Usage: $0 [OPTIONS]

Options:
    -s, --stack STACK_NAME   Stack name (default: chat-system)
    -n, --node NODE_NAME     View logs for specific node only (node1, node2, node3)
    -f, --follow             Follow log output (live streaming)
    -t, --tail LINES         Number of lines to show (default: 100)
    -a, --all                Show all logs (no tail limit)
    -h, --help               Show this help message

Examples:
    # View last 100 lines from all nodes
    $0

    # Follow logs from all nodes
    $0 -f

    # View logs from specific node
    $0 -n node1

    # Follow logs from specific node with custom tail
    $0 -n node2 -f -t 50

    # View all logs from node3
    $0 -n node3 -a
EOF
}

# ==============================================================================
# Parse Command Line Arguments
# ==============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--stack)
            STACK_NAME="$2"
            shift 2
            ;;
        -n|--node)
            NODE_NAME="$2"
            shift 2
            ;;
        -f|--follow)
            FOLLOW=true
            shift
            ;;
        -t|--tail)
            TAIL_LINES="$2"
            shift 2
            ;;
        -a|--all)
            SHOW_ALL=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# ==============================================================================
# Validation
# ==============================================================================

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

# Check if stack exists
if ! docker stack ls 2>/dev/null | grep -q "$STACK_NAME"; then
    print_error "Stack ${STACK_NAME} not found"
    print_info "Available stacks:"
    docker stack ls
    exit 1
fi

# ==============================================================================
# Build Docker Service Logs Command
# ==============================================================================

build_logs_command() {
    local service_name=$1
    local cmd="docker service logs"
    
    if [ "$FOLLOW" = true ]; then
        cmd="$cmd -f"
    fi
    
    if [ "$SHOW_ALL" = false ]; then
        cmd="$cmd --tail ${TAIL_LINES}"
    fi
    
    cmd="$cmd --timestamps ${service_name}"
    
    echo "$cmd"
}

# ==============================================================================
# View Logs
# ==============================================================================

if [ -n "$NODE_NAME" ]; then
    # View logs for specific node
    SERVICE_NAME="${STACK_NAME}_${NODE_NAME}"
    
    # Check if service exists
    if ! docker service ls --filter "name=${SERVICE_NAME}" --format "{{.Name}}" | grep -q "^${SERVICE_NAME}$"; then
        print_error "Service ${SERVICE_NAME} not found"
        print_info "Available services in stack ${STACK_NAME}:"
        docker stack services "$STACK_NAME" --format "table {{.Name}}\t{{.Replicas}}"
        exit 1
    fi
    
    print_info "Viewing logs for ${NODE_NAME} (service: ${SERVICE_NAME})"
    
    # Build and execute command
    CMD=$(build_logs_command "$SERVICE_NAME")
    eval "$CMD"
else
    # View logs for all nodes
    print_info "Viewing logs for all nodes in stack ${STACK_NAME}"
    
    # Get all services in the stack
    SERVICES=$(docker stack services "$STACK_NAME" --format "{{.Name}}")
    
    if [ -z "$SERVICES" ]; then
        print_error "No services found in stack ${STACK_NAME}"
        exit 1
    fi
    
    if [ "$FOLLOW" = true ]; then
        # For follow mode, we need to run all in parallel
        print_info "Following logs from all services (Press Ctrl+C to stop)..."
        
        PIDS=()
        for service in $SERVICES; do
            CMD=$(build_logs_command "$service")
            
            # Add service name prefix to output
            {
                eval "$CMD" 2>&1 | while IFS= read -r line; do
                    echo "[${service##*_}] $line"
                done
            } &
            
            PIDS+=($!)
        done
        
        # Wait for all background processes
        for pid in "${PIDS[@]}"; do
            wait "$pid" 2>/dev/null || true
        done
    else
        # For non-follow mode, show logs sequentially
        for service in $SERVICES; do
            echo ""
            print_info "=== Logs from ${service##*_} (${service}) ==="
            echo ""
            
            CMD=$(build_logs_command "$service")
            eval "$CMD"
        done
    fi
fi

# ==============================================================================
# Additional Log Commands
# ==============================================================================

if [ "$FOLLOW" = false ]; then
    echo ""
    print_info "Additional log commands:"
    echo "  Follow all logs:      $0 -f"
    echo "  Follow specific node: $0 -n node1 -f"
    echo "  View more lines:      $0 -t 500"
    echo "  View all logs:        $0 -a"
fi
