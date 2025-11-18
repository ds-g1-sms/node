# Protocol Buffers Definitions

This directory contains Protocol Buffer (.proto) definitions for gRPC services.

## Purpose

Defines the interface for:
- Server-to-server communication (inter-node gRPC)
- Message types and structures
- Service definitions for room management, message forwarding, and coordination

## Generating Python Code

After defining .proto files, generate Python code with:

```bash
python -m grpc_tools.protoc -I. \
    --python_out=. \
    --grpc_python_out=. \
    proto/*.proto
```
