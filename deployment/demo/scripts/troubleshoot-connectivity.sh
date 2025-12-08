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
else
    print_success "All tasks are scheduled"
fi
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
for port in 8081 8082 8083; do
    echo "Testing port $port..."
    if vagrant ssh node1 -c "curl -s -o /dev/null -w '%{http_code}' http://localhost:$port --connect-timeout 5" 2>&1 | grep -q "000\|52"; then
        print_warning "Port $port not responding (service may still be starting)"
    else
        print_success "Port $port is accessible"
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
echo "3. Try accessing from any node in the swarm:"
echo "   curl http://192.168.56.101:8081"
echo "   curl http://192.168.56.102:8081"
echo "   curl http://192.168.56.103:8081"
echo ""
echo "4. If containers keep restarting, check for application errors:"
echo "   vagrant ssh node1 -c 'docker service ps chat-demo_node1 --no-trunc'"
echo ""
echo "5. Redeploy if needed:"
echo "   vagrant ssh node1 -c 'docker stack rm chat-demo'"
echo "   sleep 10"
echo "   ./scripts/deploy-demo.sh"
echo ""
