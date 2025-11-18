# Distributed Chat System - Node

A distributed peer-to-peer chat system built with Python, gRPC, and WebSockets.

## Overview

This repository contains the implementation of a distributed chat node that participates in a peer-to-peer messaging network. Each node can host chat rooms, handle client connections, and communicate with other nodes to provide a distributed chat service.

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

### Key Features

- **Distributed Architecture**: All nodes are equal peers
- **Room Hosting**: Each node can host multiple chat rooms
- **Administrator-Based Ordering**: Room creator acts as authority for message ordering
- **gRPC Communication**: Efficient server-to-server communication using Protocol Buffers
- **WebSocket Clients**: Real-time bidirectional client-server messaging
- **Fault Tolerance**: Basic health checks and failure detection

## Project Structure

```
.
├── cmd/
│   ├── node/           # Node server main entry point
│   └── client/         # Chat client application
├── internal/           # Private application code
│   ├── room/           # Room management
│   ├── state/          # State management
│   ├── coordination/   # Two-phase commit coordination
│   └── handler/        # Request handlers
├── pkg/                # Public library code
│   ├── protocol/       # Protocol utilities
│   └── discovery/      # Node discovery
├── proto/              # Protocol Buffer definitions
├── deploy/             # Deployment configurations
├── scripts/            # Utility scripts
├── .github/workflows/  # CI/CD workflows
└── docs/               # Documentation
```

## Getting Started

### Prerequisites

- Python 3.8 or later
- Poetry - Python package manager
- Protocol Buffers compiler (protoc) - for code generation
- Make - for using Makefile targets
- Docker & Docker Compose - for containerized deployment (optional)

### Quick Start with Make

```bash
# View all available targets
make help

# Install dependencies
make deps

# Run node server in development mode
make dev-node

# Run client in development mode (in another terminal)
make dev-client
```

### Installing

```bash
# Using Make (recommended)
make install

# Or using Poetry directly
poetry install
```

### Running

```bash
# Start a node server
poetry run python -m src.node.main

# Start a client
poetry run python -m src.client.main
```

## Development

### Dependency Management

```bash
# Install dependencies
make deps

# Update dependencies to latest versions
make deps-update
```

### Code Generation

Generate Python code from Protocol Buffer definitions:

```bash
# Using Make
make proto

# Or using Poetry and protoc directly
poetry run python -m grpc_tools.protoc -I. \
    --python_out=. \
    --grpc_python_out=. \
    proto/*.proto
```

### Testing

```bash
# Using Make
make test

# Or using Poetry directly
poetry run pytest -v
```

### Linting

```bash
make lint
```

### Docker Development

```bash
# Build Docker images
make docker-build

# Start all containers (3 nodes + 1 client)
make docker-up

# View logs
docker compose logs -f

# Stop containers
make docker-down

# Clean up (remove containers, volumes, and images)
make docker-clean
```

**Note**: Docker builds use a `requirements.txt` file generated from `pyproject.toml`. If you update dependencies in `pyproject.toml`, update `requirements.txt` accordingly for Docker builds.

For more details on Docker deployment, see [deploy/README.md](deploy/README.md).

## Technology Stack

- **Language**: Python
- **Server-to-Server**: gRPC with Protocol Buffers
- **Client-to-Server**: WebSockets
- **State Management**: In-memory (with optional CockroachDB for persistence)
- **Coordination**: Custom two-phase commit implementation

## Contributing

This is a course project for distributed systems. See architecture documentation for design decisions and trade-offs.

## License

[Specify license here]
