#!/bin/bash
# ==============================================================================
# Demo Deployment Script
# ==============================================================================
# This script deploys the chat system to the demo Vagrant VMs
#
# Usage: Run from the host machine:
#   cd deployment/demo
#   ./scripts/deploy-demo.sh
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_DIR="$(dirname "$DEMO_DIR")"
PROJECT_ROOT="$(dirname "$DEPLOYMENT_DIR")"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

# Check if we're in the right directory
if [ ! -f "$DEMO_DIR/Vagrantfile" ]; then
    print_error "Must be run from deployment/demo directory"
    exit 1
fi

print_info "Starting demo deployment..."
echo ""

# Check if VMs are running
print_info "Checking VM status..."
if ! vagrant status | grep -q "running"; then
    print_warning "VMs are not running. Starting them now..."
    vagrant up
fi

print_success "VMs are running"
echo ""

# Setup Swarm if not already done
print_info "Setting up Swarm cluster..."
vagrant ssh node1 -c "bash /vagrant/scripts/setup-swarm.sh"

echo ""

# Build Docker image
print_info "Building Docker image..."
cd "$PROJECT_ROOT"

# Check if we should build locally or use existing
if docker info &>/dev/null; then
    print_info "Building image locally..."
    docker build -f Dockerfile.node -t chat-node:demo .
    
    # Save image to file
    print_info "Saving image to transfer to VMs..."
    docker save chat-node:demo -o /tmp/chat-node-demo.tar
    
    # Load image on all VMs
    for node in node1 node2 node3; do
        print_info "Loading image on $node..."
        vagrant ssh $node -c "docker load -i /tmp/chat-node-demo.tar" || true
    done
    
    rm -f /tmp/chat-node-demo.tar
    print_success "Image loaded on all nodes"
else
    print_warning "Docker not available on host. Image must be built on VMs."
    vagrant ssh node1 -c "cd /vagrant && docker build -f Dockerfile.node -t chat-node:demo ."
fi

echo ""

# Create deployment configuration for demo
print_info "Creating demo deployment configuration..."
cd "$DEMO_DIR"

cat > demo.env <<EOF
# Demo Environment Configuration
REGISTRY=
VERSION=demo
NODE1_WS_PORT=8081
NODE2_WS_PORT=8082
NODE3_WS_PORT=8083
NODE1_XMLRPC_PORT=9091
NODE2_XMLRPC_PORT=9092
NODE3_XMLRPC_PORT=9093
LOG_LEVEL=INFO
CPU_LIMIT=1.0
MEMORY_LIMIT=512M
CPU_RESERVATION=0.25
MEMORY_RESERVATION=256M
EOF

print_success "Configuration created"
echo ""

# Create demo docker-compose file
print_info "Creating demo compose file..."
cat > docker-compose.demo.yml <<'EOF'
version: '3.8'

services:
  node1:
    image: chat-node:demo
    hostname: node1
    networks:
      - chat-overlay
    ports:
      - target: 8080
        published: 8081
        protocol: tcp
        mode: host
      - target: 9090
        published: 9091
        protocol: tcp
        mode: host
    environment:
      - NODE_ID=node1
      - XMLRPC_PORT=9090
      - WEBSOCKET_PORT=8080
      - XMLRPC_HOST=0.0.0.0
      - WEBSOCKET_HOST=0.0.0.0
      - XMLRPC_ADDRESS=http://node1:9090
      - PEER_NODES=node2:http://node2:9090,node3:http://node3:9090
      - LOG_LEVEL=INFO
    volumes:
      - node1-logs:/var/log/chatnode
    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints:
          - node.labels.node_type == node1
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD", "python", "-c", "import xmlrpc.client; xmlrpc.client.ServerProxy('http://localhost:9090').heartbeat()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  node2:
    image: chat-node:demo
    hostname: node2
    networks:
      - chat-overlay
    ports:
      - target: 8080
        published: 8082
        protocol: tcp
        mode: host
      - target: 9090
        published: 9092
        protocol: tcp
        mode: host
    environment:
      - NODE_ID=node2
      - XMLRPC_PORT=9090
      - WEBSOCKET_PORT=8080
      - XMLRPC_HOST=0.0.0.0
      - WEBSOCKET_HOST=0.0.0.0
      - XMLRPC_ADDRESS=http://node2:9090
      - PEER_NODES=node1:http://node1:9090,node3:http://node3:9090
      - LOG_LEVEL=INFO
    volumes:
      - node2-logs:/var/log/chatnode
    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints:
          - node.labels.node_type == node2
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD", "python", "-c", "import xmlrpc.client; xmlrpc.client.ServerProxy('http://localhost:9090').heartbeat()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  node3:
    image: chat-node:demo
    hostname: node3
    networks:
      - chat-overlay
    ports:
      - target: 8080
        published: 8083
        protocol: tcp
        mode: host
      - target: 9090
        published: 9093
        protocol: tcp
        mode: host
    environment:
      - NODE_ID=node3
      - XMLRPC_PORT=9090
      - WEBSOCKET_PORT=8080
      - XMLRPC_HOST=0.0.0.0
      - WEBSOCKET_HOST=0.0.0.0
      - XMLRPC_ADDRESS=http://node3:9090
      - PEER_NODES=node1:http://node1:9090,node2:http://node2:9090
      - LOG_LEVEL=INFO
    volumes:
      - node3-logs:/var/log/chatnode
    deploy:
      mode: replicated
      replicas: 1
      placement:
        constraints:
          - node.labels.node_type == node3
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD", "python", "-c", "import xmlrpc.client; xmlrpc.client.ServerProxy('http://localhost:9090').heartbeat()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  chat-overlay:
    driver: overlay
    attachable: true

volumes:
  node1-logs:
  node2-logs:
  node3-logs:
EOF

print_success "Demo compose file created"
echo ""

# Deploy to Swarm
print_info "Deploying stack to Swarm..."
vagrant ssh node1 -c "cd /vagrant && docker stack deploy -c docker-compose.demo.yml chat-demo"

echo ""
print_success "Deployment initiated!"
echo ""

# Wait a bit and check status
sleep 10

print_info "Checking deployment status..."
vagrant ssh node1 -c "docker stack services chat-demo"

echo ""
echo "=========================================="
print_success "Demo deployment complete!"
echo "=========================================="
echo ""
echo "Access points:"
echo "  Node 1: http://192.168.56.101:8081 (WebSocket)"
echo "  Node 2: http://192.168.56.102:8082 (WebSocket)"
echo "  Node 3: http://192.168.56.103:8083 (WebSocket)"
echo ""
echo "To check logs:"
echo "  vagrant ssh node1 -c 'docker service logs -f chat-demo_node1'"
echo ""
echo "To check health:"
echo "  vagrant ssh node1 -c 'docker stack ps chat-demo'"
echo ""
echo "To remove deployment:"
echo "  vagrant ssh node1 -c 'docker stack rm chat-demo'"
echo ""
