# Deployment - Distributed Chat System

This directory contains all deployment configurations, scripts, and
documentation for the distributed chat system.

## 🚀 Try the Demo First!

**New to the system?** Try our automated VM demo that sets up 3 virtual machines
with full Swarm orchestration:

```bash
cd demo
vagrant up
./scripts/deploy-demo.sh
```

See [demo/QUICKSTART.md](demo/QUICKSTART.md) for a 15-minute walkthrough, or
[demo/README.md](demo/README.md) for full documentation.

______________________________________________________________________

## Quick Start

### Production Deployment (Multi-Host)

1. **Prepare three machines** with Docker and join them to a Docker Swarm
2. **Label the nodes**:
   ```bash
   docker node update --label-add node_type=node1 <NODE1-NAME>
   docker node update --label-add node_type=node2 <NODE2-NAME>
   docker node update --label-add node_type=node3 <NODE3-NAME>
   ```
3. **Configure environment**:
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with your settings
   ```
4. **Deploy**:
   ```bash
   ./scripts/deploy.sh -e .env.prod -b -v
   ```

### Development Deployment (Single Machine)

For local testing on a single machine:

```bash
# Using the development override
docker compose -f docker-compose.prod.yml -f docker-compose.dev.yml up -d

# Or use the root docker-compose.yml (simplified version)
cd ..
docker compose up -d
```

## Directory Structure

```
deployment/
├── README.md                       # This file
├── docker-compose.prod.yml         # Production Swarm configuration
├── docker-compose.dev.yml          # Development overrides
├── .env.example                    # Environment variables template
├── demo/                           # 🆕 Multi-VM demo environment
│   ├── Vagrantfile                 # VM provisioning
│   ├── QUICKSTART.md               # 15-min getting started
│   ├── README.md                   # Full demo documentation
│   └── scripts/                    # Demo deployment scripts
├── configs/                        # Node-specific configurations
│   ├── node1.env
│   ├── node2.env
│   └── node3.env
├── scripts/                        # Operational scripts
│   ├── deploy.sh                   # Automated deployment
│   ├── health-check.sh             # Health verification
│   └── logs.sh                     # Log aggregation
└── docs/                           # Documentation
    ├── DEPLOYMENT.md               # Deployment guide
    ├── OPERATIONS.md               # Operations manual
    └── TROUBLESHOOTING.md          # Troubleshooting guide
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Complete deployment guide

  - Prerequisites and requirements
  - Machine setup instructions
  - Docker Swarm configuration
  - Step-by-step deployment
  - Verification procedures

- **[OPERATIONS.md](docs/OPERATIONS.md)** - Day-to-day operations

  - Monitoring and health checks
  - Log management
  - Service management
  - Scaling operations
  - Updates and rollbacks
  - Backup and recovery

- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Problem resolution

  - Common issues and solutions
  - Diagnostic procedures
  - Error message reference
  - Debug mode

## Key Features

### Multi-Host Deployment

- Docker Swarm orchestration
- Three nodes on separate machines
- Overlay network for inter-node communication
- Placement constraints ensure node distribution

### High Availability

- Health checks with automatic restart
- Rolling updates with zero downtime
- Graceful shutdown handling
- Fault tolerance and recovery

### Resource Management

- CPU and memory limits
- Resource reservations
- Configurable constraints per service

### Monitoring and Observability

- Health check endpoints
- Service logs aggregation
- Resource monitoring
- Operational metrics

### Security

- Non-root container users
- Minimal base images
- Secret management support
- Network segmentation

## Quick Commands

```bash
# Deploy stack
./scripts/deploy.sh -e .env.prod

# Check health
./scripts/health-check.sh -v

# View logs
./scripts/logs.sh -f

# Manual operations
docker stack services chat-system
docker stack ps chat-system
docker service logs -f chat-system_node1
```

## Environment Variables

Key environment variables (see `.env.example` for complete list):

| Variable        | Description              | Default             |
| --------------- | ------------------------ | ------------------- |
| `REGISTRY`      | Container registry URL   | `ghcr.io/ds-g1-sms` |
| `VERSION`       | Image version/tag        | `latest`            |
| `NODE1_WS_PORT` | Node 1 WebSocket port    | `8080`              |
| `NODE2_WS_PORT` | Node 2 WebSocket port    | `8080`              |
| `NODE3_WS_PORT` | Node 3 WebSocket port    | `8080`              |
| `LOG_LEVEL`     | Logging level            | `INFO`              |
| `CPU_LIMIT`     | CPU limit per service    | `1.0`               |
| `MEMORY_LIMIT`  | Memory limit per service | `512M`              |

## Port Mapping

Since each node runs on a separate machine with a unique IP address, all nodes
use the same ports:

| Node   | WebSocket (Client) | XML-RPC (Inter-node) |
| ------ | ------------------ | -------------------- |
| Node 1 | 8080               | 9090                 |
| Node 2 | 8080               | 9090                 |
| Node 3 | 8080               | 9090                 |

## Network Architecture

```
┌─────────────────────────────────────────────┐
│         Docker Swarm Cluster                │
├───────────────┬────────────┬────────────────┤
│  Machine 1    │ Machine 2  │  Machine 3     │
│  ┌─────────┐  │ ┌────────┐ │  ┌─────────┐   │
│  │ Node 1  │  │ │ Node 2 │ │  │ Node 3  │   │
│  │ :8080   │  │ │ :8080  │ │  │ :8080   │   │
│  │ :9090   │  │ │ :9090  │ │  │ :9090   │   │
│  └─────────┘  │ └────────┘ │  └─────────┘   │
└───────────────┴────────────┴────────────────┘
           │         │         │
           └─────────┴─────────┘
           Overlay Network (10.10.0.0/16)
```

## Prerequisites

### Hardware

- 3 machines (physical or virtual)
- 2+ CPU cores per machine
- 4+ GB RAM per machine
- 20+ GB disk per machine

### Software

- Docker Engine 20.10+
- Docker Compose 1.29+ (for local dev)
- Linux OS (Ubuntu 20.04+ or CentOS 8+)

### Network

- Open ports: 2377, 7946, 4789 (Swarm)
- Open ports: 8080, 9090 (Application - same on each machine)
- Network connectivity between all machines

## Support and Troubleshooting

1. **Check health**: `./scripts/health-check.sh -v`
2. **View logs**: `./scripts/logs.sh -f`
3. **Read docs**: Start with [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
4. **Contact**: DS-G1-SMS team

## License

Part of the DS-G1-SMS distributed chat system project.
