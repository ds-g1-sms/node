# Client Service Module

This module provides the client-side functionality for the distributed chat system.

## Overview

The client service enables applications to connect to node servers via WebSocket and perform operations such as creating rooms, joining rooms, and sending messages.

## Components

### 1. ClientService (`service.py`)

The main service class that handles all client-server interactions.

**Key Features:**
- WebSocket connection management
- Asynchronous communication
- Dependency injection support for testing
- Message handler registration

**Entry Points:**
- `connect()` - Establish connection to a node
- `disconnect()` - Close connection
- `create_room(room_name, creator_id)` - Create a new chat room
- `handle_messages()` - Listen for incoming messages (future)

**Current Status:** 
- Connection management: ✅ Implemented
- Room creation: ⚠️ Stub implementation (returns mock responses)
- Message handling: 🚧 Scaffolded for future work

### 2. Protocol Messages (`protocol.py`)

Message classes for client-server communication.

**Implemented Messages:**
- `CreateRoomRequest` - Request to create a room
- `RoomCreatedResponse` - Response after room creation

**Message Format:**
All messages use JSON with the following structure:
```json
{
  "type": "message_type",
  "data": { ... message-specific fields ... }
}
```

**Future Messages (TODO):**
- `JoinRoomRequest` / `JoinRoomResponse`
- `SendMessageRequest`
- `MessageReceivedNotification`
- `LeaveRoomRequest`
- `RoomListRequest` / `RoomListResponse`

## Usage

### Basic Example

```python
from src.client import ClientService
import asyncio

async def main():
    # Initialize service
    service = ClientService(node_url="ws://localhost:8000")
    
    # Connect to node
    await service.connect()
    
    # Create a room
    response = await service.create_room(
        room_name="general",
        creator_id="user123"
    )
    
    print(f"Room created: {response.room_id}")
    
    # Disconnect
    await service.disconnect()

asyncio.run(main())
```

### Demo Script

Run the demo script to see the client service in action:

```bash
# Single room creation demo
poetry run python -m src.client.demo

# Multiple rooms demo
poetry run python -m src.client.demo --demo multiple

# Custom node URL
poetry run python -m src.client.demo --node-url ws://node1.example.com:8000
```

## Testing

Tests are located in `tests/test_client_service.py`.

Run tests:
```bash
poetry run pytest tests/test_client_service.py -v
```

**Current Test Coverage:**
- ✅ Service initialization
- ✅ Protocol message creation and serialization
- ✅ Stub create_room functionality

**Future Tests (TODO):**
- Integration tests with real WebSocket server
- Error handling scenarios
- Message handler registration
- Concurrent operations

## Architecture Notes

### Dependency Injection

The `ClientService` supports dependency injection for the WebSocket connection factory, making it testable:

```python
# Custom WebSocket factory for testing
async def mock_websocket_factory(url):
    return MockWebSocket()

service = ClientService(
    node_url="ws://localhost:8000",
    websocket_factory=mock_websocket_factory
)
```

### Async/Await Pattern

All I/O operations use async/await for non-blocking execution:
- Better performance with concurrent operations
- Natural fit for WebSocket communication
- Compatible with modern Python async frameworks

## Integration Points

### With Node Server

The client service expects the node server to:
1. Accept WebSocket connections
2. Handle JSON-formatted messages
3. Respond with appropriate message types
4. Maintain connection health (heartbeat/ping-pong)

**Protocol Contract:**
- Client sends `CreateRoomRequest` with `type: "create_room"`
- Server responds with `RoomCreatedResponse` containing room details
- All messages follow the standard JSON message format

### Future Integration

**Planned Features:**
- Connection pooling for multiple nodes
- Automatic reconnection on failure
- Message queueing and retry logic
- Room state caching
- Multi-node room discovery

## Development Status

### ✅ Completed
- [x] Client service module structure
- [x] WebSocket foundation (connection/disconnection)
- [x] Protocol message classes
- [x] Stub create_room method
- [x] Demo script
- [x] Basic test coverage
- [x] Documentation

### 🚧 TODO
- [ ] Implement full create_room request/response cycle
- [ ] Add join_room functionality
- [ ] Add send_message functionality
- [ ] Add message receiving and dispatching
- [ ] Implement message handler routing
- [ ] Add connection retry logic
- [ ] Add timeout handling
- [ ] Add validation for inputs
- [ ] Implement heartbeat/ping-pong
- [ ] Add integration tests with real server
- [ ] Add error handling for all edge cases

## Contributing

When implementing new features:

1. **Add protocol messages** in `protocol.py` first
2. **Implement service methods** in `service.py`
3. **Write tests** in `tests/test_client_service.py`
4. **Update this README** with new features
5. **Add demo examples** if applicable

## Related Documentation

- [Architecture Overview](../../docs/architecture.md)
- [Parent Issue #12](https://github.com/ds-g1-sms/node/issues/12) - Client room creation
- Node server documentation (TODO)
