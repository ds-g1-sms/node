#!/bin/bash
# ==============================================================================
# Connectivity Troubleshooting Script for Demo Environment
# ==============================================================================
# This script helps diagnose WebSocket connectivity issues in the demo
#
# Usage: ./scripts/troubleshoot-connectivity.sh
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_DIR="$(dirname "$SCRIPT_DIR")"

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
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cd "$DEMO_DIR"

echo "=========================================="
echo "Connectivity Troubleshooting"
echo "=========================================="
echo ""

# Check VMs are running
print_info "Checking VM status..."
if ! vagrant status | grep -q "running"; then
    print_error "Some VMs are not running!"
    vagrant status
    echo ""
    echo "Start VMs with: vagrant up"
    exit 1
fi
print_success "All VMs are running"
echo ""

# Check Swarm status
print_info "Checking Docker Swarm status..."
SWARM_STATUS=$(vagrant ssh node1 -c "docker node ls" 2>&1)
if echo "$SWARM_STATUS" | grep -q "chat-node"; then
    print_success "Docker Swarm is active"
    echo "$SWARM_STATUS"
else
    print_error "Docker Swarm not properly configured!"
    exit 1
fi
echo ""

# Check if stack is deployed
print_info "Checking if chat-demo stack is deployed..."
STACK_SERVICES=$(vagrant ssh node1 -c "docker stack services chat-demo 2>&1")
if echo "$STACK_SERVICES" | grep -q "chat-demo"; then
    print_success "Stack is deployed"
    echo "$STACK_SERVICES"
else
    print_error "Stack not deployed!"
    echo ""
    echo "Deploy with: ./scripts/deploy-demo.sh"
    exit 1
fi
echo ""

# Check service tasks
print_info "Checking service task status..."
TASK_STATUS=$(vagrant ssh node1 -c "docker stack ps chat-demo --no-trunc" 2>&1)
echo "$TASK_STATUS"

# Check for failed tasks
if echo "$TASK_STATUS" | grep -qi "failed\|rejected"; then
    print_error "Some tasks have failed!"
    
    # Check if it's an image issue
    if echo "$TASK_STATUS" | grep -qi "No such image"; then
        print_error "Image not found on nodes! This usually means the image wasn't properly distributed."
        echo ""
        print_info "Checking which nodes have the image..."
        for node in node1 node2 node3; do
            if vagrant ssh $node -c "docker images | grep chat-node:demo" &>/dev/null; then
                print_success "Image found on $node"
            else
                print_error "Image NOT found on $node"
            fi
        done
        echo ""
        echo "To fix this issue:"
        echo "1. Remove the failed stack: vagrant ssh node1 -c 'docker stack rm chat-demo'"
        echo "2. Wait 10 seconds for cleanup"
        echo "3. Re-run deployment: ./scripts/deploy-demo.sh"
        echo ""
    fi
else
    print_success "All tasks are scheduled"
fi
echo ""

# Check images on each node
print_info "Checking Docker images on each node..."
for node in node1 node2 node3; do
    echo "--- $node ---"
    vagrant ssh $node -c "docker images | grep -E 'REPOSITORY|chat-node'" 2>&1 || echo "No chat-node images found"
done
echo ""

# Check containers are running on each node
print_info "Checking containers on each node..."
for node in node1 node2 node3; do
    echo "--- $node ---"
    vagrant ssh $node -c "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" 2>&1
done
echo ""

# Test port connectivity from each VM
print_info "Testing port connectivity from VMs..."
echo "Testing WebSocket port 8080 on each node..."
for node_ip in 192.168.56.101 192.168.56.102 192.168.56.103; do
    node_name=$(echo $node_ip | sed 's/192.168.56.10/node/')
    if vagrant ssh node1 -c "curl -s -o /dev/null -w '%{http_code}' http://$node_ip:8080 --connect-timeout 5" 2>&1 | grep -q "000\|52"; then
        print_warning "Port 8080 on $node_name ($node_ip) not responding (service may still be starting)"
    else
        print_success "Port 8080 on $node_name ($node_ip) is accessible"
    fi
done
echo ""

# Check service logs for errors
print_info "Checking service logs (last 20 lines)..."
for service in node1 node2 node3; do
    echo "--- chat-demo_$service ---"
    vagrant ssh node1 -c "docker service logs --tail 20 chat-demo_$service 2>&1" | tail -20
    echo ""
done

# Test network connectivity
print_info "Testing network connectivity between VMs..."
vagrant ssh node1 -c "ping -c 2 192.168.56.102 > /dev/null 2>&1" && print_success "node1 -> node2: OK" || print_error "node1 -> node2: FAIL"
vagrant ssh node1 -c "ping -c 2 192.168.56.103 > /dev/null 2>&1" && print_success "node1 -> node3: OK" || print_error "node1 -> node3: FAIL"
vagrant ssh node2 -c "ping -c 2 192.168.56.103 > /dev/null 2>&1" && print_success "node2 -> node3: OK" || print_error "node2 -> node3: FAIL"
echo ""

# Check ingress network
print_info "Checking Docker ingress network..."
vagrant ssh node1 -c "docker network inspect ingress --format '{{range .Containers}}{{.Name}} {{end}}'" 2>&1
echo ""

# Recommendations
echo "=========================================="
echo "Recommendations"
echo "=========================================="
echo ""
echo "If services are not accessible:"
echo ""
echo "1. Wait 30-60 seconds after deployment for services to fully start"
echo ""
echo "2. Check service logs for startup errors:"
echo "   vagrant ssh node1 -c 'docker service logs -f chat-demo_node1'"
echo ""
echo "3. Try accessing each node (all use port 8080):"
echo "   curl http://192.168.56.101:8080"
echo "   curl http://192.168.56.102:8080"
echo "   curl http://192.168.56.103:8080"
echo ""
echo "4. If containers keep restarting, check for application errors:"
echo "   vagrant ssh node1 -c 'docker service ps chat-demo_node1 --no-trunc'"
echo ""
echo "5. Redeploy if needed:"
echo "   vagrant ssh node1 -c 'docker stack rm chat-demo'"
echo "   sleep 10"
echo "   ./scripts/deploy-demo.sh"
echo ""
