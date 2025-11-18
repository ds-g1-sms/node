# Node Server

This directory contains the main entry point for the distributed chat node server.

## Purpose

Each node in the distributed system runs this server application, which:
- Hosts chat rooms
- Handles client connections via WebSocket
- Communicates with peer nodes via gRPC
- Manages room state and message ordering
- Acts as administrator for rooms it creates

## Running

```bash
go run main.go
```
