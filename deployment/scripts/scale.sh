#!/bin/bash
# ==============================================================================
# Scaling Script for Distributed Chat System
# ==============================================================================
# This script helps scale services in the distributed chat system.
#
# Usage:
#   ./scale.sh [OPTIONS]
#
# Options:
#   -s, --stack STACK_NAME   Stack name (default: chat-system)
#   -n, --node NODE_NAME     Node to scale (required)
#   -r, --replicas COUNT     Number of replicas (required)
#   -v, --verify             Verify scaling operation
#   -h, --help               Show this help message
#
# ==============================================================================

set -e

# Default configuration
STACK_NAME="chat-system"
NODE_NAME=""
REPLICAS=""
VERIFY=false

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
Scaling Script for Distributed Chat System

Usage: $0 [OPTIONS]

Options:
    -s, --stack STACK_NAME   Stack name (default: chat-system)
    -n, --node NODE_NAME     Node to scale (required: node1, node2, node3)
    -r, --replicas COUNT     Number of replicas (required)
    -v, --verify             Verify scaling operation
    -h, --help               Show this help message

Examples:
    # Scale node1 to 2 replicas
    $0 -n node1 -r 2

    # Scale node2 to 1 replica (scale down)
    $0 -n node2 -r 1

    # Scale with verification
    $0 -n node3 -r 3 -v

    # Scale in custom stack
    $0 -s my-chat-stack -n node1 -r 2

Note:
    For production multi-host deployment, ensure you have sufficient machines
    with appropriate node labels for the replicas you want to create.
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
        -r|--replicas)
            REPLICAS="$2"
            shift 2
            ;;
        -v|--verify)
            VERIFY=true
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

# Check required parameters
if [ -z "$NODE_NAME" ]; then
    print_error "Node name is required"
    usage
    exit 1
fi

if [ -z "$REPLICAS" ]; then
    print_error "Number of replicas is required"
    usage
    exit 1
fi

# Validate replicas is a number
if ! [[ "$REPLICAS" =~ ^[0-9]+$ ]]; then
    print_error "Replicas must be a positive number"
    exit 1
fi

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

# Check if running in Swarm mode
if ! docker info | grep -q "Swarm: active"; then
    print_error "Docker Swarm is not active"
    exit 1
fi

# Check if stack exists
if ! docker stack ls | grep -q "$STACK_NAME"; then
    print_error "Stack ${STACK_NAME} not found"
    exit 1
fi

# Build service name
SERVICE_NAME="${STACK_NAME}_${NODE_NAME}"

# Check if service exists
if ! docker service ls --filter "name=${SERVICE_NAME}" --format "{{.Name}}" | grep -q "^${SERVICE_NAME}$"; then
    print_error "Service ${SERVICE_NAME} not found"
    print_info "Available services:"
    docker stack services "$STACK_NAME"
    exit 1
fi

# ==============================================================================
# Get Current State
# ==============================================================================

CURRENT_REPLICAS_RAW=$(docker service ls --filter "name=${SERVICE_NAME}" --format "{{.Replicas}}" 2>/dev/null)

if [ -z "$CURRENT_REPLICAS_RAW" ]; then
    print_error "Unable to get current replica count for ${SERVICE_NAME}"
    exit 1
fi

# Validate format is "running/desired"
if ! echo "$CURRENT_REPLICAS_RAW" | grep -qE '^[0-9]+/[0-9]+$'; then
    print_error "Unexpected replica format: ${CURRENT_REPLICAS_RAW}"
    exit 1
fi

CURRENT_REPLICAS=$(echo "$CURRENT_REPLICAS_RAW" | cut -d'/' -f1)
CURRENT_DESIRED=$(echo "$CURRENT_REPLICAS_RAW" | cut -d'/' -f2)
print_info "Current replicas for ${NODE_NAME}: ${CURRENT_REPLICAS_RAW}"

if [ "$CURRENT_DESIRED" = "$REPLICAS" ]; then
    print_warning "Service is already configured for ${REPLICAS} replicas."
    if [ "$CURRENT_REPLICAS" != "$CURRENT_DESIRED" ]; then
        print_info "Service is converging to desired state..."
    fi
    exit 0
fi

# ==============================================================================
# Perform Scaling
# ==============================================================================

print_info "Scaling ${NODE_NAME} to ${REPLICAS} replicas..."

if [ "$REPLICAS" -gt "$CURRENT_REPLICAS" ]; then
    print_info "Scaling UP from ${CURRENT_REPLICAS} to ${REPLICAS}"
else
    print_info "Scaling DOWN from ${CURRENT_REPLICAS} to ${REPLICAS}"
fi

# Execute scaling command
if docker service scale "${SERVICE_NAME}=${REPLICAS}"; then
    print_success "Scaling command executed successfully"
else
    print_error "Failed to scale service"
    exit 1
fi

# ==============================================================================
# Verify Scaling (Optional)
# ==============================================================================

if [ "$VERIFY" = true ]; then
    print_info "Verifying scaling operation..."
    
    # Wait a moment for changes to take effect
    sleep 5
    
    # Check service status multiple times
    MAX_ATTEMPTS=6
    ATTEMPT=1
    SUCCESS=false
    
    while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
        print_info "Verification attempt ${ATTEMPT}/${MAX_ATTEMPTS}..."
        
        CURRENT_STATE=$(docker service ls --filter "name=${SERVICE_NAME}" --format "{{.Replicas}}")
        READY=$(echo "$CURRENT_STATE" | cut -d'/' -f1)
        DESIRED=$(echo "$CURRENT_STATE" | cut -d'/' -f2)
        
        print_info "Service state: ${READY}/${DESIRED} ready"
        
        if [ "$READY" = "$DESIRED" ] && [ "$DESIRED" = "$REPLICAS" ]; then
            print_success "Scaling verification successful! All replicas are ready."
            SUCCESS=true
            break
        fi
        
        if [ $ATTEMPT -lt $MAX_ATTEMPTS ]; then
            print_info "Waiting 10 seconds before next check..."
            sleep 10
        fi
        
        ATTEMPT=$((ATTEMPT + 1))
    done
    
    if [ "$SUCCESS" = false ]; then
        print_warning "Scaling may still be in progress. Check service status manually."
        print_info "Command: docker service ps ${SERVICE_NAME}"
    fi
fi

# ==============================================================================
# Display Status
# ==============================================================================

echo ""
print_info "Current service status:"
docker service ps "$SERVICE_NAME" --no-trunc

echo ""
print_info "Service details:"
docker service ls --filter "name=${SERVICE_NAME}"

echo ""
print_info "Useful commands:"
echo "  View service tasks:   docker service ps ${SERVICE_NAME}"
echo "  View service logs:    docker service logs -f ${SERVICE_NAME}"
echo "  Inspect service:      docker service inspect ${SERVICE_NAME}"
echo "  Scale back:           $0 -n ${NODE_NAME} -r ${CURRENT_REPLICAS}"

print_success "Scaling operation completed!"
