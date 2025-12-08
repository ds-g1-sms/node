#!/bin/bash
# ==============================================================================
# Deployment Script for Distributed Chat System
# ==============================================================================
# This script automates the deployment of the chat system to a Docker Swarm
# cluster across multiple machines.
#
# Usage:
#   ./deploy.sh [OPTIONS]
#
# Options:
#   -e, --env ENV_FILE       Environment file to use (default: .env.prod)
#   -s, --stack STACK_NAME   Stack name (default: chat-system)
#   -b, --build              Build and push images before deploying
#   -v, --verify             Verify deployment after completion
#   -h, --help               Show this help message
#
# ==============================================================================

set -e  # Exit on error

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$DEPLOYMENT_DIR")"

# Default configuration
ENV_FILE="${DEPLOYMENT_DIR}/.env.prod"
STACK_NAME="chat-system"
COMPOSE_FILE="${DEPLOYMENT_DIR}/docker-compose.prod.yml"
BUILD_IMAGES=false
VERIFY_DEPLOYMENT=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
Deployment Script for Distributed Chat System

Usage: $0 [OPTIONS]

Options:
    -e, --env ENV_FILE       Environment file to use (default: .env.prod)
    -s, --stack STACK_NAME   Stack name (default: chat-system)
    -b, --build              Build and push images before deploying
    -v, --verify             Verify deployment after completion
    -h, --help               Show this help message

Examples:
    # Deploy with default settings
    $0

    # Deploy with custom environment file
    $0 -e .env.staging

    # Build images and deploy
    $0 -b -v

    # Deploy with custom stack name
    $0 -s my-chat-stack
EOF
}

# ==============================================================================
# Parse Command Line Arguments
# ==============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--env)
            ENV_FILE="$2"
            shift 2
            ;;
        -s|--stack)
            STACK_NAME="$2"
            shift 2
            ;;
        -b|--build)
            BUILD_IMAGES=true
            shift
            ;;
        -v|--verify)
            VERIFY_DEPLOYMENT=true
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
# Pre-deployment Checks
# ==============================================================================

print_info "Starting deployment checks..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if we're in a Swarm
if ! docker info | grep -q "Swarm: active"; then
    print_error "Docker Swarm is not active. Please initialize or join a swarm first."
    print_info "To initialize: docker swarm init --advertise-addr <IP>"
    exit 1
fi

# Check if environment file exists
if [ ! -f "$ENV_FILE" ]; then
    print_error "Environment file not found: $ENV_FILE"
    print_info "Please create the environment file from .env.example:"
    print_info "  cp ${DEPLOYMENT_DIR}/.env.example $ENV_FILE"
    exit 1
fi

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Docker Compose file not found: $COMPOSE_FILE"
    exit 1
fi

# Check if nodes are labeled
print_info "Checking node labels..."
NODE_LABELS=$(docker node ls --format "{{.ID}}" | while read node_id; do
    docker node inspect "$node_id" --format '{{ .Spec.Labels }}' 2>/dev/null || echo "{}"
done)

if ! echo "$NODE_LABELS" | grep -q "node_type"; then
    print_warning "Some nodes may not have node_type labels."
    print_info "Label nodes with: docker node update --label-add node_type=node1 <NODE-NAME>"
fi

print_success "Pre-deployment checks passed!"

# ==============================================================================
# Build and Push Images (Optional)
# ==============================================================================

if [ "$BUILD_IMAGES" = true ]; then
    print_info "Building and pushing Docker images..."
    
    # Source environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    # Build node image
    print_info "Building node image..."
    docker build -f "${PROJECT_ROOT}/Dockerfile.node" \
        -t "${REGISTRY}/chat-node:${VERSION}" \
        "${PROJECT_ROOT}"
    
    # Push to registry
    print_info "Pushing images to registry..."
    docker push "${REGISTRY}/chat-node:${VERSION}"
    
    print_success "Images built and pushed successfully!"
fi

# ==============================================================================
# Deploy Stack
# ==============================================================================

print_info "Deploying stack '${STACK_NAME}'..."

# Export environment variables from env file for stack deploy
set -a
source "$ENV_FILE"
set +a

# Deploy the stack with environment file
docker stack deploy \
    -c "$COMPOSE_FILE" \
    --with-registry-auth \
    "$STACK_NAME"

print_success "Stack deployed successfully!"

# ==============================================================================
# Post-deployment Information
# ==============================================================================

print_info "Deployment Information:"
echo "  Stack Name: ${STACK_NAME}"
echo "  Environment: ${ENV_FILE}"
echo ""

print_info "Checking service status..."
docker stack services "$STACK_NAME"

echo ""
print_info "Useful commands:"
echo "  View services:    docker stack services ${STACK_NAME}"
echo "  View tasks:       docker stack ps ${STACK_NAME}"
echo "  View logs:        docker service logs -f ${STACK_NAME}_node1"
echo "  Remove stack:     docker stack rm ${STACK_NAME}"

# ==============================================================================
# Verify Deployment (Optional)
# ==============================================================================

if [ "$VERIFY_DEPLOYMENT" = true ]; then
    print_info "Verifying deployment..."
    sleep 10  # Wait for services to start
    
    # Check if all services are running
    SERVICES=$(docker stack services "$STACK_NAME" --format "{{.Name}}" 2>/dev/null)
    
    if [ -z "$SERVICES" ]; then
        print_error "No services found in stack ${STACK_NAME}"
        exit 1
    fi
    
    ALL_HEALTHY=true
    for service in $SERVICES; do
        REPLICAS=$(docker service ls --filter "name=${service}" --format "{{.Replicas}}")
        print_info "Service ${service}: ${REPLICAS}"
        
        # Parse replicas in format "running/desired"
        RUNNING=$(echo "$REPLICAS" | cut -d'/' -f1)
        DESIRED=$(echo "$REPLICAS" | cut -d'/' -f2)
        
        if [ "$RUNNING" != "$DESIRED" ] || [ "$RUNNING" -eq 0 ]; then
            print_warning "Service ${service} is not fully ready"
            ALL_HEALTHY=false
        fi
    done
    
    if [ "$ALL_HEALTHY" = true ]; then
        print_success "All services are healthy!"
    else
        print_warning "Some services are not fully ready. Check logs for details."
    fi
    
    # Run health check script if available
    if [ -f "${SCRIPT_DIR}/health-check.sh" ]; then
        print_info "Running health checks..."
        bash "${SCRIPT_DIR}/health-check.sh" -s "$STACK_NAME"
    fi
fi

print_success "Deployment completed successfully!"
