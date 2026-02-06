# Client Service Module

This module provides the client-side functionality for the distributed chat
system, including the terminal user interface.

## Overview

The client service enables applications to connect to node servers via WebSocket
and perform operations such as creating rooms, joining rooms, and sending
messages. It includes a terminal-based user interface built with the Textual
framework.

## Quick Start

### Running the Chat Client

```bash
# Using Poetry
poetry run chat-client

# Or directly
poetry run python -m src.client.main
```

This launches the terminal-based chat interface where you can:

1. Enter your username and node address
2. Connect to a node
3. Discover and browse available rooms
4. Create new rooms or join existing ones
5. Send and receive messages in real-time
6. See other members in the room

### Keyboard Shortcuts

- `q` - Quit the application
- `Escape` - Go back / Cancel
- `r` - Refresh room list (when in room list view)
- `Enter` - Submit forms / Send messages

## Components

### 1. User Interface (`ui/`)

Terminal-based UI built with the Textual framework.

**Main Components:**

- `ChatApp` - Main application class
- `ConnectionScreen` - Connect to a node
- `RoomListScreen` - View and manage rooms
- `CreateRoomDialog` - Create new rooms
- `ChatScreen` - Chat interface with message display

**Features:**

- Connection management with status feedback
- Room discovery (local and global)
- Room creation with name and description
- Real-time message display with sender info
- Member list sidebar
- System notifications
- Message ordering and gap detection

### 2. ClientService (`service.py`)

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
- `list_rooms()` - Get list of rooms on the node
- `join_room(room_id, username)` - Join a room
- `send_message(room_id, username, content)` - Send a message

### 3. ChatClient (`chat_client.py`)

Extended client with message ordering capabilities.

**Features:**

- Per-room message buffers
- Ordered message delivery
- Duplicate detection
- UI callback integration

### 4. Protocol Messages (`protocol.py`)

Message classes for client-server communication.

**Implemented Messages:**

- `CreateRoomRequest` / `RoomCreatedResponse`
- `ListRoomsRequest` / `RoomsListResponse`
- `JoinRoomRequest` / `JoinRoomSuccessResponse` / `JoinRoomErrorResponse`
- `SendMessageRequest` / `MessageSentConfirmation`
- `NewMessageNotification`
- `MemberJoinedNotification`
- `MessageErrorResponse`

**Message Format:** All messages use JSON with the following structure:

```json
{
  "type": "message_type",
  "data": { ... message-specific fields ... }
}
```

### 5. MessageBuffer (`message_buffer.py`)

Client-side message ordering buffer.

**Features:**

- Binary search insertion (O(log n))
- Sequential message retrieval
- Gap detection
- Memory-bounded operation

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
    
    # List rooms
    rooms = await service.list_rooms()
    for room in rooms.rooms:
        print(f"Room: {room.room_name}")
    
    # Create a room
    response = await service.create_room(
        room_name="general",
        creator_id="user123"
    )
    print(f"Room created: {response.room_id}")
    
    # Join the room
    join_response = await service.join_room(
        room_id=response.room_id,
        username="user123"
    )
    
    # Send a message
    await service.send_message(
        room_id=response.room_id,
        username="user123",
        content="Hello, World!"
    )
    
    # Disconnect
    await service.disconnect()

asyncio.run(main())
```

### Using ChatClient with Message Ordering

```python
from src.client import ChatClient
import asyncio

async def main():
    client = ChatClient("ws://localhost:8000/ws")
    
    # Set up callbacks
    client.set_on_message_ready(lambda msg: print(f"Message: {msg}"))
    client.set_on_member_joined(lambda data: print(f"Member joined: {data}"))
    
    await client.connect()
    client.set_username("user123")
    
    # Join a room
    response = await client.join_room("room-id", "user123")
    client.set_current_room(response.room_id)
    
    # Start receiving messages
    await client.receive_messages()

asyncio.run(main())
```

## Testing

Tests are located in `tests/test_*.py`.

Run all tests:

```bash
poetry run pytest -v
```

Run UI-specific tests:

```bash
poetry run pytest tests/test_ui.py -v
```

## Architecture Notes

### Dependency Injection

The `ClientService` supports dependency injection for the WebSocket connection
factory, making it testable:

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
- Compatible with Textual's async nature

## Integration Points

### With Node Server

The client service expects the node server to:

1. Accept WebSocket connections at `/ws` endpoint
2. Handle JSON-formatted messages
3. Respond with appropriate message types
4. Broadcast messages to room members

**Protocol Contract:**

- Client sends requests with `type` field
- Server responds with corresponding response types
- Real-time notifications for new messages and member joins

## Development Status

### ✅ Completed

- [x] Client service module structure
- [x] WebSocket connection/disconnection
- [x] Protocol message classes
- [x] Room creation, listing, and joining
- [x] Message sending and receiving
- [x] Message ordering and buffering
- [x] Terminal-based UI with Textual
- [x] Connection management screen
- [x] Room discovery (local and global)
- [x] Room creation dialog
- [x] Chat interface with message display
- [x] Member list sidebar
- [x] System notifications
- [x] Basic test coverage
- [x] Documentation

### 🚧 Future Enhancements

- [ ] Multiple simultaneous room participation
- [ ] Private messaging
- [ ] User profiles
- [ ] Message search
- [ ] Keyboard shortcuts customization
- [ ] Theme support
- [ ] Message notifications
- [ ] Persistent conversation history

## Contributing

When implementing new features:

1. **Add protocol messages** in `protocol.py` first
2. **Implement service methods** in `service.py`
3. **Update UI** in `ui/app.py`
4. **Write tests** in `tests/`
5. **Update this README** with new features

## Related Documentation

- [Architecture Overview](../../docs/architecture.md)
- Node server documentation
