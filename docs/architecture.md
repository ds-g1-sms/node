# Simplified Distributed Message Service - Architecture

______________________________________________________________________

## Core Architecture: Distributed Chat System

### System Components

The implemented system consists of the following components:

1. **Node Types** (all nodes are equal peers)

   - Each node runs the full chat service stack
   - Each node can host multiple chat rooms
   - Minimum 3 nodes recommended for fault tolerance

2. **State Management Layer** (`room_state.py`)

   - **In-Memory State**: Active chat rooms, messages, and member information
   - **RoomStateManager**: Central state management with thread-safe operations
   - **MemberInfo**: Tracks room members with activity timestamps
   - **NodeHealth**: Monitors peer node health with heartbeat tracking
   - **Room Distribution**: Each node hosts its own rooms independently

3. **Coordination Layer**

   - **Administrator-Based Message Ordering**: Room creator/admin decides
     message order
   - **Two-Phase Commit Protocol**: Implemented for room deletion coordination
     - Phase 1: Prepare (all nodes check readiness)
     - Phase 2: Commit or Rollback
     - Handles coordinated room deletion across nodes
   - **Health Monitoring**: Periodic heartbeat checks between nodes
   - **Disconnect Detection**: Automatic cleanup of inactive members

4. **Communication Layers**

   - **WebSocket Server** (`websocket_server.py`): Handles client connections

     - Processes client requests (list rooms, create room, join room, send
       message)
     - Manages real-time bidirectional communication
     - Coordinates with XML-RPC server for distributed operations

   - **XML-RPC Server** (`xmlrpc_server.py`): Inter-node communication

     - Exposes methods for peer-to-peer operations
     - Handles room discovery, message forwarding, and coordination
     - Implements 2PC protocol for room deletion
     - Provides heartbeat endpoint for health checks

5. **Modular Architecture**

   - **Schemas Module** (`schemas/`): Standardized data structures

     - `messages.py`: Message data structures and confirmations
     - `events.py`: Member join/leave and room deletion events
     - `responses.py`: Success and error response formats

   - **Utils Module** (`utils/`): Reusable utility functions

     - `broadcast.py`: Peer broadcast functionality
     - `validation.py`: Input validation utilities

   - **Peer Registry** (`peer_registry.py`): Manages peer node connections

6. **Consistency Approach**

   - **Administrator Authority**: The node hosting a room acts as authority for
     that room
   - **Message Ordering**: Administrator node determines final message order
   - **Membership Management**: Administrator handles join/leave operations
   - **Sequence Numbers**: Messages assigned sequential numbers for ordering

## Requirements

### a) Stateful with Global State

**Solution**: Distributed state across peer nodes

- Each node maintains its own state (rooms it hosts, connected users)
- Nodes communicate to share information about available rooms
- Node discovery through direct peer connections
- **CockroachDB**: For optional persistent storage (future feature)

**State Components**:

- Local room registry per node
- Connected users per node
- In-memory message buffers (no history before joining in prototype)
- Optional: Future persistent storage for chat history

### b) Data Consistency and Synchronization

**Administrator-Based Consistency Model**:

**Room Administrator Authority**:

- The node that creates a room becomes its administrator
- Administrator node is the authority for message ordering
- Members follow the administrator's ordering decisions
- Simple and sufficient complexity for the system

**Message Synchronization**:

```
1. Message Send:
   - Client → Connected Node
   - If node is room admin: Accept and broadcast with sequence number
   - If node is not admin: Forward to administrator node
   - Administrator assigns order and broadcasts to all members
   - Members receive and display in administrator's order

2. Room Operations:
   - Join/Leave: Handled by administrator node
   - Room Info: Queried from administrator node
   - Room Deletion: Two-phase commit across relevant nodes
```

**Benefits of Administrator Approach**:

- Simpler than complex consensus protocols
- Clear authority for message ordering
- Reduces system complexity significantly
- Sufficient for course requirements

### c) Consensus (Shared Decision)

**Simplified Coordination with Two-Phase Commit**:

**When Coordination is Needed**:

- Room deletion (needs to be coordinated across nodes)
- Potentially room migration (future feature)

**Two-Phase Commit Protocol for Room Deletion**:

```
Phase 1 (Prepare):
1. Administrator node initiates deletion
2. Sends PREPARE message to all nodes with room members
3. Each node checks if it can delete (no pending operations)
4. Nodes respond with READY or ABORT

Phase 2 (Commit):
1. If all nodes respond READY:
   - Administrator sends COMMIT message
   - All nodes delete room data
2. If any node responds ABORT:
   - Administrator sends ROLLBACK message
   - Deletion is cancelled
```

**Why Two-Phase Commit Instead of Raft**:

- Much simpler to implement and understand
- Sufficient for room deletion coordination
- Learning existing Raft implementation is time-consuming
- Implementing Raft from scratch is not recommended (too complex)
- Acceptable trade-off: May have issues with node failure, but simpler design

**Note**: For the prototype, we may not even implement room deletion to keep it
simpler.

### d) Fault Tolerance

**Node Failure Handling**:

**Administrator Node Failure**:

- Rooms hosted on failed node become unavailable
- Users in those rooms are disconnected
- Health monitoring detects failures through heartbeat mechanism
- Rooms can be recreated on other nodes

**Member Node Failure**:

- User disconnects from room
- Administrator removes user from room member list
- No impact on room availability

**Implemented Fault Tolerance Strategies**:

1. **Health Checks**: Heartbeat mechanism between nodes

   - Configurable intervals (default: 30 seconds)
   - Timeout detection (default: 2 seconds per check)
   - Maximum failure tracking before node marked as failed

2. **Failure Detection**:

   - Timeout-based detection for heartbeat failures
   - Inactivity timeout for member cleanup (default: 15 minutes)
   - Automatic cleanup tasks run periodically (default: 60 seconds)

3. **Graceful Degradation**: Rooms survive as long as admin node is up

4. **Disconnect Notifications**:

   - Peer nodes notified when members disconnect
   - Automatic member list synchronization
   - Room member counts updated in real-time

**Future Enhancements** (not yet implemented):

- Room replication across multiple nodes
- Automatic room migration on node failure
- Persistent storage to recover room state

### e) Scalability

**Horizontal Scaling**:

**Adding New Nodes**:

```
1. New node joins the network
2. Announces itself to existing nodes
3. New node can host new rooms
4. Users can connect to any available node
5. Room discovery: Nodes share information about available rooms
```

**Scaling Approach**:

**User Scalability**:

- More nodes = more users can connect
- Each node handles its own connected users
- Load distribution through client choice of connection node

**Room Scalability**:

- More nodes = more rooms can be hosted
- Each node can host multiple rooms
- Rooms are independent from each other

**Prototype Scalability** (simplified):

- Start with 3-5 nodes
- Fixed number of rooms (one per node initially)
- Focus on demonstrating server-to-server communication
- Scaling complexity deferred to future enhancements

## Communication Protocols

### Inter-Node Communication (Server-to-Server)

- **XML-RPC**: For structured server-to-server communication using Python's
  native library
- **XML Serialization**: Standard XML-based serialization
- Focus area for the course requirements
- Handles: room discovery, message forwarding, coordination

### Client-Node Communication

- **WebSockets**: Real-time bidirectional messaging
- Clients can be co-located with servers for prototype
- Simple connection protocol

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer (Textual UI)                │
│     Terminal-based chat client with rich UI                 │
└─────────────────┬───────────────────────────────────────────┘
                  │ WebSocket
┌─────────────────┴───────────────────────────────────────────┐
│                    Node 1 (Peer & Admin for Room A)         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Client Handler (WebSocket)                           │   │
│  │  - Client connection handling                        │   │
│  │  - Request processing (list, create, join, message)  │   │
│  │  - Room member tracking                              │   │
│  └──────────────┬───────────────────────────────────────┘   │
│  ┌──────────────┴───────────────────────────────────────┐   │
│  │ Business Logic Layer                                 │   │
│  │  - RoomStateManager (room_state.py)                  │   │
│  │  - Message Ordering & Sequence Numbers               │   │
│  │  - Member Management with Activity Tracking          │   │
│  │  - Health Monitoring (NodeHealth, MemberInfo)        │   │
│  └──────────────┬───────────────────────────────────────┘   │
│  ┌──────────────┴───────────────────────────────────────┐   │
│  │ Inter-Node Communication Handler (RPC)               │   │
│  │  - Inter-node Communication                          │   │
│  │  - Room Discovery (get_hosted_rooms)                 │   │
│  │  - Message Forwarding & Broadcasting                 │   │
│  │  - 2PC Protocol (prepare/commit/rollback)            │   │
│  │  - Heartbeat endpoint                                │   │
│  └──────────────┬───────────────────────────────────────┘   │
│  ┌──────────────┴───────────────────────────────────────┐   │
│  │ State Layer (In-Memory)                              │   │
│  │  - Room States (RoomState dataclass)                 │   │
│  │  - Member Information (MemberInfo)                   │   │
│  │  - Message History per Room                          │   │
│  │  - Node Health Status (NodeHealth)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────────┘
                  │ XML-RPC (Server-to-Server Communication)
         ┌────────┴────────┬────────────────┐
         │                 │                │
    ┌────┴─────┐      ┌────┴─────┐     ┌────┴─────┐
    │  Node 1  │←────→│  Node 2  │←───→│  Node 3  │
    │ (Room A) │      │ (Room B) │     │ (Room C) │
    └──────────┘      └──────────┘     └──────────┘
    (Each node administers its own rooms)
```

## Implementation Status

### Implemented Features

The following features have been successfully implemented:

**Core Functionality**:

- **Dynamic room creation**: Clients can create rooms on any node
- **Room discovery mechanism**: Global room discovery across all peer nodes
- **In-memory state management**: All room and member state maintained in memory
- **Group chat**: Multi-user chat rooms with real-time messaging
- **Textual UI client**: Rich terminal-based user interface with multiple
  screens
- **Server-to-server communication**: Full XML-RPC implementation for peer
  coordination

**Distributed Features**:

- **Administrator-based message ordering**: Room creator assigns sequence
  numbers
- **Message forwarding**: Non-admin nodes forward messages to admin node
- **Message broadcasting**: Admin nodes broadcast ordered messages to all peers
- **Member join/leave coordination**: Events synchronized across all nodes
- **Room deletion with 2PC**: Two-phase commit protocol for coordinated deletion

**Fault Tolerance**:

- **Health monitoring**: Periodic heartbeat checks between nodes
- **Disconnect detection**: Automatic detection and cleanup of disconnected
  members
- **Inactivity timeouts**: Stale member cleanup after configurable timeout
- **Node failure handling**: Failed nodes detected via heartbeat mechanism

**Code Organization**:

- **Modular architecture**: Schemas and utils modules for code reuse
- **Standardized data structures**: Consistent message, event, and response
  formats
- **Broadcast utilities**: Reusable functions for peer communication
- **Input validation**: Message content validation utilities

### Not Yet Implemented

**Future Enhancements** (beyond current scope):

- **Persistent storage**: No database integration (all state is in-memory)
- **Chat history**: Messages only available while room is active
- **Room replication**: No redundancy for room state
- **Automatic room migration**: Rooms unavailable if admin node fails
- **Private messaging**: System supports group chat only

### Development Environment

- **3-5 nodes**: For prototype testing
- **Single machine**: Can run all nodes locally
- **Network**: localhost connections for development
- **Simple setup**: Easy to iterate and debug
- **Clients co-located**: Simplifies deployment for prototype

## Trade-offs and Considerations

**Advantages of Simplified Design**:

- Much simpler to implement and understand
- Administrator-based ordering is intuitive
- Two-phase commit is easier than Raft
- Focuses on core distributed system concepts
- Achievable within course timeline

**Known Limitations** (Acceptable for prototype):

- Room unavailable if administrator node fails
- Two-phase commit has issues with coordinator failure
- No chat history before joining (prototype)
- Limited fault tolerance in initial version

**Future Enhancements** (Beyond Prototype):

- Room replication for high availability
- Persistent storage for chat history
- More sophisticated consensus if needed
- Dynamic room migration

**Tech Stack**:

- **Language**: Python (easy to develop, excellent library support)
- **Server-to-Server**: XML-RPC (Python's native XML-RPC library)
- **Coordination**: Custom two-phase commit implementation
