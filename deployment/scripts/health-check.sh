#!/bin/bash
# ==============================================================================
# Health Check Script for Distributed Chat System
# ==============================================================================
# This script performs health checks on all deployed nodes in the chat system.
#
# Usage:
#   ./health-check.sh [OPTIONS]
#
# Options:
#   -s, --stack STACK_NAME   Stack name to check (default: chat-system)
#   -n, --node NODE_NAME     Check specific node only
#   -v, --verbose            Show detailed output
#   -h, --help               Show this help message
#
# ==============================================================================

set -e

# Default configuration
STACK_NAME="chat-system"
NODE_NAME=""
VERBOSE=false

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

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
Health Check Script for Distributed Chat System

Usage: $0 [OPTIONS]

Options:
    -s, --stack STACK_NAME   Stack name to check (default: chat-system)
    -n, --node NODE_NAME     Check specific node only
    -v, --verbose            Show detailed output
    -h, --help               Show this help message

Examples:
    # Check all nodes in the default stack
    $0

    # Check specific stack
    $0 -s my-chat-stack

    # Check specific node
    $0 -n node1

    # Verbose output
    $0 -v
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
        -v|--verbose)
            VERBOSE=true
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
# Health Check Functions
# ==============================================================================

check_service_running() {
    local service_name=$1
    local replicas
    
    replicas=$(docker service ls --filter "name=${service_name}" --format "{{.Replicas}}" 2>/dev/null)
    
    if [ -z "$replicas" ]; then
        print_error "Service ${service_name} not found"
        return 1
    fi
    
    # Parse replicas in format "running/desired"
    local running=$(echo "$replicas" | cut -d'/' -f1)
    local desired=$(echo "$replicas" | cut -d'/' -f2)
    
    if [ "$running" = "$desired" ] && [ "$running" -gt 0 ]; then
        print_success "Service ${service_name} is running (${replicas})"
        return 0
    else
        print_warning "Service ${service_name} is not fully ready (${replicas})"
        return 1
    fi
}

check_service_health() {
    local service_name=$1
    local container_id
    
    # Get container ID for the service
    container_id=$(docker ps --filter "name=${service_name}" --format "{{.ID}}" | head -1)
    
    if [ -z "$container_id" ]; then
        print_error "No container found for service ${service_name}"
        return 1
    fi
    
    # Check container health status
    health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "unknown")
    
    case "$health_status" in
        "healthy")
            print_success "Service ${service_name} is healthy"
            return 0
            ;;
        "unhealthy")
            print_error "Service ${service_name} is unhealthy"
            if [ "$VERBOSE" = true ]; then
                docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' "$container_id"
            fi
            return 1
            ;;
        "starting")
            print_warning "Service ${service_name} is still starting"
            return 1
            ;;
        *)
            print_warning "Service ${service_name} health status: ${health_status}"
            return 1
            ;;
    esac
}

check_node_connectivity() {
    local node_name=$1
    local service_name="${STACK_NAME}_${node_name}"
    
    # Get service task container
    local container_id
    container_id=$(docker ps --filter "name=${service_name}" --format "{{.ID}}" | head -1)
    
    if [ -z "$container_id" ]; then
        print_error "Cannot check connectivity: container not found"
        return 1
    fi
    
    # Try to execute health check command inside container
    if docker exec "$container_id" python -c "import xmlrpc.client; xmlrpc.client.ServerProxy('http://localhost:9090').heartbeat()" &>/dev/null; then
        print_success "Node ${node_name} is responding to health checks"
        return 0
    else
        print_error "Node ${node_name} is not responding to health checks"
        return 1
    fi
}

check_node_logs() {
    local node_name=$1
    local service_name="${STACK_NAME}_${node_name}"
    
    print_info "Recent logs for ${node_name}:"
    docker service logs --tail 10 "$service_name" 2>&1 | tail -10
}

# ==============================================================================
# Main Health Check
# ==============================================================================

print_info "Starting health checks for stack: ${STACK_NAME}"
echo ""

# Check if stack exists
if ! docker stack ls | grep -q "$STACK_NAME"; then
    print_error "Stack ${STACK_NAME} not found"
    exit 1
fi

# Determine which nodes to check
if [ -n "$NODE_NAME" ]; then
    NODES=("$NODE_NAME")
else
    NODES=("node1" "node2" "node3")
fi

# Track overall health
ALL_HEALTHY=true

# Check each node
for node in "${NODES[@]}"; do
    print_info "Checking ${node}..."
    SERVICE_NAME="${STACK_NAME}_${node}"
    
    # Check if service is running
    if ! check_service_running "$SERVICE_NAME"; then
        ALL_HEALTHY=false
        continue
    fi
    
    # Wait a moment for service to be ready
    sleep 2
    
    # Check service health
    if ! check_service_health "$SERVICE_NAME"; then
        ALL_HEALTHY=false
    fi
    
    # Check node connectivity
    if ! check_node_connectivity "$node"; then
        ALL_HEALTHY=false
    fi
    
    # Show logs if verbose or if there's an issue
    if [ "$VERBOSE" = true ] || [ "$ALL_HEALTHY" = false ]; then
        check_node_logs "$node"
    fi
    
    echo ""
done

# ==============================================================================
# Summary
# ==============================================================================

echo ""
print_info "Health Check Summary"
echo "===================="

if [ "$ALL_HEALTHY" = true ]; then
    print_success "All nodes are healthy!"
    exit 0
else
    print_error "Some nodes are not healthy. Please check the logs above."
    echo ""
    print_info "Troubleshooting commands:"
    echo "  View service details: docker service ps ${STACK_NAME}_node1 --no-trunc"
    echo "  View logs:           docker service logs -f ${STACK_NAME}_node1"
    echo "  Inspect service:     docker service inspect ${STACK_NAME}_node1"
    exit 1
fi
