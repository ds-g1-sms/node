# Distributed Chat System - Terminology

This document defines key terms and concepts used throughout the distributed
chat system.

______________________________________________________________________

## System Architecture Terms

### Node

A peer server in the distributed chat system. Each node:

- Runs both WebSocket and XML-RPC servers
- Can host multiple chat rooms
- Maintains its own in-memory state
- Communicates with other nodes as an equal peer
- Has a unique identifier (node_id)

### Room

A chat space where multiple users can communicate. Each room:

- Has a unique identifier (room_id)
- Is hosted by a single administrator node
- Can have multiple members across different nodes
- Maintains message history while active
- Has a human-readable name

### Administrator (Admin) Node

The node that created and hosts a specific room. The administrator:

- Has authority over the room's state
- Assigns sequence numbers to messages
- Manages the room's member list
- Coordinates room deletion via 2PC
- Broadcasts ordered messages to all peers

### Member Node

A node that has users connected to a room it doesn't administer. Member nodes:

- Forward messages to the administrator node
- Receive broadcasts from the administrator
- Maintain local state about room membership
- Can host multiple members in the same room

### Peer Registry

A registry that maintains the list of known peer nodes. It tracks:

- Node identifiers and their XML-RPC addresses
- Node availability and health status
- Methods for registering and discovering peers

## Communication Terms

### WebSocket

A protocol providing full-duplex communication channels over TCP. Used for:

- Real-time client-to-server communication
- Bidirectional message flow
- Low-latency updates to clients
- Connection state management

### XML-RPC

A remote procedure call protocol using XML for encoding. Used for:

- Server-to-server communication between nodes
- Synchronous method invocations across the network
- Room discovery and coordination
- Message forwarding and broadcasting

### Two-Phase Commit (2PC)

A distributed transaction protocol ensuring all nodes agree on an operation. In
this system:

- **Phase 1 (Prepare)**: Administrator asks all nodes if they can proceed
- **Phase 2 (Commit/Rollback)**: All nodes execute or abort based on consensus
- Used for coordinated room deletion
- Ensures atomic operations across distributed nodes

### Heartbeat

A periodic signal sent between nodes to verify availability. Features:

- Configurable interval (default: 30 seconds)
- Timeout detection (default: 2 seconds)
- Tracks consecutive failures
- Updates node health status

## Data Structure Terms

### RoomState

A dataclass representing the complete state of a room:

- Room metadata (id, name, creator)
- Member list with activity tracking
- Message history
- Creation timestamp
- Administrator node identifier

### MemberInfo

A dataclass tracking information about a room member:

- Username
- Connected node ID
- Join timestamp
- Last activity timestamp
- Used for disconnect detection and cleanup

### NodeHealth

A dataclass monitoring the health of a peer node:

- Node identifier
- Last successful heartbeat timestamp
- Current status (healthy, degraded, failed)
- Consecutive failure count

### Message Data

A standardized structure for chat messages containing:

- Unique message identifier (message_id)
- Room identifier (room_id)
- Sender username
- Message content
- Sequence number (assigned by admin)
- ISO 8601 timestamp

### Sequence Number

An incrementing integer assigned by the administrator node to each message:

- Ensures total ordering of messages
- Starts at 1 for each room
- Used by clients to order messages correctly
- Prevents message reordering issues

## Protocol Terms

### Message Forwarding

The process where a non-admin node sends a message to the administrator:

1. Client sends message to their connected node
2. If node is not the admin, forward to admin via XML-RPC
3. Admin assigns sequence number
4. Admin broadcasts ordered message to all peers

### Message Broadcasting

The process where the administrator distributes messages to all nodes:

1. Admin receives or creates a message
2. Assigns sequence number
3. Calls `receive_message_broadcast()` on all peer nodes
4. Each node delivers to its connected clients in that room

### Room Discovery

The process of finding available rooms across all nodes:

- **Local Discovery**: Listing rooms on the connected node
- **Global Discovery**: Querying all peer nodes via `get_hosted_rooms()`
- Returns room metadata (id, name, member count, admin node)

### Member Event

An event broadcast when room membership changes:

- **member_joined**: User joins a room
- **member_left**: User leaves or disconnects
- Contains: room_id, username, member_count, timestamp
- Synchronized across all nodes

## Client Terms

### Chat Client

The terminal-based user interface application that:

- Connects to a node via WebSocket
- Provides screens for connection, room list, and chat
- Uses the Textual library for rich TUI
- Handles message ordering on the client side

### Message Buffer

A client-side component that:

- Stores messages temporarily
- Orders messages by sequence number
- Handles out-of-order message delivery
- Ensures correct display order

### Connection Screen

The initial UI screen where users:

- Enter their username
- Specify the node address to connect to
- Establish WebSocket connection

### Room List Screen

A UI screen displaying:

- Available rooms (local or global)
- Room metadata (name, member count)
- Options to create or join rooms
- Refresh functionality

### Chat Screen

The main chat interface showing:

- Message history with timestamps
- List of room members
- Input field for sending messages
- System notifications and events

## State Management Terms

### In-Memory State

All room and member data stored in RAM:

- Fast access and updates
- No persistent storage overhead
- State lost when node restarts
- Suitable for prototype and testing

### Room Manager

The `RoomStateManager` class that:

- Maintains all rooms hosted on a node
- Provides thread-safe operations
- Manages room lifecycle (create, delete)
- Tracks member activity

### Activity Tracking

Monitoring user activity to detect disconnections:

- Updates on message sends and heartbeats
- Inactivity timeout (default: 15 minutes)
- Automatic cleanup of stale members
- Periodic cleanup task (default: 60 seconds)

### Stale Member

A room member that:

- Has exceeded the inactivity timeout
- No longer responsive to heartbeat checks
- Is automatically removed from the room
- Triggers a member_left event

## Error Handling Terms

### Error Response

A standardized error message structure containing:

- Error type (e.g., "join_room_error", "message_error")
- Error message (human-readable description)
- Error code (machine-readable identifier)
- Context data (room_id, etc.)

### Transaction ID

A unique identifier for 2PC operations:

- Used to track room deletion transactions
- Ensures idempotency of operations
- Allows correlation of prepare/commit messages
- Optional in current implementation

## Validation Terms

### Message Validation

Checking message content before processing:

- Non-empty content check
- Maximum length limit (5000 characters)
- Returns validation result and error message
- Prevents invalid messages from being processed

### Input Sanitization

Cleaning and validating user inputs:

- Username validation
- Room name validation
- Prevents malformed data
- Ensures system stability

## Deployment Terms

### Docker Compose

A tool for defining multi-container applications:

- Defines 3 nodes in development setup
- Maps ports for external access
- Manages node lifecycle
- Simplifies multi-node testing

### Environment Configuration

Configuration via environment variables:

- Node ID and port assignments
- Peer node addresses
- Timeouts and intervals
- Logging levels

### Health Check Endpoint

An XML-RPC method for monitoring:

- Responds with node status
- Used by Docker health checks
- Interval: 30s, Timeout: 10s
- Start period: 40s, Retries: 3
