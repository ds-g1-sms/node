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
    print_error "Vagrantfile not found at $DEMO_DIR"
    exit 1
fi

# Change to demo directory for all vagrant commands
cd "$DEMO_DIR"

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

# Check if we should build locally or use existing
if docker info &>/dev/null; then
    print_info "Building image locally..."
    # Build from project root
    (cd "$PROJECT_ROOT" && docker build -f Dockerfile.node -t chat-node:demo .)
    
    # Save image to file in demo directory (accessible to VMs via /vagrant)
    print_info "Saving image to transfer to VMs..."
    docker save chat-node:demo -o "$DEMO_DIR/chat-node-demo.tar"
    
    # Change back to demo directory for vagrant commands
    cd "$DEMO_DIR"
    
    # Load image on all VMs
    for node in node1 node2 node3; do
        print_info "Loading image on $node..."
        if vagrant ssh $node -c "docker load -i /vagrant/chat-node-demo.tar"; then
            print_success "Image loaded on $node"
        else
            print_error "Failed to load image on $node"
            exit 1
        fi
    done
    
    # Verify image is present on all nodes
    print_info "Verifying images on all nodes..."
    for node in node1 node2 node3; do
        if vagrant ssh $node -c "docker images | grep chat-node:demo" &>/dev/null; then
            print_success "Image verified on $node"
        else
            print_error "Image not found on $node"
            exit 1
        fi
    done
    
    # Clean up tar file
    rm -f "$DEMO_DIR/chat-node-demo.tar"
    print_success "Image loaded and verified on all nodes"
else
    print_warning "Docker not available on host. Building image on VMs..."
    
    # Change to demo directory for vagrant commands
    cd "$DEMO_DIR"
    
    # Build on manager node
    print_info "Building image on node1..."
    vagrant ssh node1 -c "cd /vagrant && docker build -f ../Dockerfile.node -t chat-node:demo .."
    
    # Save and transfer to other nodes
    print_info "Transferring image to worker nodes..."
    vagrant ssh node1 -c "docker save chat-node:demo -o /vagrant/chat-node-demo.tar"
    
    for node in node2 node3; do
        print_info "Loading image on $node..."
        if vagrant ssh $node -c "docker load -i /vagrant/chat-node-demo.tar"; then
            print_success "Image loaded on $node"
        else
            print_error "Failed to load image on $node"
            exit 1
        fi
    done
    
    # Clean up
    vagrant ssh node1 -c "rm -f /vagrant/chat-node-demo.tar"
    print_success "Image built and distributed to all nodes"
fi

echo ""

# Create deployment configuration for demo
print_info "Creating demo deployment configuration..."
cd "$DEMO_DIR"

cat > demo.env <<EOF
# Demo Environment Configuration
REGISTRY=
VERSION=demo
NODE1_WS_PORT=8080
NODE2_WS_PORT=8080
NODE3_WS_PORT=8080
NODE1_XMLRPC_PORT=9090
NODE2_XMLRPC_PORT=9090
NODE3_XMLRPC_PORT=9090
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
        published: 8080
        protocol: tcp
      - target: 9090
        published: 9090
        protocol: tcp
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
        published: 8080
        protocol: tcp
      - target: 9090
        published: 9090
        protocol: tcp
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
        published: 8080
        protocol: tcp
      - target: 9090
        published: 9090
        protocol: tcp
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
print_info "Waiting for services to be ready (this may take 30-60 seconds)..."
sleep 20

# Check if services are running
print_info "Verifying service deployment..."
vagrant ssh node1 -c "docker stack ps chat-demo"

echo ""
echo "=========================================="
print_success "Demo deployment complete!"
echo "=========================================="
echo ""
echo "Each node runs on a separate machine at port 8080:"
echo ""
echo "Access points:"
echo "  - Node 1: ws://192.168.56.101:8080"
echo "  - Node 2: ws://192.168.56.102:8080"
echo "  - Node 3: ws://192.168.56.103:8080"
echo ""
echo "Recommended: Connect to ws://192.168.56.101:8080"
echo ""
echo "To check logs:"
echo "  vagrant ssh node1 -c 'docker service logs -f chat-demo_node1'"
echo ""
echo "To check health:"
echo "  vagrant ssh node1 -c 'docker stack ps chat-demo'"
echo ""
echo "To test connectivity:"
echo "  curl -v http://192.168.56.101:8080"
echo ""
echo "To remove deployment:"
echo "  vagrant ssh node1 -c 'docker stack rm chat-demo'"
echo ""
