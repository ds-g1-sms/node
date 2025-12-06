"""
Chat Application UI

Main application class for the distributed chat system terminal UI.
Built using the Textual framework.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import (
    Container,
    Horizontal,
    Vertical,
    ScrollableContainer,
)
from textual.css.query import NoMatches
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from ..chat_client import ChatClient

logger = logging.getLogger(__name__)


class MessageDisplay(Static):
    """Widget for displaying a single chat message."""

    def __init__(
        self,
        username: str,
        message_content: str,
        timestamp: str,
        is_own_message: bool = False,
    ) -> None:
        """Initialize message display."""
        super().__init__()
        self.msg_username = username
        self.msg_content = message_content
        self.msg_timestamp = timestamp
        self.is_own_message = is_own_message

    def compose(self) -> ComposeResult:
        """Compose the message display."""
        time_part = (
            self.msg_timestamp.split("T")[1][:8]
            if "T" in self.msg_timestamp
            else ""
        )
        prefix = "You" if self.is_own_message else self.msg_username
        yield Static(
            f"[bold cyan]{prefix}[/] [dim]{time_part}[/]\n{self.msg_content}",
            classes="message-content",
        )


class SystemMessage(Static):
    """Widget for displaying system messages and notifications."""

    def __init__(self, message: str, message_type: str = "info") -> None:
        """Initialize system message display."""
        self.message = message
        self.message_type = message_type
        super().__init__()

    def compose(self) -> ComposeResult:
        """Compose the system message."""
        color = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
            "success": "green",
        }.get(self.message_type, "white")
        yield Static(f"[{color}]⚡ {self.message}[/]", classes="system-message")


class ConnectionScreen(Container):
    """Screen for establishing connection to a node."""

    def compose(self) -> ComposeResult:
        """Compose the connection screen."""
        yield Static(
            "[bold blue]Distributed Chat System[/]",
            id="title",
            classes="screen-title",
        )
        yield Static("Enter your details to connect:", classes="subtitle")
        with Vertical(id="connection-form"):
            yield Label("Username:")
            yield Input(
                placeholder="Enter your username...", id="username-input"
            )
            yield Label("Node Address:")
            yield Input(
                placeholder="host:port (e.g., localhost:8000)",
                id="node-address-input",
            )
            yield Button("Connect", id="connect-btn", variant="primary")
        yield Static("", id="connection-status", classes="status-message")


class RoomListScreen(Container):
    """Screen for viewing and managing rooms."""

    def compose(self) -> ComposeResult:
        """Compose the room list screen."""
        yield Static(
            "[bold blue]Available Rooms[/]",
            id="rooms-title",
            classes="screen-title",
        )
        with Horizontal(id="room-actions"):
            yield Button("Refresh", id="refresh-btn", variant="default")
            yield Button(
                "Local Only", id="local-discover-btn", variant="default"
            )
            yield Button("Create Room", id="create-room-btn", variant="primary")
            yield Button("Disconnect", id="disconnect-btn", variant="warning")
        yield DataTable(id="room-table")
        yield Static("", id="room-status", classes="status-message")


class CreateRoomDialog(Container):
    """Dialog for creating a new room."""

    def compose(self) -> ComposeResult:
        """Compose the create room dialog."""
        yield Static(
            "[bold blue]Create New Room[/]",
            classes="screen-title",
        )
        with Vertical(id="create-room-form"):
            yield Label("Room Name:")
            yield Input(placeholder="Enter room name...", id="room-name-input")
            yield Label("Description (optional):")
            yield Input(
                placeholder="Enter description...", id="room-desc-input"
            )
            with Horizontal(classes="button-row"):
                yield Button(
                    "Create", id="confirm-create-btn", variant="primary"
                )
                yield Button(
                    "Cancel", id="cancel-create-btn", variant="default"
                )
        yield Static("", id="create-room-status", classes="status-message")


class DeleteRoomDialog(Container):
    """Confirmation dialog for deleting a room."""

    def compose(self) -> ComposeResult:
        """Compose the delete room dialog."""
        yield Static(
            "[bold red]Delete Room[/]",
            classes="screen-title",
        )
        with Vertical(id="delete-room-form"):
            yield Static(
                "",
                id="delete-room-message",
                classes="dialog-message",
            )
            yield Static(
                "[yellow]This action cannot be undone. "
                "All members will be disconnected.[/]",
                classes="warning-message",
            )
            with Horizontal(classes="button-row"):
                yield Button(
                    "Cancel", id="cancel-delete-btn", variant="default"
                )
                yield Button(
                    "Delete Room", id="confirm-delete-btn", variant="error"
                )
        yield Static("", id="delete-room-status", classes="status-message")


class ChatScreen(Container):
    """Screen for chatting in a room."""

    def compose(self) -> ComposeResult:
        """Compose the chat screen."""
        with Horizontal(id="chat-container"):
            with Vertical(id="chat-main"):
                yield Static("", id="room-header", classes="room-header")
                yield ScrollableContainer(id="messages-container")
                with Horizontal(id="message-input-row"):
                    yield Input(
                        placeholder="Type a message...",
                        id="message-input",
                    )
                    yield Button("Send", id="send-btn", variant="primary")
            with Vertical(id="sidebar"):
                yield Static("[bold]Members[/]", classes="sidebar-header")
                yield ListView(id="member-list")
                yield Button(
                    "Leave Room", id="leave-room-btn", variant="warning"
                )
                yield Button(
                    "Delete Room",
                    id="delete-room-btn",
                    variant="error",
                    classes="hidden",
                )


class ChatApp(App):
    """Main chat application."""

    CSS = """
    Screen {
        layout: vertical;
    }

    .screen-title {
        text-align: center;
        padding: 1 0;
        text-style: bold;
    }

    .subtitle {
        text-align: center;
        padding: 0 0 1 0;
    }

    #connection-form {
        align: center middle;
        padding: 2;
        width: 60;
        height: auto;
    }

    #connection-form Input {
        margin: 0 0 1 0;
    }

    #connection-form Button {
        margin: 1 0 0 0;
        width: 100%;
    }

    .status-message {
        text-align: center;
        padding: 1;
    }

    ConnectionScreen {
        align: center middle;
    }

    RoomListScreen {
        padding: 1;
    }

    #room-actions {
        height: 3;
        padding: 0 0 1 0;
    }

    #room-actions Button {
        margin: 0 1 0 0;
    }

    #room-table {
        height: 1fr;
    }

    CreateRoomDialog {
        align: center middle;
        padding: 2;
    }

    #create-room-form {
        width: 50;
        padding: 1;
        border: solid green;
    }

    #create-room-form Input {
        margin: 0 0 1 0;
    }

    .button-row {
        height: 3;
        margin: 1 0 0 0;
    }

    .button-row Button {
        margin: 0 1 0 0;
    }

    ChatScreen {
        height: 100%;
    }

    #chat-container {
        height: 100%;
    }

    #chat-main {
        width: 3fr;
    }

    #sidebar {
        width: 1fr;
        border-left: solid $primary;
        padding: 0 1;
    }

    .sidebar-header {
        padding: 1 0;
        text-align: center;
    }

    #member-list {
        height: 1fr;
    }

    #leave-room-btn {
        margin: 1 0 0 0;
    }

    .room-header {
        padding: 1;
        background: $surface;
        text-align: center;
    }

    #messages-container {
        height: 1fr;
        padding: 1;
    }

    #message-input-row {
        height: 3;
        padding: 0 1;
    }

    #message-input {
        width: 1fr;
    }

    #send-btn {
        margin: 0 0 0 1;
    }

    MessageDisplay {
        padding: 0 0 1 0;
    }

    .message-content {
        padding: 0 1;
    }

    .own-message .message-content {
        text-align: right;
    }

    SystemMessage {
        padding: 0 0 1 0;
    }

    .system-message {
        text-align: center;
        text-style: italic;
    }

    .hidden {
        display: none;
    }

    #delete-room-btn {
        margin: 1 0 0 0;
    }

    DeleteRoomDialog {
        align: center middle;
        padding: 2;
    }

    #delete-room-form {
        width: 50;
        padding: 1;
        border: solid red;
    }

    .dialog-message {
        padding: 1 0;
        text-align: center;
    }

    .warning-message {
        padding: 1 0;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "go_back", "Back", show=True),
        Binding("r", "refresh_rooms", "Refresh", show=False),
    ]

    def __init__(self) -> None:
        """Initialize the chat application."""
        super().__init__()
        self.client: Optional[ChatClient] = None
        self.username: Optional[str] = None
        self.current_room_id: Optional[str] = None
        self.current_room_name: Optional[str] = None
        self.current_room_creator: Optional[str] = None
        self.current_members: List[str] = []
        self._current_screen = "connection"
        self._receive_task: Optional[asyncio.Task] = None
        self._deletion_in_progress = False
        self._rooms_cache: Dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield Header()
        yield ConnectionScreen(id="connection-screen")
        yield RoomListScreen(id="room-list-screen")
        yield CreateRoomDialog(id="create-room-dialog")
        yield DeleteRoomDialog(id="delete-room-dialog")
        yield ChatScreen(id="chat-screen")
        yield Footer()

    def on_mount(self) -> None:
        """Handle application mount."""
        self._show_screen("connection")

    def _show_screen(self, screen_name: str) -> None:
        """Show a specific screen and hide others."""
        screens = {
            "connection": "connection-screen",
            "room-list": "room-list-screen",
            "create-room": "create-room-dialog",
            "delete-room": "delete-room-dialog",
            "chat": "chat-screen",
        }

        for name, screen_id in screens.items():
            try:
                screen = self.query_one(f"#{screen_id}")
                screen.display = name == screen_name
            except NoMatches:
                pass

        self._current_screen = screen_name

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id

        if button_id == "connect-btn":
            await self._handle_connect()
        elif button_id == "disconnect-btn":
            await self._handle_disconnect()
        elif button_id == "refresh-btn":
            await self._refresh_rooms(global_discovery=True)
        elif button_id == "local-discover-btn":
            await self._refresh_rooms(global_discovery=False)
        elif button_id == "create-room-btn":
            self._show_screen("create-room")
        elif button_id == "confirm-create-btn":
            await self._handle_create_room()
        elif button_id == "cancel-create-btn":
            self._show_screen("room-list")
        elif button_id == "send-btn":
            await self._handle_send_message()
        elif button_id == "leave-room-btn":
            await self._handle_leave_room()
        elif button_id == "delete-room-btn":
            self._show_delete_confirmation()
        elif button_id == "confirm-delete-btn":
            await self._handle_delete_room()
        elif button_id == "cancel-delete-btn":
            self._show_screen("chat")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submit events (Enter key)."""
        input_id = event.input.id

        if input_id == "message-input":
            await self._handle_send_message()
        elif input_id in ("username-input", "node-address-input"):
            await self._handle_connect()
        elif input_id in ("room-name-input", "room-desc-input"):
            await self._handle_create_room()

    async def on_data_table_row_selected(
        self, event: DataTable.RowSelected
    ) -> None:
        """Handle room selection from table."""
        if event.row_key:
            room_id = str(event.row_key.value)
            await self._handle_join_room(room_id)

    async def _handle_connect(self) -> None:
        """Handle connection to a node."""
        try:
            username_input = self.query_one("#username-input", Input)
            address_input = self.query_one("#node-address-input", Input)
            status = self.query_one("#connection-status", Static)

            username = username_input.value.strip()
            address = address_input.value.strip()

            if not username:
                status.update("[red]Please enter a username[/]")
                return
            if not address:
                status.update("[red]Please enter a node address[/]")
                return

            status.update("[yellow]Connecting...[/]")

            # Parse address - add ws:// prefix if not present
            if "://" not in address:
                ws_url = f"ws://{address}"
            else:
                ws_url = address

            # Create client and connect
            self.client = ChatClient(ws_url)
            self.client.set_username(username)

            # Set up callbacks
            self.client.set_on_message_ready(self._on_message_received)
            self.client.set_on_member_joined(self._on_member_joined)
            self.client.set_on_member_left(self._on_member_left)
            self.client.set_on_ordering_gap_detected(self._on_ordering_gap)
            # Set up deletion callbacks
            self.client.set_on_delete_initiated(self._on_delete_initiated)
            self.client.set_on_delete_success(self._on_delete_success)
            self.client.set_on_delete_failed(self._on_delete_failed)
            self.client.set_on_room_deleted(self._on_room_deleted)

            await self.client.connect()
            self.username = username

            status.update("[green]Connected![/]")
            self._show_screen("room-list")
            await self._refresh_rooms(global_discovery=True)

        except Exception as e:
            logger.error("Connection failed: %s", e)
            status = self.query_one("#connection-status", Static)
            status.update(f"[red]Connection failed: {e}[/]")

    async def _handle_disconnect(self) -> None:
        """Handle disconnection from node."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self.client:
            await self.client.disconnect()
            self.client = None

        self.username = None
        self.current_room_id = None
        self.current_room_name = None
        self.current_members = []

        self._show_screen("connection")
        status = self.query_one("#connection-status", Static)
        status.update("[yellow]Disconnected[/]")

    async def _refresh_rooms(self, global_discovery: bool = False) -> None:
        """Refresh the room list."""
        if not self.client or not self.client.is_connected:
            return

        status = self.query_one("#room-status", Static)
        table = self.query_one("#room-table", DataTable)

        try:
            status.update("[yellow]Loading rooms...[/]")

            if global_discovery:
                # Global discovery requires a custom request
                rooms_data = await self._discover_rooms_globally()
            else:
                response = await self.client.list_rooms()
                rooms_data = [
                    {
                        "room_id": r.room_id,
                        "room_name": r.room_name,
                        "description": r.description or "",
                        "member_count": r.member_count,
                        "admin_node": r.admin_node,
                    }
                    for r in response.rooms
                ]

            # Store rooms data for later reference (e.g., getting creator_id)
            self._rooms_cache = {r["room_id"]: r for r in rooms_data}

            # Update table
            table.clear(columns=True)
            table.add_columns("Name", "Description", "Members", "Admin Node")
            table.cursor_type = "row"

            for room in rooms_data:
                table.add_row(
                    room["room_name"],
                    room.get("description") or "-",
                    str(room["member_count"]),
                    room["admin_node"],
                    key=room["room_id"],
                )

            if rooms_data:
                status.update(
                    f"[green]Found {len(rooms_data)} room(s). "
                    f"Click a row to join.[/]"
                )
            else:
                status.update("[yellow]No rooms available. Create one![/]")

        except Exception as e:
            logger.error("Failed to refresh rooms: %s", e)
            status.update(f"[red]Error: {e}[/]")

    async def _discover_rooms_globally(self) -> List[Dict[str, Any]]:
        """Discover rooms globally across all nodes."""
        if not self.client or not self.client.websocket:
            return []

        # Send discover_rooms request
        request = json.dumps({"type": "discover_rooms"})
        await self.client.websocket.send(request)

        # Receive response - loop until we get the expected response
        # Other messages may be pending in the buffer
        max_attempts = 10
        for _ in range(max_attempts):
            response_json = await self.client.websocket.recv()
            response_data = json.loads(response_json)

            if response_data.get("type") == "global_rooms_list":
                return response_data.get("data", {}).get("rooms", [])
            else:
                # Skip non-discovery responses (e.g., pending broadcasts)
                logger.debug(
                    "Skipping non-discovery response while refreshing: %s",
                    response_data.get("type"),
                )

        logger.warning("Timed out waiting for global_rooms_list response")
        return []

    async def _handle_create_room(self) -> None:
        """Handle room creation."""
        if not self.client or not self.client.is_connected:
            return

        name_input = self.query_one("#room-name-input", Input)
        desc_input = self.query_one("#room-desc-input", Input)
        status = self.query_one("#create-room-status", Static)

        room_name = name_input.value.strip()

        if not room_name:
            status.update("[red]Please enter a room name[/]")
            return

        try:
            status.update("[yellow]Creating room...[/]")

            await self.client.create_room(room_name, self.username)

            # Clear inputs
            name_input.value = ""
            desc_input.value = ""

            status.update(f"[green]Room '{room_name}' created![/]")

            # Go back to room list and refresh
            await self._refresh_rooms(global_discovery=True)

        except Exception as e:
            logger.error("Failed to create room: %s", e)
            status.update(f"[red]Error: {e}[/]")

    async def _handle_join_room(self, room_id: str) -> None:
        """Handle joining a room."""
        if not self.client or not self.client.is_connected:
            return

        status = self.query_one("#room-status", Static)

        try:
            status.update("[yellow]Joining room...[/]")

            response = await self.client.join_room(room_id, self.username)

            self.current_room_id = response.room_id
            self.current_room_name = response.room_name
            self.client.set_current_room(response.room_id)
            self.current_members = list(response.members)

            # Get creator from cache (if available)
            cached_room = self._rooms_cache.get(room_id, {})
            self.current_room_creator = cached_room.get("creator_id")

            # Switch to chat screen
            self._show_screen("chat")
            self._update_chat_screen()

            # Start receiving messages
            self._start_message_receiver()

        except ValueError as e:
            logger.error("Failed to join room: %s", e)
            status.update(f"[red]Failed to join: {e}[/]")
        except Exception as e:
            logger.error("Failed to join room: %s", e)
            status.update(f"[red]Error: {e}[/]")

    async def _handle_leave_room(self) -> None:
        """Handle leaving the current room."""
        # Cancel the receive task first and wait for it to complete
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # Notify server that we're leaving the room
        if self.client and self.current_room_id and self.username:
            try:
                await self.client.leave_room(
                    self.current_room_id, self.username
                )
            except Exception as e:
                logger.warning("Failed to notify server of leave: %s", e)

        if self.client:
            self.client.leave_current_room()

        self.current_room_id = None
        self.current_room_name = None
        self.current_room_creator = None
        self.current_members = []

        # Clear messages
        messages = self.query_one("#messages-container", ScrollableContainer)
        await messages.remove_children()

        self._show_screen("room-list")
        await self._refresh_rooms(global_discovery=True)

    async def _handle_send_message(self) -> None:
        """Handle sending a message."""
        if not self.client or not self.client.is_connected:
            return
        if not self.current_room_id:
            return

        message_input = self.query_one("#message-input", Input)
        content = message_input.value.strip()

        if not content:
            return

        try:
            await self.client.send_message(
                self.current_room_id, self.username, content
            )
            message_input.value = ""
        except Exception as e:
            logger.error("Failed to send message: %s", e)
            self._add_system_message(f"Failed to send message: {e}", "error")

    def _update_chat_screen(self) -> None:
        """Update the chat screen with current room info."""
        try:
            header = self.query_one("#room-header", Static)
            header.update(
                f"[bold]Room: {self.current_room_name}[/] "
                f"| Members: {len(self.current_members)}"
            )

            # Update member list
            member_list = self.query_one("#member-list", ListView)
            member_list.clear()
            for member in self.current_members:
                if member == self.username:
                    display = f"[bold cyan]{member}[/] (you)"
                else:
                    display = member
                member_list.append(ListItem(Label(display)))

            # Show/hide delete button based on whether user is the creator
            delete_btn = self.query_one("#delete-room-btn", Button)
            is_creator = self.current_room_creator == self.username
            if is_creator:
                delete_btn.remove_class("hidden")
            else:
                delete_btn.add_class("hidden")

        except NoMatches:
            pass

    def _start_message_receiver(self) -> None:
        """Start the background task for receiving messages."""
        if self._receive_task:
            self._receive_task.cancel()

        async def receive_loop():
            try:
                if self.client:
                    await self.client.receive_messages()
            except asyncio.CancelledError:
                pass
            except Exception as err:
                logger.error("Message receiver error: %s", err)
                error_msg = str(err)
                # Handle connection loss by going back to connection screen
                asyncio.create_task(self._handle_connection_lost(error_msg))

        self._receive_task = asyncio.create_task(receive_loop())

    def _on_message_received(self, message: Dict[str, Any]) -> None:
        """Callback when a message is ready to display."""
        # Use call_later since this is called from the async event loop
        self.call_later(lambda m=message: self._add_chat_message(m))

    def _on_member_joined(self, data: Dict[str, Any]) -> None:
        """Callback when a member joins the room."""
        username = data.get("username", "Unknown")
        if username != self.username:
            self.call_later(
                lambda: self._add_system_message(
                    f"{username} joined the room", "info"
                )
            )
            # Update member list
            if username not in self.current_members:
                self.current_members.append(username)
                self.call_later(self._update_chat_screen)

    def _on_member_left(self, data: Dict[str, Any]) -> None:
        """Callback when a member leaves the room."""
        username = data.get("username", "Unknown")
        reason = data.get("reason", "")

        if username == self.username:
            # We were removed from the room (inactivity, node failure, etc.)
            room_name = self.current_room_name or "the room"
            asyncio.create_task(
                self._handle_removed_from_room(room_name, reason)
            )
        else:
            # Another member left
            reason_suffix = ""
            if reason and reason != "User disconnected":
                reason_suffix = f" ({reason.lower()})"
            self.call_later(
                lambda u=username, r=reason_suffix: self._add_system_message(
                    f"{u} left the room{r}", "info"
                )
            )
            # Update member list
            if username in self.current_members:
                self.current_members.remove(username)
                self.call_later(self._update_chat_screen)

    def _on_ordering_gap(  # pylint: disable=unused-argument
        self, room_id: str
    ) -> None:
        """Callback when a gap is detected in message ordering."""
        self.call_later(
            lambda: self._add_system_message(
                "⚠️ Some messages may be out of order", "warning"
            )
        )

    def _on_delete_initiated(self, data: Dict[str, Any]) -> None:
        """Callback when room deletion is initiated."""
        initiator = data.get("initiator", "Unknown")
        if initiator != self.username:
            self.call_later(
                lambda: self._add_system_message(
                    f"🗑️ Room deletion initiated by {initiator}", "warning"
                )
            )

    def _on_delete_success(self, data: Dict[str, Any]) -> None:
        """Callback when room deletion succeeds (for initiator)."""
        self._deletion_in_progress = False
        # Will be handled by the async handler

    def _on_delete_failed(self, data: Dict[str, Any]) -> None:
        """Callback when room deletion fails."""
        self._deletion_in_progress = False
        reason = data.get("reason", "Unknown error")
        self.call_later(
            lambda r=reason: self._add_system_message(
                f"❌ Room deletion failed: {r}", "error"
            )
        )

    def _on_room_deleted(self, data: Dict[str, Any]) -> None:
        """Callback when a room is deleted (for all members)."""
        room_name = data.get("room_name", self.current_room_name)
        asyncio.create_task(self._handle_room_deleted_notification(room_name))

    async def _cleanup_room_state(self) -> None:
        """
        Clean up room state when leaving, being removed, or room deleted.

        This handles:
        - Cancelling receive task
        - Clearing client message buffer
        - Clearing room state variables
        - Clearing messages from UI
        """
        # Cancel receive task
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        # Clear client message buffer
        if self.client:
            self.client.leave_current_room()

        # Clear room state
        self.current_room_id = None
        self.current_room_name = None
        self.current_room_creator = None
        self.current_members = []
        self._deletion_in_progress = False

        # Clear messages from UI
        try:
            messages = self.query_one(
                "#messages-container", ScrollableContainer
            )
            await messages.remove_children()
        except NoMatches:
            pass

    async def _handle_room_deleted_notification(self, room_name: str) -> None:
        """Handle the room deleted notification in the UI."""
        await self._cleanup_room_state()

        # Show room list and refresh
        self._show_screen("room-list")
        await self._refresh_rooms(global_discovery=True)

        # Show notification
        try:
            status = self.query_one("#room-status", Static)
            status.update(f"[yellow]Room '{room_name}' has been deleted.[/]")
        except NoMatches:
            pass

    async def _handle_removed_from_room(
        self, room_name: str, reason: str
    ) -> None:
        """
        Handle being removed from a room by the administrator.

        This is called when the current user is removed due to inactivity,
        node failure, or other reasons.

        Args:
            room_name: Name of the room we were removed from
            reason: Reason for removal (e.g., "Inactivity")
        """
        await self._cleanup_room_state()

        # Show room list and refresh
        self._show_screen("room-list")
        await self._refresh_rooms(global_discovery=True)

        # Show notification with reason
        try:
            status = self.query_one("#room-status", Static)
            reason_text = reason.lower() if reason else "unknown reason"
            status.update(
                f"[red]You were removed from '{room_name}' "
                f"due to {reason_text}.[/]"
            )
        except NoMatches:
            pass

    async def _handle_connection_lost(self, error_msg: str) -> None:
        """
        Handle WebSocket connection loss.

        This is called when the connection to the node is lost unexpectedly.
        Cleans up state and returns to the connection screen with an error.

        Args:
            error_msg: Error message describing the connection failure
        """
        # Clear room state first
        self.current_room_id = None
        self.current_room_name = None
        self.current_room_creator = None
        self.current_members = []
        self._deletion_in_progress = False

        # Clear messages from UI if we were in chat
        try:
            messages = self.query_one(
                "#messages-container", ScrollableContainer
            )
            await messages.remove_children()
        except NoMatches:
            pass

        # Clear client state
        if self.client:
            self.client.leave_current_room()
            try:
                await self.client.disconnect()
            except Exception:
                pass  # Already disconnected
            self.client = None

        self.username = None

        # Go to connection screen with error message
        self._show_screen("connection")
        try:
            status = self.query_one("#connection-status", Static)
            status.update(f"[red]Connection lost: {error_msg}[/]")
        except NoMatches:
            pass

    def _show_delete_confirmation(self) -> None:
        """Show the delete room confirmation dialog."""
        try:
            message = self.query_one("#delete-room-message", Static)
            message.update(
                f"Are you sure you want to delete "
                f"[bold]'{self.current_room_name}'[/]?"
            )
            status = self.query_one("#delete-room-status", Static)
            status.update("")
            self._show_screen("delete-room")
        except NoMatches:
            pass

    async def _handle_delete_room(self) -> None:
        """Handle the room deletion request."""
        if not self.client or not self.client.is_connected:
            return

        if self._deletion_in_progress:
            return

        if not self.current_room_id or not self.username:
            return

        try:
            status = self.query_one("#delete-room-status", Static)
            status.update("[yellow]Deleting room...[/]")
            self._deletion_in_progress = True

            # Send deletion request
            await self.client.delete_room(self.current_room_id, self.username)

            # Wait for response through the message loop
            # The callbacks will handle the result

        except Exception as e:
            logger.error("Failed to initiate room deletion: %s", e)
            self._deletion_in_progress = False
            try:
                status = self.query_one("#delete-room-status", Static)
                status.update(f"[red]Error: {e}[/]")
            except NoMatches:
                pass

    def _add_chat_message(self, message: Dict[str, Any]) -> None:
        """Add a chat message to the display."""
        try:
            messages = self.query_one(
                "#messages-container", ScrollableContainer
            )
            username = message.get("username", "Unknown")
            content = message.get("content", "")
            timestamp = message.get("timestamp", "")
            is_own = username == self.username

            msg_widget = MessageDisplay(
                username=username,
                message_content=content,
                timestamp=timestamp,
                is_own_message=is_own,
            )
            if is_own:
                msg_widget.add_class("own-message")
            messages.mount(msg_widget)
            messages.scroll_end()
        except NoMatches:
            pass

    def _add_system_message(
        self, message: str, message_type: str = "info"
    ) -> None:
        """Add a system message to the display."""
        try:
            messages = self.query_one(
                "#messages-container", ScrollableContainer
            )
            messages.mount(SystemMessage(message, message_type))
            messages.scroll_end()
        except NoMatches:
            pass

    def action_go_back(self) -> None:
        """Handle back action."""
        if self._current_screen == "chat":
            asyncio.create_task(self._handle_leave_room())
        elif self._current_screen == "create-room":
            self._show_screen("room-list")
        elif self._current_screen == "delete-room":
            self._show_screen("chat")
        elif self._current_screen == "room-list":
            asyncio.create_task(self._handle_disconnect())

    def action_refresh_rooms(self) -> None:
        """Handle refresh rooms action."""
        if self._current_screen == "room-list":
            asyncio.create_task(self._refresh_rooms(global_discovery=True))
