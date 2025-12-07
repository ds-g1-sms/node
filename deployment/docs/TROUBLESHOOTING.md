# Troubleshooting Guide - Distributed Chat System

This guide helps diagnose and resolve common issues with the distributed chat system.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Deployment Issues](#deployment-issues)
- [Service Issues](#service-issues)
- [Network Issues](#network-issues)
- [Performance Issues](#performance-issues)
- [Data Issues](#data-issues)
- [Common Error Messages](#common-error-messages)
- [Debug Mode](#debug-mode)

## Quick Diagnostics

Run these commands first when troubleshooting:

```bash
# Check stack status
docker stack services chat-system

# Run health checks
cd deployment
./scripts/health-check.sh -v

# View recent logs
./scripts/logs.sh -t 100

# Check node status
docker node ls
```

## Deployment Issues

### Issue: Stack Deploy Fails

**Symptoms:**
- `docker stack deploy` command fails
- Error messages about compose file format
- Services don't start

**Diagnosis:**

```bash
# Validate compose file
docker-compose -f deployment/docker-compose.prod.yml config

# Check Swarm status
docker info | grep Swarm
```

**Solutions:**

1. **Not in Swarm mode**:
```bash
docker swarm init --advertise-addr <IP>
```

2. **Invalid compose file**:
```bash
# Check for syntax errors
docker-compose -f deployment/docker-compose.prod.yml config
```

3. **Missing environment file**:
```bash
# Create from example
cp deployment/.env.example deployment/.env.prod
```

### Issue: Images Not Found

**Symptoms:**
- Error: "image not found"
- Services stuck in "pending" state
- Pull access denied errors

**Diagnosis:**

```bash
# Check if image exists
docker pull yourusername/chat-node:v1.0

# Check registry login
docker info | grep Registry
```

**Solutions:**

1. **Not logged into registry**:
```bash
docker login
```

2. **Wrong image name/tag**:
```bash
# Check .env.prod settings
cat deployment/.env.prod | grep REGISTRY
cat deployment/.env.prod | grep VERSION
```

3. **Build and push image**:
```bash
docker build -f Dockerfile.node -t yourusername/chat-node:v1.0 .
docker push yourusername/chat-node:v1.0
```

### Issue: Node Placement Constraints Not Met

**Symptoms:**
- Services stuck in "pending" state
- Error: "no suitable node"
- Services don't distribute across machines

**Diagnosis:**

```bash
# Check node labels
docker node ls
docker node inspect <NODE-NAME> --format '{{ .Spec.Labels }}'

# Check service constraints
docker service inspect chat-system_node1 --format '{{ .Spec.TaskTemplate.Placement }}'
```

**Solutions:**

1. **Add missing labels**:
```bash
docker node update --label-add node_type=node1 <NODE1-NAME>
docker node update --label-add node_type=node2 <NODE2-NAME>
docker node update --label-add node_type=node3 <NODE3-NAME>
```

2. **Verify labels**:
```bash
for node in $(docker node ls -q); do
  echo "Node: $(docker node inspect $node --format '{{.Description.Hostname}}')"
  docker node inspect $node --format '{{.Spec.Labels}}'
done
```

## Service Issues

### Issue: Service Keeps Restarting

**Symptoms:**
- Service shows "Starting" repeatedly
- Restart count keeps increasing
- Containers exit immediately

**Diagnosis:**

```bash
# Check service tasks
docker service ps chat-system_node1 --no-trunc

# View logs
./scripts/logs.sh -n node1 -t 200

# Check exit code
docker service ps chat-system_node1 --format "{{.Error}}"
```

**Solutions:**

1. **Configuration errors**:
```bash
# Check environment variables
docker service inspect chat-system_node1 --format '{{.Spec.TaskTemplate.ContainerSpec.Env}}'

# Update configuration if needed
docker service update --env-add NODE_ID=node1 chat-system_node1
```

2. **Resource constraints**:
```bash
# Check resource limits
docker service inspect chat-system_node1 | grep -A 10 Resources

# Increase limits if needed
docker service update \
  --limit-memory 1G \
  --reserve-memory 512M \
  chat-system_node1
```

3. **Port conflicts**:
```bash
# Check if ports are already in use
sudo netstat -tlnp | grep 8081
sudo netstat -tlnp | grep 9091

# Stop conflicting services or change ports
```

### Issue: Health Checks Failing

**Symptoms:**
- Container shows "unhealthy" status
- Services restart frequently
- Health check errors in logs

**Diagnosis:**

```bash
# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# View health check logs
docker inspect $(docker ps -q -f name=node1) \
  --format '{{range .State.Health.Log}}{{.Output}}{{end}}'

# Test health check manually
docker exec $(docker ps -q -f name=node1) \
  python -c "import xmlrpc.client; print(xmlrpc.client.ServerProxy('http://localhost:9090').heartbeat())"
```

**Solutions:**

1. **XML-RPC server not ready**:
```bash
# Increase start_period in healthcheck
docker service update \
  --health-start-period 60s \
  chat-system_node1
```

2. **Wrong health check port**:
```bash
# Verify ports match configuration
docker service inspect chat-system_node1 | grep -i port
```

3. **Application error**:
```bash
# Check application logs
./scripts/logs.sh -n node1 -t 100 | grep -i error
```

### Issue: Service Not Accessible

**Symptoms:**
- Cannot connect to service from outside
- Timeout errors
- Connection refused

**Diagnosis:**

```bash
# Check if service is running
docker service ps chat-system_node1

# Check published ports
docker service inspect chat-system_node1 | grep -A 10 PublishedPorts

# Test from inside container
docker exec $(docker ps -q -f name=node1) \
  curl -I http://localhost:8080

# Test from host
curl -I http://localhost:8081
```

**Solutions:**

1. **Firewall blocking**:
```bash
# Check firewall rules
sudo ufw status

# Allow ports
sudo ufw allow 8081/tcp
sudo ufw allow 9091/tcp
```

2. **Wrong port mapping**:
```bash
# Check port configuration in compose file
cat deployment/docker-compose.prod.yml | grep -A 5 "ports:"

# Update if needed
docker service update \
  --publish-rm 8081:8080 \
  --publish-add 8081:8080 \
  chat-system_node1
```

3. **Service not binding to correct interface**:
```bash
# Check bind address in logs
./scripts/logs.sh -n node1 | grep "listening"

# Update environment variable
docker service update \
  --env-add WEBSOCKET_HOST=0.0.0.0 \
  chat-system_node1
```

## Network Issues

### Issue: Nodes Cannot Communicate

**Symptoms:**
- Peer connection errors
- Timeout when contacting other nodes
- "No route to host" errors

**Diagnosis:**

```bash
# Check overlay network
docker network inspect chat-system_chat-overlay

# Test connectivity between nodes
docker exec $(docker ps -q -f name=node1) ping node2
docker exec $(docker ps -q -f name=node1) ping node3

# Check if nodes are on network
docker network inspect chat-system_chat-overlay \
  --format '{{range .Containers}}{{.Name}} {{end}}'
```

**Solutions:**

1. **Overlay network not configured**:
```bash
# Recreate network
docker network rm chat-system_chat-overlay
docker stack deploy -c deployment/docker-compose.prod.yml chat-system
```

2. **Firewall blocking overlay traffic**:
```bash
# Open required ports on all nodes
sudo ufw allow 7946/tcp
sudo ufw allow 7946/udp
sudo ufw allow 4789/udp
```

3. **Wrong peer addresses**:
```bash
# Check peer configuration
docker service inspect chat-system_node1 | grep PEER_NODES

# Update if needed
docker service update \
  --env-add PEER_NODES=node2:http://node2:9090,node3:http://node3:9090 \
  chat-system_node1
```

### Issue: DNS Resolution Failures

**Symptoms:**
- "Name or service not known" errors
- Cannot resolve node hostnames
- Intermittent connectivity issues

**Diagnosis:**

```bash
# Test DNS resolution
docker exec $(docker ps -q -f name=node1) nslookup node2
docker exec $(docker ps -q -f name=node1) nslookup node3

# Check DNS configuration
docker exec $(docker ps -q -f name=node1) cat /etc/resolv.conf
```

**Solutions:**

1. **Use service names instead of container names**:
```bash
# Service names should match compose file
# Use: node1, node2, node3
# Not: chat-node1, chat_system_node1, etc.
```

2. **Update DNS settings**:
```bash
# Configure Docker daemon DNS
sudo nano /etc/docker/daemon.json
# Add: "dns": ["8.8.8.8", "8.8.4.4"]

sudo systemctl restart docker
```

## Performance Issues

### Issue: High CPU Usage

**Symptoms:**
- CPU usage consistently over 80%
- Slow response times
- Services becoming unresponsive

**Diagnosis:**

```bash
# Check resource usage
docker stats --no-stream

# Check specific service
docker stats $(docker ps -q -f name=node1) --no-stream

# View CPU-intensive processes
docker exec $(docker ps -q -f name=node1) top -b -n 1
```

**Solutions:**

1. **Increase CPU limits**:
```bash
docker service update \
  --limit-cpu 2.0 \
  --reserve-cpu 0.5 \
  chat-system_node1
```

2. **Optimize application**:
```bash
# Check for inefficient loops or operations in logs
./scripts/logs.sh -n node1 -f | grep -i "processing"
```

### Issue: High Memory Usage

**Symptoms:**
- Memory usage approaching limits
- OOMKilled errors
- Services restarting due to memory

**Diagnosis:**

```bash
# Check memory usage
docker stats --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check for memory leaks
docker exec $(docker ps -q -f name=node1) \
  python -c "import psutil; print(psutil.virtual_memory())"

# View OOM events
docker service ps chat-system_node1 | grep -i oom
```

**Solutions:**

1. **Increase memory limits**:
```bash
docker service update \
  --limit-memory 1G \
  --reserve-memory 512M \
  chat-system_node1
```

2. **Investigate memory leaks**:
```bash
# Enable debug logging
docker service update \
  --env-add LOG_LEVEL=DEBUG \
  chat-system_node1

# Monitor memory over time
watch -n 5 'docker stats --no-stream | grep node1'
```

## Data Issues

### Issue: Lost Room Data

**Symptoms:**
- Rooms disappear after restart
- User data not persisting
- Inconsistent state across nodes

**Diagnosis:**

```bash
# Check volumes
docker volume ls | grep chat-system

# Inspect volume
docker volume inspect chat-system_node1-logs

# Check if volume is mounted
docker service inspect chat-system_node1 | grep -A 10 Mounts
```

**Solutions:**

1. **This system uses in-memory storage** - data loss on restart is expected
2. **For persistent data**, need to implement database backend
3. **Current workaround**: Keep services running, use health checks for automatic recovery

### Issue: Stale Member Cleanup Not Working

**Symptoms:**
- Disconnected users still show as active
- Members not removed after timeout
- Cleanup task not running

**Diagnosis:**

```bash
# Check cleanup logs
./scripts/logs.sh -n node1 | grep -i "cleanup"

# Check cleanup interval
docker service inspect chat-system_node1 | grep -i cleanup
```

**Solutions:**

1. **Verify cleanup task is running**:
```bash
./scripts/logs.sh -n node1 | grep "Starting stale member cleanup"
```

2. **Adjust cleanup interval**:
```bash
docker service update \
  --env-add CLEANUP_INTERVAL=30 \
  chat-system_node1
```

## Common Error Messages

### "No such file or directory: /var/log/chatnode"

**Cause**: Log directory not created in container

**Solution**: Already fixed in updated Dockerfile with proper directory creation

### "Permission denied" when writing logs

**Cause**: Non-root user doesn't have write permissions

**Solution**: Dockerfile creates directories with correct permissions

### "Connection refused" to XML-RPC port

**Cause**: XML-RPC server not started or wrong port

**Solution**:
```bash
# Check if server is listening
docker exec $(docker ps -q -f name=node1) netstat -tlnp | grep 9090

# Check logs for startup errors
./scripts/logs.sh -n node1 | grep -i "xml-rpc"
```

### "Overlay network subnet exhausted"

**Cause**: Too many containers on overlay network

**Solution**:
```bash
# Use larger subnet
# Edit docker-compose.prod.yml:
# subnet: 10.10.0.0/16  # Supports ~65k hosts
```

## Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Enable debug logging
docker service update \
  --env-add LOG_LEVEL=DEBUG \
  chat-system_node1

# Follow logs
./scripts/logs.sh -n node1 -f

# Disable after debugging
docker service update \
  --env-rm LOG_LEVEL \
  chat-system_node1
```

## Getting Help

If issues persist:

1. **Collect diagnostics**:
```bash
# Save logs
./scripts/logs.sh -a > /tmp/debug-logs-$(date +%Y%m%d).log

# Save service info
docker service inspect chat-system_node1 > /tmp/service-inspect.json
```

2. **Create issue report** with:
   - Error messages
   - Log excerpts
   - Service configuration
   - Steps to reproduce

3. **Contact support**: DS-G1-SMS team

## Additional Resources

- [Deployment Guide](DEPLOYMENT.md)
- [Operations Manual](OPERATIONS.md)
- [Docker Swarm Troubleshooting](https://docs.docker.com/engine/swarm/swarm-tutorial/#troubleshooting)
