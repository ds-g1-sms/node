# Distributed Chat System - Node

A distributed peer-to-peer chat system built with Go, gRPC, and WebSockets.

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

- Go 1.21 or later
- Protocol Buffers compiler (protoc)
- Make (optional)

### Building

```bash
# Build node server
go build -o bin/node ./cmd/node

# Build client
go build -o bin/client ./cmd/client
```

### Running

```bash
# Start a node server
./bin/node

# Start a client
./bin/client
```

## Development

### Code Generation

Generate Go code from Protocol Buffer definitions:

```bash
protoc --go_out=. --go_opt=paths=source_relative \
    --go-grpc_out=. --go-grpc_opt=paths=source_relative \
    proto/*.proto
```

### Testing

```bash
go test ./...
```

## Technology Stack

- **Language**: Go
- **Server-to-Server**: gRPC with Protocol Buffers
- **Client-to-Server**: WebSockets
- **State Management**: In-memory (with optional CockroachDB for persistence)
- **Coordination**: Custom two-phase commit implementation

## Contributing

This is a course project for distributed systems. See architecture documentation for design decisions and trade-offs.

## License

[Specify license here]
