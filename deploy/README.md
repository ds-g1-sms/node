# Deployment Configurations

⚠️ **Note**: This directory contains legacy information. For production deployment, see the `../deployment/` directory.

## Production Deployment

For production multi-host deployment using Docker Swarm, see:

**📁 [../deployment/](../deployment/)** - Complete production deployment infrastructure with:
- Docker Swarm orchestration
- Multi-host deployment configuration
- Automated deployment scripts
- Comprehensive documentation
- Health checks and monitoring
- Operations manual

Quick Start for Production:
```bash
cd deployment
./scripts/deploy.sh -e .env.prod -v
```

See [deployment/docs/DEPLOYMENT.md](../deployment/docs/DEPLOYMENT.md) for complete instructions.

---

## Development Environment (Legacy)

## Development Environment

For prototype testing, you can run 3-5 nodes locally on localhost.

### Using Docker Compose (Recommended)

The project includes a `docker-compose.yml` file at the root that sets up a complete development environment with:
- 3 chat node servers (node1, node2, node3)
- 1 chat client

#### Quick Start

```bash
# Build Docker images
make docker-build

# Start all containers
make docker-up

# View logs
docker compose logs -f

# Stop all containers
make docker-down

# Clean up everything (containers, volumes, images)
make docker-clean
```

#### Port Mapping

- Node 1: WebSocket on 8081, gRPC on 9091
- Node 2: WebSocket on 8082, gRPC on 9092
- Node 3: WebSocket on 8083, gRPC on 9093

### Local Development Without Docker

```bash
# Install dependencies
make deps

# Run node server
make dev-node

# In another terminal, run client
make dev-client
```
