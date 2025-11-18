# Simplified Distributed Message Service - Architecture

______________________________________________________________________

## Core Architecture: Distributed Chat System

### System Components

1. **Node Types** (all nodes are equal peers)

   - Each node runs the full chat service stack
   - Each node can host chat rooms
   - Minimum 3 nodes for fault tolerance

2. **State Management Layer**

   - **In-Memory State**: For active chat rooms and messages
   - **Optional Persistent Storage**: For future chat history (not in initial
     prototype)
   - **Room Distribution**: Rooms distributed across nodes

3. **Coordination Layer**

   - **Administrator-Based Message Ordering**: Room creator/admin decides
     message order
   - **Two-Phase Commit Protocol**: For room deletion coordination
     - Simpler than Raft, sufficient for coordinated operations
     - Easier to implement and understand
     - Acceptable trade-off with node failure scenarios

4. **Consistency Approach**

   - **Administrator Authority**: The node hosting a room acts as authority for
     that room
   - **Message Ordering**: Administrator node determines final message order
   - **Membership Management**: Administrator handles join/leave operations

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
- For prototype: Simple detection and notification
- Future enhancement: Room migration to another node

**Member Node Failure**:

- User disconnects from room
- Administrator removes user from room member list
- No impact on room availability

**Fault Tolerance Strategies** (for prototype):

1. **Health Checks**: Basic heartbeat between nodes
2. **Failure Detection**: Timeout-based detection
3. **Graceful Degradation**: Rooms survive as long as admin node is up
4. **User Notification**: Inform users when rooms become unavailable

**Future Enhancements** (beyond prototype):

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

- **gRPC**: For structured server-to-server communication
- **Protocol Buffers**: Efficient serialization
- Focus area for the course requirements
- Handles: room discovery, message forwarding, coordination

### Client-Node Communication

- **WebSockets**: Real-time bidirectional messaging
- Clients can be co-located with servers for prototype
- Simple connection protocol

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer (Co-located)                │
│     Simple clients on same nodes as servers for prototype   │
└─────────────────┬───────────────────────────────────────────┘
                  │ WebSocket
┌─────────────────┴───────────────────────────────────────────┐
│                    Node 1 (Peer & Admin for Room A)         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Client Handler (WebSocket)                           │   │
│  └──────────────┬───────────────────────────────────────┘   │
│  ┌──────────────┴───────────────────────────────────────┐   │
│  │ Business Logic Layer                                 │   │
│  │  - Room Management (Admin for owned rooms)           │   │
│  │  - Message Ordering (for administered rooms)         │   │
│  │  - Member Management                                 │   │
│  └──────────────┬───────────────────────────────────────┘   │
│  ┌──────────────┴───────────────────────────────────────┐   │
│  │ Coordination Layer                                   │   │
│  │  - Two-Phase Commit (for deletion)                   │   │
│  │  - Node Discovery & Communication                    │   │
│  └──────────────┬───────────────────────────────────────┘   │
│  ┌──────────────┴───────────────────────────────────────┐   │
│  │ State Layer (In-Memory)                              │   │
│  │  - Local Room State (Room A)                         │   │
│  │  - Connected Users                                   │   │
│  │  - Message Buffer (no history before join)           │   │
│  └──────────────┬───────────────────────────────────────┘   │
│  ┌──────────────┴───────────────────────────────────────┐   │
│  │ Optional: Future Persistent Storage                  │   │
│  │  - CockroachDB (for chat history)                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────┬───────────────────────────────────────────┘
                  │ gRPC (Server-to-Server Communication)
         ┌────────┴────────┬────────────────┐
         │                 │                │
    ┌────┴─────┐      ┌────┴─────┐     ┌────┴─────┐
    │  Node 2  │←────→│  Node 3  │←───→│  Node 1  │
    │ (Room B) │      │ (Room C) │     │ (Room A) │
    └──────────┘      └──────────┘     └──────────┘
    (Each node administers its own room(s))
```

## Prototype Implementation Approach

### Simplest Running Prototype

Focus on getting a working system quickly, then add features:

**Phase 1 - Basic Prototype**:

- **Fixed chat rooms**: One room per server (3 rooms for 3 nodes)
- **No persistent storage**: All state in memory
- **No history**: Clients only see messages sent after they join
- **Group chat only**: No private messaging needed for prototype
- **Co-located clients**: Clients run on same machines as servers
- **Focus**: Server-to-server communication for message distribution

**Key Implementation Notes**:

- Course focus is on **server-to-server communication** - this is the priority
- Client implementation can be very simple (even command-line)
- Keep extensibility in mind for adding features later
- Design should allow adding dynamic rooms and persistence before demo

**Benefits of Simple Start**:

- Get running system quickly
- Demonstrate core distributed concepts
- Test server-to-server communication thoroughly
- Working foundation to build upon
- Less time learning complex frameworks (Raft, DHT)

### Phase 2 - Enhanced Prototype (If Time Permits)

Add features incrementally:

- Dynamic room creation (clients can create rooms on any node)
- Room discovery mechanism across nodes
- Basic persistence (CockroachDB for chat history)
- Client history retrieval upon joining
- Room deletion with two-phase commit

**Design Principle**: Build simple first, but architect with extensibility in
mind so features can be added just before demo if time allows.

### Development Environment

- **3-5 nodes**: For prototype testing
- **Single machine**: Can run all nodes locally
- **Network**: localhost connections for development
- **Simple setup**: Easy to iterate and debug
- **Clients co-located**: Simplifies deployment for prototype

## Trade-offs and Considerations

**Advantages of Simplified Design**:

- ✅ Much simpler to implement and understand
- ✅ Administrator-based ordering is intuitive
- ✅ Two-phase commit is easier than Raft
- ✅ Focuses on core distributed system concepts
- ✅ Achievable within course timeline

**Known Limitations** (Acceptable for prototype):

- ⚠️ Room unavailable if administrator node fails
- ⚠️ Two-phase commit has issues with coordinator failure
- ⚠️ No chat history before joining (prototype)
- ⚠️ Limited fault tolerance in initial version

**Future Enhancements** (Beyond Prototype):

- Room replication for high availability
- Persistent storage for chat history
- More sophisticated consensus if needed
- Dynamic room migration

**Tech Stack**:

- **Language**: Python (easy to develop, excellent library support)
- **Server-to-Server**: gRPC with Protocol Buffers
- **Database**: CockroachDB (optional, for future persistence)
- **Coordination**: Custom two-phase commit implementation
- **Consensus**: etcd (optional, if time permits for advanced features)
