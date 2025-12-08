# Multi-VM Demo for Distributed Chat System

This directory contains a complete demo environment that creates three virtual machines to demonstrate the production deployment of the distributed chat system using Docker Swarm.

## Overview

The demo automatically provisions three Ubuntu VMs using Vagrant and VirtualBox, sets up Docker Swarm across them, and deploys the chat system in a truly distributed manner - exactly as it would be deployed in production.

## Prerequisites

Before running the demo, you need the following installed on your host machine:

### Required Software

1. **VirtualBox** (6.1 or later)
   - Download: https://www.virtualbox.org/wiki/Downloads
   - Used to run the virtual machines

2. **Vagrant** (2.3 or later)
   - Download: https://www.vagrantup.com/downloads
   - Used to manage and provision VMs

3. **Docker** (optional, for building images locally)
   - Download: https://www.docker.com/get-started
   - If not available, images will be built on the VMs

### System Requirements

- **CPU**: 6+ cores recommended (2 per VM)
- **RAM**: 8GB minimum (2GB per VM + host overhead)
- **Disk**: 20GB free space
- **OS**: Windows, macOS, or Linux

## Quick Start

### 1. Start the VMs

From this directory (`deployment/demo`), run:

```bash
vagrant up
```

This will:
- Download the Ubuntu 22.04 base box (first time only)
- Create three VMs: `node1`, `node2`, `node3`
- Install Docker on each VM
- Initialize Docker Swarm with `node1` as manager
- Join `node2` and `node3` as workers
- Configure networking between VMs

**Expected time**: 10-15 minutes (first run)

### 2. Verify the Setup

Check that all VMs are running:

```bash
vagrant status
```

Expected output:
```
node1                     running (virtualbox)
node2                     running (virtualbox)
node3                     running (virtualbox)
```

Check Swarm status:

```bash
vagrant ssh node1 -c "docker node ls"
```

### 3. Label Nodes (if not done automatically)

```bash
vagrant ssh node1 -c "bash /vagrant/scripts/setup-swarm.sh"
```

### 4. Deploy the Chat System

#### Option A: Automated Deployment (Recommended)

```bash
./scripts/deploy-demo.sh
```

This script will:
- Build the Docker image
- Transfer it to all VMs
- Create demo configuration
- Deploy the stack to Swarm
- Show access information

#### Option B: Manual Deployment

Build the image:

```bash
cd ../..  # Go to project root
docker build -f Dockerfile.node -t chat-node:demo .
docker save chat-node:demo -o /tmp/chat-node-demo.tar
```

Transfer and load on each VM:

```bash
cd deployment/demo
vagrant ssh node1 -c "docker load -i /tmp/chat-node-demo.tar"
vagrant ssh node2 -c "docker load -i /tmp/chat-node-demo.tar"
vagrant ssh node3 -c "docker load -i /tmp/chat-node-demo.tar"
```

Deploy the stack:

```bash
vagrant ssh node1 -c "cd /vagrant && docker stack deploy -c docker-compose.demo.yml chat-demo"
```

### 5. Access the System

Once deployed, you can access the nodes:

- **Node 1**: http://192.168.56.101:8081 (WebSocket)
- **Node 2**: http://192.168.56.102:8082 (WebSocket)
- **Node 3**: http://192.168.56.103:8083 (WebSocket)

Connect using the chat client:

```bash
# From project root
poetry run chat-client
```

Then connect to any of the nodes using their IP:port (e.g., `192.168.56.101:8081`)

## VM Network Configuration

The demo creates a private network with the following configuration:

| VM | Hostname | IP Address | WebSocket Port | XML-RPC Port |
|----|----------|------------|----------------|--------------|
| node1 | chat-node1 | 192.168.56.101 | 8081 | 9091 |
| node2 | chat-node2 | 192.168.56.102 | 8082 | 9092 |
| node3 | chat-node3 | 192.168.56.103 | 8083 | 9093 |

## Useful Commands

### VM Management

```bash
# Start all VMs
vagrant up

# Start a specific VM
vagrant up node1

# Stop all VMs
vagrant halt

# Restart all VMs
vagrant reload

# Destroy all VMs (clean up)
vagrant destroy -f

# SSH into a VM
vagrant ssh node1

# Check VM status
vagrant status
```

### Docker Swarm Operations

```bash
# Check Swarm nodes (from manager)
vagrant ssh node1 -c "docker node ls"

# Check stack services
vagrant ssh node1 -c "docker stack services chat-demo"

# Check service tasks (where they're running)
vagrant ssh node1 -c "docker stack ps chat-demo"

# View logs from a service
vagrant ssh node1 -c "docker service logs -f chat-demo_node1"

# Check service health
vagrant ssh node1 -c "docker service ps chat-demo --no-trunc"
```

### Deployment Operations

```bash
# Deploy stack
vagrant ssh node1 -c "cd /vagrant && docker stack deploy -c docker-compose.demo.yml chat-demo"

# Update a service
vagrant ssh node1 -c "docker service update chat-demo_node1"

# Remove stack
vagrant ssh node1 -c "docker stack rm chat-demo"
```

### Debugging

```bash
# Check Docker on a node
vagrant ssh node2 -c "docker ps"

# Check network connectivity
vagrant ssh node1 -c "ping -c 3 192.168.56.102"

# Check if services can communicate
vagrant ssh node1 -c "docker exec \$(docker ps -q -f name=node1) ping -c 3 node2"

# View all containers across cluster
for node in node1 node2 node3; do
  echo "=== $node ==="
  vagrant ssh $node -c "docker ps"
done
```

## Architecture

```
Host Machine (your computer)
│
├── VirtualBox
│   │
│   ├── VM: node1 (192.168.56.101) - Swarm Manager
│   │   └── Docker: chat-demo_node1 service
│   │
│   ├── VM: node2 (192.168.56.102) - Swarm Worker
│   │   └── Docker: chat-demo_node2 service
│   │
│   └── VM: node3 (192.168.56.103) - Swarm Worker
│       └── Docker: chat-demo_node3 service
│
└── Private Network: 192.168.56.0/24
    └── Overlay Network: Docker Swarm (chat-overlay)
```

## Troubleshooting

### VMs won't start

```bash
# Check VirtualBox is installed
VBoxManage --version

# Check for resource conflicts
vagrant global-status
vagrant global-status --prune  # Clean up old entries
```

### Swarm not initializing

```bash
# Check if Swarm is initialized
vagrant ssh node1 -c "docker info | grep Swarm"

# Reinitialize if needed
vagrant ssh node1 -c "docker swarm init --advertise-addr 192.168.56.101"
```

### Services not starting

**Error: "No such image: chat-node:demo"**

This means the Docker image wasn't properly distributed to all nodes in the Swarm.

**Solution:**

1. Remove the failed stack:
   ```bash
   vagrant ssh node1 -c "docker stack rm chat-demo"
   sleep 10
   ```

2. Verify images are missing:
   ```bash
   for node in node1 node2 node3; do
     echo "=== $node ==="
     vagrant ssh $node -c "docker images | grep chat-node"
   done
   ```

3. Re-run the deployment script (it will rebuild and distribute the image):
   ```bash
   ./scripts/deploy-demo.sh
   ```

**Prevention:** The deployment script now automatically verifies images on all nodes before deployment.

**Other service issues:**

```bash
# Check service logs
vagrant ssh node1 -c "docker service logs chat-demo_node1"

# Check node availability
vagrant ssh node1 -c "docker node ls"

# Check service status
vagrant ssh node1 -c "docker stack ps chat-demo --no-trunc"
```

### Network connectivity issues

```bash
# Test VM network
vagrant ssh node1 -c "ping -c 3 192.168.56.102"

# Test overlay network (from container)
vagrant ssh node1 -c "docker exec \$(docker ps -q -f name=node1) ping -c 3 node2"

# Check firewall rules (shouldn't be an issue in VMs)
vagrant ssh node1 -c "sudo iptables -L"
```

### WebSocket errors in logs (EXPECTED - NOT A PROBLEM)

You may see errors like these in the service logs:

```
websockets.server - ERROR - opening handshake failed
EOFError: connection closed while reading HTTP request line
websockets.exceptions.InvalidUpgrade: missing Connection header
connection rejected (426 Upgrade Required)
```

**These are NORMAL and can be safely ignored.** They occur when:
- Docker Swarm's ingress network does TCP health checks on published ports
- Non-WebSocket clients (like curl or health probes) try to connect to WebSocket ports
- Port scanners or load balancers probe the ports

The WebSocket server is working correctly. These errors don't affect functionality - actual WebSocket clients with proper upgrade headers will connect successfully. You'll see "Node server ready" and "WebSocket server started" messages indicating everything is working.

### Can't connect from chat client

**Common Issue**: Connection refused on port 8081/8082/8083

This usually happens if services are still starting up. Docker Swarm services can take 30-60 seconds to fully initialize.

**Solutions**:

1. **Wait for services to be ready**:
   ```bash
   vagrant ssh node1 -c "docker stack ps chat-demo"
   ```
   All services should show "Running" state.

2. **Check service logs**:
   ```bash
   vagrant ssh node1 -c "docker service logs chat-demo_node1"
   ```
   Look for "WebSocket server started" or similar messages.

3. **Test from inside a VM**:
   ```bash
   vagrant ssh node1 -c "curl -v http://localhost:8081"
   ```
   If this works but external access doesn't, it's a networking issue.

4. **Verify Swarm ingress networking**:
   ```bash
   vagrant ssh node1 -c "docker network inspect ingress"
   ```
   Should show all nodes in the swarm.

5. **Check if containers are running**:
   ```bash
   vagrant ssh node1 -c "docker ps"
   vagrant ssh node2 -c "docker ps"
   vagrant ssh node3 -c "docker ps"
   ```

6. **Verify port publishing**:
   ```bash
   vagrant ssh node1 -c "docker service inspect chat-demo_node1 --format '{{json .Endpoint.Ports}}'"
   ```

7. **Try accessing from any Swarm node** (Swarm ingress routing):
   - http://192.168.56.101:8081 (from manager)
   - http://192.168.56.102:8081 (from worker 1)
   - http://192.168.56.103:8081 (from worker 2)
   
   All should work due to Swarm's routing mesh!

## Customization

### Changing VM Resources

Edit the `Vagrantfile`:

```ruby
config.vm.provider "virtualbox" do |vb|
  vb.memory = "4096"  # Increase RAM
  vb.cpus = 4         # Increase CPUs
end
```

Then reload:

```bash
vagrant reload
```

### Using Different Network Range

Edit the `Vagrantfile` and change the IP addresses:

```ruby
{ name: "node1", ip: "10.0.0.101", hostname: "chat-node1" },
```

### Adding More Nodes

While the system is designed for 3 nodes, you can add more for testing:

1. Add to the `nodes` array in `Vagrantfile`
2. Update `docker-compose.demo.yml` with additional services
3. Update peer configurations

## Cleaning Up

To remove all VMs and free up resources:

```bash
# Stop and destroy all VMs
vagrant destroy -f

# Remove any generated files
rm -f swarm-token.txt swarm-manager-ip.txt demo.env docker-compose.demo.yml
```

## Demo Scenarios

### 1. Normal Operation

Deploy and watch logs to see nodes communicating:

```bash
./scripts/deploy-demo.sh
vagrant ssh node1 -c "docker service logs -f chat-demo_node1" &
vagrant ssh node1 -c "docker service logs -f chat-demo_node2" &
vagrant ssh node1 -c "docker service logs -f chat-demo_node3" &
```

### 2. Node Failure Simulation

Stop a node and watch the system handle it:

```bash
# Stop node2
vagrant halt node2

# Check service status
vagrant ssh node1 -c "docker stack ps chat-demo"

# Restart node2
vagrant up node2
```

### 3. Rolling Update

Update the service with zero downtime:

```bash
# Build new version
docker build -f Dockerfile.node -t chat-node:v2 .
docker save chat-node:v2 -o /tmp/chat-node-v2.tar

# Load on all nodes
for node in node1 node2 node3; do
  vagrant ssh $node -c "docker load -i /tmp/chat-node-v2.tar"
done

# Update service
vagrant ssh node1 -c "docker service update --image chat-node:v2 chat-demo_node1"
```

## Next Steps

After testing the demo:

1. Review the `../docs/DEPLOYMENT.md` for production deployment
2. Understand the differences between demo and production
3. Plan your actual production infrastructure
4. Consider using the demo for CI/CD testing

## Support

For issues with the demo:

1. Check the troubleshooting section above
2. Review Vagrant logs: `vagrant up --debug`
3. Check VirtualBox logs in the VirtualBox GUI
4. See main documentation in `../docs/`

## License

Part of the DS-G1-SMS distributed chat system project.
