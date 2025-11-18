# Internal Packages

This directory contains private application and library code.

## Structure

- **room/**: Room management logic (creation, deletion, membership)
- **state/**: In-memory state management for rooms, users, messages
- **coordination/**: Two-phase commit protocol for coordinated operations
- **handler/**: Request handlers for client WebSocket and inter-node gRPC

## Note

Code in `internal/` is only importable by this module and cannot be imported by external projects.
