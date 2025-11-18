# Protocol Buffers Definitions

This directory contains Protocol Buffer (.proto) definitions for gRPC services.

## Purpose

Defines the interface for:
- Server-to-server communication (inter-node gRPC)
- Message types and structures
- Service definitions for room management, message forwarding, and coordination

## Generating Go Code

After defining .proto files, generate Go code with:

```bash
protoc --go_out=. --go_opt=paths=source_relative \
    --go-grpc_out=. --go-grpc_opt=paths=source_relative \
    proto/*.proto
```
