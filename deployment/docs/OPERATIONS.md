# Operations Manual - Distributed Chat System

This manual provides guidance for day-to-day operations of the distributed chat system.

## Table of Contents

- [Overview](#overview)
- [Monitoring](#monitoring)
- [Log Management](#log-management)
- [Service Management](#service-management)
- [Scaling Operations](#scaling-operations)
- [Updates and Rollbacks](#updates-and-rollbacks)
- [Backup and Recovery](#backup-and-recovery)
- [Security Operations](#security-operations)
- [Incident Response](#incident-response)
- [Maintenance Windows](#maintenance-windows)

## Overview

The distributed chat system consists of three independent node services orchestrated by Docker Swarm. This manual covers common operational tasks and procedures.

### Key Operational Principles

1. **High Availability**: At least 2 nodes should be running at all times
2. **Zero Downtime**: Use rolling updates for deployments
3. **Monitoring First**: Always check metrics before making changes
4. **Log Everything**: Comprehensive logging for troubleshooting
5. **Test First**: Test changes in development before production

## Monitoring

### Service Health Checks

#### Automated Health Checks

Run the health check script regularly:

```bash
cd deployment
./scripts/health-check.sh -s chat-system -v
```

#### Manual Health Checks

Check individual service status:

```bash
# List all services
docker stack services chat-system

# Check specific service
docker service ps chat-system_node1

# View service details
docker service inspect chat-system_node1 --pretty
```

#### Health Check Metrics

Monitor these key metrics:

- **Service Status**: All replicas should be running (1/1)
- **Health Status**: All containers should be "healthy"
- **Uptime**: Services should have consistent uptime
- **Restart Count**: Low restart counts indicate stability

### Resource Monitoring

#### CPU and Memory Usage

```bash
# Check node resource usage
docker node ls

# Check container stats
docker stats --no-stream

# Detailed service stats
docker service ps chat-system_node1 --no-trunc
```

#### Network Monitoring

```bash
# Check overlay network
docker network inspect chat-system_chat-overlay

# Monitor network traffic (from host)
sudo iftop -i eth0
```

### Application Metrics

#### Message Throughput

Monitor via application logs:

```bash
./scripts/logs.sh -n node1 -t 100 | grep "message"
```

#### Active Connections

Check WebSocket connections:

```bash
# View active connections in logs
./scripts/logs.sh -f | grep -i "connected"
```

## Log Management

### Viewing Logs

#### All Nodes

```bash
# View logs from all nodes
./scripts/logs.sh

# Follow logs in real-time
./scripts/logs.sh -f

# View last 500 lines
./scripts/logs.sh -t 500
```

#### Specific Node

```bash
# View logs from node1
./scripts/logs.sh -n node1

# Follow node2 logs
./scripts/logs.sh -n node2 -f

# View all logs from node3
./scripts/logs.sh -n node3 -a
```

#### Direct Docker Commands

```bash
# Service logs
docker service logs -f chat-system_node1

# Container logs
docker logs $(docker ps -q -f name=node1)

# Last 100 lines with timestamps
docker service logs --tail 100 --timestamps chat-system_node1
```

### Log Rotation

Docker handles log rotation automatically, but you can configure:

```bash
# Configure log rotation in daemon.json
sudo nano /etc/docker/daemon.json

# Add:
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

# Restart Docker
sudo systemctl restart docker
```

### Log Analysis

#### Search for Errors

```bash
# Find errors in logs
./scripts/logs.sh -a | grep -i "error"

# Find warnings
./scripts/logs.sh -a | grep -i "warning"

# Search for specific pattern
./scripts/logs.sh -f | grep "room_id"
```

#### Export Logs

```bash
# Export logs to file
./scripts/logs.sh -a > /tmp/chat-system-logs-$(date +%Y%m%d).log

# Export specific node logs
./scripts/logs.sh -n node1 -a > /tmp/node1-logs-$(date +%Y%m%d).log
```

## Service Management

### Starting Services

Services start automatically on deployment, but you can control them:

```bash
# Deploy/start stack
docker stack deploy -c deployment/docker-compose.prod.yml chat-system

# Or use the deployment script
./deployment/scripts/deploy.sh -e deployment/.env.prod
```

### Stopping Services

```bash
# Stop specific service
docker service scale chat-system_node1=0

# Stop all services (remove stack)
docker stack rm chat-system
```

### Restarting Services

```bash
# Force update (restarts service)
docker service update --force chat-system_node1

# Restart all services
docker service update --force chat-system_node1
docker service update --force chat-system_node2
docker service update --force chat-system_node3
```

### Service Inspection

```bash
# View service configuration
docker service inspect chat-system_node1 --pretty

# View service tasks
docker service ps chat-system_node1

# View service logs
docker service logs chat-system_node1
```

## Scaling Operations

### Scale Up

Add more replicas to handle increased load:

```bash
# Scale node1 to 2 replicas
./scripts/scale.sh -n node1 -r 2 -v

# Or using docker command
docker service scale chat-system_node1=2
```

**Note**: Ensure you have machines with appropriate labels for additional replicas.

### Scale Down

Reduce replicas to save resources:

```bash
# Scale back to 1 replica
./scripts/scale.sh -n node1 -r 1 -v

# Or using docker command
docker service scale chat-system_node1=1
```

### Scaling Best Practices

1. **Monitor Load**: Scale based on actual metrics, not assumptions
2. **Gradual Scaling**: Scale one node at a time
3. **Verify Health**: Use `-v` flag to verify scaling completes successfully
4. **Consider Dependencies**: Ensure peer nodes are informed of changes

## Updates and Rollbacks

### Rolling Updates

Update services with zero downtime:

```bash
# Update to new version
docker service update \
  --image yourusername/chat-node:v1.1 \
  --update-parallelism 1 \
  --update-delay 30s \
  chat-system_node1

# Update all services
for node in node1 node2 node3; do
  docker service update \
    --image yourusername/chat-node:v1.1 \
    chat-system_$node
  sleep 30
done
```

### Update Configuration

Update environment variables or settings:

```bash
# Update environment variable
docker service update \
  --env-add LOG_LEVEL=DEBUG \
  chat-system_node1

# Update multiple settings
docker service update \
  --env-add LOG_LEVEL=DEBUG \
  --env-add HEARTBEAT_INTERVAL=60 \
  chat-system_node1
```

### Rollback

If an update fails, rollback to previous version:

```bash
# Automatic rollback (configured in compose file)
# Happens automatically on update failure

# Manual rollback
docker service rollback chat-system_node1

# Rollback to specific version
docker service update \
  --image yourusername/chat-node:v1.0 \
  --rollback \
  chat-system_node1
```

### Update Verification

After updates, verify system health:

```bash
# Run health checks
./scripts/health-check.sh -v

# Check service status
docker stack services chat-system

# View recent logs
./scripts/logs.sh -t 50
```

## Backup and Recovery

### Configuration Backup

Backup deployment configuration:

```bash
# Create backup directory
mkdir -p /backup/chat-system/$(date +%Y%m%d)

# Backup configuration files
cp deployment/.env.prod /backup/chat-system/$(date +%Y%m%d)/
cp -r deployment/configs /backup/chat-system/$(date +%Y%m%d)/
cp deployment/docker-compose.prod.yml /backup/chat-system/$(date +%Y%m%d)/

# Create archive
tar -czf /backup/chat-system-$(date +%Y%m%d).tar.gz \
  -C /backup/chat-system/$(date +%Y%m%d) .
```

### Volume Backup

Backup persistent data:

```bash
# List volumes
docker volume ls | grep chat-system

# Backup volume
docker run --rm \
  -v chat-system_node1-logs:/data \
  -v /backup:/backup \
  alpine tar -czf /backup/node1-logs-$(date +%Y%m%d).tar.gz -C /data .
```

### Recovery

Restore from backup:

```bash
# Extract configuration
tar -xzf /backup/chat-system-20240101.tar.gz -C /tmp/restore/

# Copy files back
cp /tmp/restore/.env.prod deployment/
cp /tmp/restore/docker-compose.prod.yml deployment/

# Redeploy
./deployment/scripts/deploy.sh -e deployment/.env.prod
```

## Security Operations

### Access Control

Manage access to Docker Swarm:

```bash
# View current managers and workers
docker node ls

# Promote worker to manager
docker node promote <NODE-NAME>

# Demote manager to worker
docker node demote <NODE-NAME>
```

### Secret Management

Use Docker secrets for sensitive data:

```bash
# Create secret
echo "secret-value" | docker secret create my_secret -

# Update service to use secret
docker service update \
  --secret-add my_secret \
  chat-system_node1

# List secrets
docker secret ls

# Remove secret
docker secret rm my_secret
```

### Security Scanning

Scan images for vulnerabilities:

```bash
# Scan image
docker scan yourusername/chat-node:v1.0

# Scan with specific severity
docker scan --severity high yourusername/chat-node:v1.0
```

### Network Security

Review and update network policies:

```bash
# Inspect network
docker network inspect chat-system_chat-overlay

# View connected services
docker network inspect chat-system_chat-overlay \
  --format '{{range .Containers}}{{.Name}} {{end}}'
```

## Incident Response

### Service Down

1. **Check service status**:
```bash
docker service ps chat-system_node1
```

2. **View logs for errors**:
```bash
./scripts/logs.sh -n node1 -t 100
```

3. **Check node health**:
```bash
docker node ls
docker node inspect <NODE-NAME>
```

4. **Restart service if needed**:
```bash
docker service update --force chat-system_node1
```

### High Resource Usage

1. **Check resource consumption**:
```bash
docker stats --no-stream
```

2. **Identify problematic container**:
```bash
docker stats $(docker ps -q -f name=node)
```

3. **Review recent logs**:
```bash
./scripts/logs.sh -n node1 -t 200
```

4. **Scale if needed**:
```bash
./scripts/scale.sh -n node1 -r 2 -v
```

### Network Issues

1. **Test connectivity**:
```bash
# Between nodes
docker exec $(docker ps -q -f name=node1) ping node2

# To external
docker exec $(docker ps -q -f name=node1) ping 8.8.8.8
```

2. **Check overlay network**:
```bash
docker network inspect chat-system_chat-overlay
```

3. **Restart network if needed**:
```bash
# Restart affected services
docker service update --force chat-system_node1
```

## Maintenance Windows

### Planned Maintenance

Schedule maintenance during low-traffic periods:

1. **Notify users** of upcoming maintenance

2. **Verify backups** are current:
```bash
# Run backup
./scripts/backup.sh  # if created
```

3. **Perform maintenance** (e.g., updates):
```bash
# Update services one at a time
./scripts/deploy.sh -e deployment/.env.prod -b
```

4. **Verify system** post-maintenance:
```bash
./scripts/health-check.sh -v
```

5. **Monitor closely** for 30 minutes after maintenance

### Emergency Maintenance

For urgent issues:

1. **Assess severity** - Does it require immediate action?

2. **Isolate issue** - Identify affected services

3. **Take corrective action**:
```bash
# Quick fixes
docker service update --force chat-system_node1

# Or rollback
docker service rollback chat-system_node1
```

4. **Document incident** for post-mortem review

## Common Tasks Quick Reference

```bash
# View service status
docker stack services chat-system

# View logs
./scripts/logs.sh -f

# Health check
./scripts/health-check.sh -v

# Restart service
docker service update --force chat-system_node1

# Scale service
./scripts/scale.sh -n node1 -r 2

# Update image
docker service update --image user/chat-node:v2 chat-system_node1

# Rollback
docker service rollback chat-system_node1

# Remove stack
docker stack rm chat-system
```

## Best Practices

1. **Regular Health Checks**: Run automated health checks at least hourly
2. **Log Monitoring**: Review logs daily for errors and warnings
3. **Backup Schedule**: Backup configuration weekly, volumes daily
4. **Update Strategy**: Test updates in staging before production
5. **Documentation**: Document all changes and incidents
6. **Monitoring**: Set up alerts for critical metrics
7. **Security**: Regular security audits and updates

## Additional Resources

- [Deployment Guide](DEPLOYMENT.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [Docker Swarm Documentation](https://docs.docker.com/engine/swarm/)

## Support

For assistance:
- Review logs: `./scripts/logs.sh -f`
- Run health checks: `./scripts/health-check.sh -v`
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Contact: DS-G1-SMS team
