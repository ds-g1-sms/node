#!/bin/bash
# ==============================================================================
# Setup Script for Docker Swarm on Demo VMs
# ==============================================================================
# This script labels nodes and prepares the Swarm cluster for deployment
#
# Usage: Run this from the manager node (node1) via:
#   vagrant ssh node1 -- /vagrant/scripts/setup-swarm.sh
# ==============================================================================

set -e

echo "=========================================="
echo "Setting up Docker Swarm for Chat System"
echo "=========================================="
echo ""

# Check if running on manager node
if ! docker node ls &>/dev/null; then
    echo "Error: This script must be run on the Swarm manager node"
    exit 1
fi

echo "Current Swarm status:"
docker node ls
echo ""

# Label nodes for placement constraints
echo "Applying node labels for placement constraints..."
docker node update --label-add node_type=node1 chat-node1
docker node update --label-add node_type=node2 chat-node2
docker node update --label-add node_type=node3 chat-node3

echo ""
echo "Node labels applied successfully!"
echo ""

# Verify labels
echo "Node 1 labels:"
docker node inspect chat-node1 --format '{{.Spec.Labels}}'

echo "Node 2 labels:"
docker node inspect chat-node2 --format '{{.Spec.Labels}}'

echo "Node 3 labels:"
docker node inspect chat-node3 --format '{{.Spec.Labels}}'

echo ""
echo "=========================================="
echo "Swarm setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Build and push your Docker images"
echo "2. Copy deployment files to manager node"
echo "3. Run: cd /vagrant/deployment && ./scripts/deploy.sh -e .env.prod"
echo ""
