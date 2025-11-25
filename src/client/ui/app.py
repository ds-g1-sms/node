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
                "Global Discovery", id="global-discover-btn", variant="default"
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
        self.current_members: List[str] = []
        self._current_screen = "connection"
        self._receive_task: Optional[asyncio.Task] = None

    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        yield Header()
        yield ConnectionScreen(id="connection-screen")
        yield RoomListScreen(id="room-list-screen")
        yield CreateRoomDialog(id="create-room-dialog")
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
            await self._refresh_rooms(global_discovery=False)
        elif button_id == "global-discover-btn":
            await self._refresh_rooms(global_discovery=True)
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

            # Parse address
            if "://" not in address:
                address = f"ws://{address}"
            if not address.endswith("/"):
                ws_url = f"{address}/ws"
            else:
                ws_url = f"{address}ws"

            # Create client and connect
            self.client = ChatClient(ws_url)
            self.client.set_username(username)

            # Set up callbacks
            self.client.set_on_message_ready(self._on_message_received)
            self.client.set_on_member_joined(self._on_member_joined)
            self.client.set_on_ordering_gap_detected(self._on_ordering_gap)

            await self.client.connect()
            self.username = username

            status.update("[green]Connected![/]")
            self._show_screen("room-list")
            await self._refresh_rooms(global_discovery=False)

        except Exception as e:
            logger.error("Connection failed: %s", e)
            status = self.query_one("#connection-status", Static)
            status.update(f"[red]Connection failed: {e}[/]")

    async def _handle_disconnect(self) -> None:
        """Handle disconnection from node."""
        if self._receive_task:
            self._receive_task.cancel()
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

        # Receive response
        response_json = await self.client.websocket.recv()
        response_data = json.loads(response_json)

        if response_data.get("type") == "global_rooms_list":
            return response_data.get("data", {}).get("rooms", [])
        return []

    async def _handle_create_room(self) -> None:
        """Handle room creation."""
        if not self.client or not self.client.is_connected:
            return

        name_input = self.query_one("#room-name-input", Input)
        desc_input = self.query_one("#room-desc-input", Input)
        status = self.query_one("#create-room-status", Static)

        room_name = name_input.value.strip()
        # Description input is captured for future use when API supports it
        _ = desc_input.value.strip()

        if not room_name:
            status.update("[red]Please enter a room name[/]")
            return

        try:
            status.update("[yellow]Creating room...[/]")

            response = await self.client.create_room(room_name, self.username)

            # Clear inputs
            name_input.value = ""
            desc_input.value = ""

            status.update(f"[green]Room '{room_name}' created![/]")

            # Join the created room
            self.current_room_id = response.room_id
            self.current_room_name = response.room_name
            self.client.set_current_room(response.room_id)
            self.current_members = list(response.members)

            # Switch to room list and refresh
            self._show_screen("room-list")
            await self._refresh_rooms(global_discovery=False)

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
        if self._receive_task:
            self._receive_task.cancel()
            self._receive_task = None

        if self.client:
            self.client.leave_current_room()

        self.current_room_id = None
        self.current_room_name = None
        self.current_members = []

        # Clear messages
        messages = self.query_one("#messages-container", ScrollableContainer)
        await messages.remove_children()

        self._show_screen("room-list")
        await self._refresh_rooms(global_discovery=False)

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
                self.call_later(
                    lambda msg=error_msg: self._add_system_message(
                        f"Connection lost: {msg}", "error"
                    )
                )

        self._receive_task = asyncio.create_task(receive_loop())

    def _on_message_received(self, message: Dict[str, Any]) -> None:
        """Callback when a message is ready to display."""
        self.call_from_thread(self._add_chat_message, message)

    def _on_member_joined(self, data: Dict[str, Any]) -> None:
        """Callback when a member joins the room."""
        username = data.get("username", "Unknown")
        if username != self.username:
            self.call_from_thread(
                lambda: self._add_system_message(
                    f"{username} joined the room", "info"
                )
            )
            # Update member list
            if username not in self.current_members:
                self.current_members.append(username)
                self.call_from_thread(self._update_chat_screen)

    # pylint: disable=unused-argument
    def _on_ordering_gap(self, room_id: str) -> None:
        """Callback when a gap is detected in message ordering."""
        self.call_from_thread(
            lambda: self._add_system_message(
                "⚠️ Some messages may be out of order", "warning"
            )
        )

    # pylint: enable=unused-argument

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
        elif self._current_screen == "room-list":
            asyncio.create_task(self._handle_disconnect())

    def action_refresh_rooms(self) -> None:
        """Handle refresh rooms action."""
        if self._current_screen == "room-list":
            asyncio.create_task(self._refresh_rooms(global_discovery=False))
