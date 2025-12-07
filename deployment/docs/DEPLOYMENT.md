# Deployment Guide - Distributed Chat System

This guide provides comprehensive instructions for deploying the distributed chat system in production using Docker Swarm across multiple machines.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Machine Setup](#machine-setup)
- [Docker Swarm Configuration](#docker-swarm-configuration)
- [Image Build and Registry](#image-build-and-registry)
- [Configuration](#configuration)
- [Deployment Steps](#deployment-steps)
- [Verification](#verification)
- [Client Connections](#client-connections)
- [Troubleshooting](#troubleshooting)

## Overview

The production deployment uses Docker Swarm to orchestrate three chat node services across three separate machines, providing:

- **Multi-host deployment**: Each node runs on a dedicated physical or virtual machine
- **Service discovery**: Nodes automatically discover peers via overlay network
- **Health monitoring**: Automatic health checks and restart on failure
- **Rolling updates**: Zero-downtime deployments
- **Resource management**: CPU and memory limits enforced
- **Log aggregation**: Centralized logging from all nodes

## Prerequisites

### Hardware Requirements

Three machines (physical or virtual) with minimum specifications:

- **CPU**: 2 cores per machine
- **RAM**: 4GB per machine
- **Disk**: 20GB available per machine
- **Network**: Reliable network connectivity between machines

### Software Requirements

On each machine:

- **Operating System**: Linux (Ubuntu 20.04+ or CentOS 8+ recommended)
- **Docker Engine**: Version 20.10 or later
- **Docker Compose**: Version 1.29 or later (for local testing)
- **Network**: Open ports for Docker Swarm and application

### Required Ports

Each machine must have the following ports accessible:

**Docker Swarm Ports:**
- `2377/tcp` - Cluster management
- `7946/tcp` and `7946/udp` - Node communication
- `4789/udp` - Overlay network traffic

**Application Ports (per node):**
- `8081/tcp` - Node 1 WebSocket (client connections)
- `9091/tcp` - Node 1 XML-RPC (inter-node communication)
- `8082/tcp` - Node 2 WebSocket
- `9092/tcp` - Node 2 XML-RPC
- `8083/tcp` - Node 3 WebSocket
- `9093/tcp` - Node 3 XML-RPC

## Architecture

### Deployment Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Swarm Cluster                     │
├──────────────────┬────────────────┬─────────────────────────┤
│                  │                │                          │
│   Machine 1      │   Machine 2    │   Machine 3             │
│   (Manager)      │   (Worker)     │   (Worker)              │
│                  │                │                          │
│  ┌────────────┐  │ ┌────────────┐ │ ┌────────────┐          │
│  │   Node 1   │  │ │   Node 2   │ │ │   Node 3   │          │
│  │            │  │ │            │ │ │            │          │
│  │ WS:  8081  │  │ │ WS:  8082  │ │ │ WS:  8083  │          │
│  │ RPC: 9091  │  │ │ RPC: 9092  │ │ │ RPC: 9093  │          │
│  └────────────┘  │ └────────────┘ │ └────────────┘          │
│                  │                │                          │
└──────────────────┴────────────────┴─────────────────────────┘
          │                │                │
          └────────────────┴────────────────┘
                   Overlay Network
                   (10.10.0.0/16)
```

### Service Distribution

The deployment uses Docker Swarm placement constraints to ensure:

- Node 1 service runs only on machines labeled `node_type=node1`
- Node 2 service runs only on machines labeled `node_type=node2`
- Node 3 service runs only on machines labeled `node_type=node3`

## Machine Setup

### 1. Provision Machines

Provision three machines with the required specifications. For this guide, we'll use:

- **Machine 1**: `192.168.1.10` (will be Swarm manager)
- **Machine 2**: `192.168.1.11` (worker)
- **Machine 3**: `192.168.1.12` (worker)

### 2. Install Docker

On each machine, install Docker Engine:

```bash
# Update package index
sudo apt-get update

# Install dependencies
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Verify installation
docker --version
```

### 3. Configure Firewall

On each machine, configure firewall to allow required ports:

```bash
# Docker Swarm ports
sudo ufw allow 2377/tcp
sudo ufw allow 7946/tcp
sudo ufw allow 7946/udp
sudo ufw allow 4789/udp

# Application ports (adjust per machine)
# On Machine 1:
sudo ufw allow 8081/tcp
sudo ufw allow 9091/tcp

# On Machine 2:
sudo ufw allow 8082/tcp
sudo ufw allow 9092/tcp

# On Machine 3:
sudo ufw allow 8083/tcp
sudo ufw allow 9093/tcp

# Enable firewall
sudo ufw enable
```

## Docker Swarm Configuration

### 1. Initialize Swarm (Manager Node)

On Machine 1 (192.168.1.10):

```bash
# Initialize Swarm with advertised address
docker swarm init --advertise-addr 192.168.1.10

# Output will include a join command like:
# docker swarm join --token SWMTKN-1-xxxxx 192.168.1.10:2377
```

Save the join token for worker nodes.

### 2. Join Worker Nodes

On Machine 2 (192.168.1.11):

```bash
docker swarm join --token SWMTKN-1-xxxxx 192.168.1.10:2377
```

On Machine 3 (192.168.1.12):

```bash
docker swarm join --token SWMTKN-1-xxxxx 192.168.1.10:2377
```

### 3. Verify Swarm Cluster

On the manager node (Machine 1):

```bash
docker node ls
```

You should see all three nodes listed.

### 4. Label Nodes

Label each node to control service placement:

```bash
# Get node IDs or names
docker node ls

# Label Machine 1 for node1
docker node update --label-add node_type=node1 <MACHINE1-NODE-NAME>

# Label Machine 2 for node2
docker node update --label-add node_type=node2 <MACHINE2-NODE-NAME>

# Label Machine 3 for node3
docker node update --label-add node_type=node3 <MACHINE3-NODE-NAME>

# Verify labels
docker node inspect <NODE-NAME> --format '{{ .Spec.Labels }}'
```

## Image Build and Registry

### Option 1: Using Docker Hub (Recommended)

1. **Create Docker Hub account** (if not already)

2. **Login to Docker Hub** on the manager node:

```bash
docker login
```

3. **Build and push images**:

```bash
# Clone repository (if not already)
git clone https://github.com/ds-g1-sms/node.git
cd node

# Build node image
docker build -f Dockerfile.node -t yourusername/chat-node:v1.0 .

# Push to Docker Hub
docker push yourusername/chat-node:v1.0
```

4. **Update environment file** with your registry:

```bash
# In deployment/.env.prod
REGISTRY=yourusername
VERSION=v1.0
```

### Option 2: Private Registry

If using a private registry:

```bash
# Build and tag
docker build -f Dockerfile.node -t registry.example.com/chat-node:v1.0 .

# Push to private registry
docker push registry.example.com/chat-node:v1.0

# Update .env.prod
REGISTRY=registry.example.com
VERSION=v1.0
```

## Configuration

### 1. Create Environment File

On the manager node:

```bash
cd deployment
cp .env.example .env.prod
```

### 2. Edit Configuration

Edit `.env.prod` with your settings:

```bash
nano .env.prod
```

Key settings to configure:

```bash
# Registry configuration
REGISTRY=yourusername  # or your registry URL
VERSION=v1.0

# Port configuration (use defaults or customize)
NODE1_WS_PORT=8081
NODE2_WS_PORT=8082
NODE3_WS_PORT=8083

# Logging
LOG_LEVEL=INFO

# Resources (adjust based on your hardware)
CPU_LIMIT=1.0
MEMORY_LIMIT=512M
```

### 3. Verify Configuration Files

Ensure all configuration files are in place:

```bash
ls -la deployment/
# Should show:
# - docker-compose.prod.yml
# - .env.prod
# - configs/node1.env
# - configs/node2.env
# - configs/node3.env
```

## Deployment Steps

### Method 1: Using Deployment Script (Recommended)

The automated deployment script handles the entire process:

```bash
cd deployment

# Deploy with environment file
./scripts/deploy.sh -e .env.prod -v

# Or with image building
./scripts/deploy.sh -e .env.prod -b -v
```

### Method 2: Manual Deployment

If you prefer manual deployment:

```bash
cd deployment

# Deploy the stack
docker stack deploy \
    -c docker-compose.prod.yml \
    --with-registry-auth \
    chat-system
```

### Verify Deployment

```bash
# Check stack services
docker stack services chat-system

# Expected output:
# ID     NAME                MODE    REPLICAS  IMAGE
# xxx    chat-system_node1   replicated   1/1    user/chat-node:v1.0
# xxx    chat-system_node2   replicated   1/1    user/chat-node:v1.0
# xxx    chat-system_node3   replicated   1/1    user/chat-node:v1.0

# Check service placement
docker stack ps chat-system

# View logs
docker service logs -f chat-system_node1
```

## Verification

### 1. Automated Health Checks

Run the health check script:

```bash
cd deployment
./scripts/health-check.sh -s chat-system -v
```

### 2. Manual Verification

Check each service:

```bash
# Check service status
docker service ps chat-system_node1
docker service ps chat-system_node2
docker service ps chat-system_node3

# Test health endpoints
curl -X POST http://192.168.1.10:9091 \
  -H "Content-Type: text/xml" \
  -d '<?xml version="1.0"?><methodCall><methodName>heartbeat</methodName></methodCall>'
```

### 3. Inter-Node Communication Test

Verify nodes can communicate:

```bash
# From any node container
docker exec $(docker ps -q -f name=node1) \
  python -c "import xmlrpc.client; print(xmlrpc.client.ServerProxy('http://node2:9090').heartbeat())"
```

## Client Connections

### Connecting Clients

Clients can connect to any node via WebSocket:

- Node 1: `ws://192.168.1.10:8081`
- Node 2: `ws://192.168.1.11:8082`
- Node 3: `ws://192.168.1.12:8083`

### Example Client Connection

```bash
# On your local machine or client machine
poetry install
poetry run chat-client

# In the client UI:
# - Enter username
# - Enter node address: 192.168.1.10:8081 (or any node)
# - Click Connect
```

### Load Balancer (Optional)

For production, consider adding a load balancer (HAProxy, nginx):

```nginx
# nginx configuration example
upstream chat_nodes {
    server 192.168.1.10:8081;
    server 192.168.1.11:8082;
    server 192.168.1.12:8083;
}

server {
    listen 80;
    server_name chat.example.com;
    
    location / {
        proxy_pass http://chat_nodes;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

## Troubleshooting

### Services Not Starting

```bash
# Check service logs
docker service logs chat-system_node1

# Check task details
docker service ps chat-system_node1 --no-trunc

# Inspect service
docker service inspect chat-system_node1
```

### Node Placement Issues

```bash
# Verify node labels
docker node inspect <NODE-NAME> | grep -A 10 Labels

# Update labels if needed
docker node update --label-add node_type=node1 <NODE-NAME>
```

### Network Connectivity Issues

```bash
# Check overlay network
docker network ls
docker network inspect chat-system_chat-overlay

# Test connectivity between nodes
docker exec $(docker ps -q -f name=node1) ping node2
```

### Image Pull Errors

```bash
# Ensure logged into registry
docker login

# Verify image exists
docker pull yourusername/chat-node:v1.0

# Check registry auth
docker stack deploy \
    -c docker-compose.prod.yml \
    --with-registry-auth \
    chat-system
```

### Health Check Failures

```bash
# Check container health
docker inspect $(docker ps -q -f name=node1) | grep -A 20 Health

# Test health check manually
docker exec $(docker ps -q -f name=node1) \
  python -c "import xmlrpc.client; xmlrpc.client.ServerProxy('http://localhost:9090').heartbeat()"
```

For more troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## Next Steps

- [Operations Manual](OPERATIONS.md) - Day-to-day operations
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- Configure monitoring and alerting
- Set up automated backups
- Implement CI/CD pipeline

## Support

For issues or questions:
- Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
- Review logs: `./scripts/logs.sh -f`
- Contact: ds-g1-sms team
