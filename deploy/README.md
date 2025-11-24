# Deployment Configurations

This directory contains deployment configurations and scripts.

## Purpose

Configuration files for:
- Docker containerization
- Kubernetes manifests
- Environment configurations
- Deployment scripts

## Development Environment

For prototype testing, you can run 3-5 nodes locally on localhost.

### Using Docker Compose (Recommended)

The project includes a `docker-compose.yml` file at the root that sets up a complete development environment with:
- 3 chat node servers (node1, node2, node3)
- 1 chat client

#### Quick Start Linux

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

#### Quick Start Windows

```bash
# Build Docker images
docker compose build

# Start all containers
docker compose up -d

# View logs
docker compose logs -f

# Stop all containers
docker compose down

# Clean up everything (containers, volumes, images)
docker compose down --rmi all --volumes
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

### Local Development Without Docker Windows

```bash
# Install dependencies
npm install

# Run node server
npm run dev:node

# In another terminal, run client
npm run dev:client```
