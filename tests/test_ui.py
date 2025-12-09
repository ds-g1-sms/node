"""
Tests for the Chat Client UI

Tests for the Textual-based user interface components.
"""

import pytest

from src.client.ui.app import (
    ChatApp,
    ConnectionScreen,
    RoomListScreen,
    CreateRoomDialog,
    ChatScreen,
    MessageDisplay,
    SystemMessage,
)


class TestUIComponentsCanBeImported:
    """Tests to verify UI components can be imported and created."""

    def test_chat_app_can_be_imported(self):
        """Test that ChatApp can be imported."""
        assert ChatApp is not None

    def test_connection_screen_can_be_imported(self):
        """Test that ConnectionScreen can be imported."""
        assert ConnectionScreen is not None

    def test_room_list_screen_can_be_imported(self):
        """Test that RoomListScreen can be imported."""
        assert RoomListScreen is not None

    def test_create_room_dialog_can_be_imported(self):
        """Test that CreateRoomDialog can be imported."""
        assert CreateRoomDialog is not None

    def test_chat_screen_can_be_imported(self):
        """Test that ChatScreen can be imported."""
        assert ChatScreen is not None

    def test_message_display_can_be_imported(self):
        """Test that MessageDisplay can be imported."""
        assert MessageDisplay is not None

    def test_system_message_can_be_imported(self):
        """Test that SystemMessage can be imported."""
        assert SystemMessage is not None


class TestChatAppInitialization:
    """Tests for ChatApp initialization."""

    def test_chat_app_can_be_instantiated(self):
        """Test that ChatApp can be instantiated."""
        app = ChatApp()
        assert app is not None

    def test_chat_app_initial_state(self):
        """Test ChatApp initial state."""
        app = ChatApp()
        assert app.client is None
        assert app.username is None
        assert app.current_room_id is None
        assert app.current_room_name is None
        assert app.current_room_description is None
        assert app.current_members == []
        assert app._current_screen == "connection"

    def test_chat_app_has_bindings(self):
        """Test that ChatApp has keybindings defined."""
        app = ChatApp()
        assert hasattr(app, "BINDINGS")
        assert len(app.BINDINGS) > 0

    def test_chat_app_has_css(self):
        """Test that ChatApp has CSS defined."""
        app = ChatApp()
        assert hasattr(app, "CSS")
        assert len(app.CSS) > 0


class TestMessageDisplayWidget:
    """Tests for MessageDisplay widget."""

    def test_message_display_stores_data(self):
        """Test that MessageDisplay stores message data."""
        msg = MessageDisplay(
            username="test_user",
            message_content="Hello, World!",
            timestamp="2025-11-25T12:00:00Z",
            is_own_message=False,
        )
        assert msg.msg_username == "test_user"
        assert msg.msg_content == "Hello, World!"
        assert msg.msg_timestamp == "2025-11-25T12:00:00Z"
        assert msg.is_own_message is False

    def test_message_display_own_message(self):
        """Test MessageDisplay with own message flag."""
        msg = MessageDisplay(
            username="me",
            message_content="My message",
            timestamp="2025-11-25T12:00:00Z",
            is_own_message=True,
        )
        assert msg.is_own_message is True


class TestSystemMessageWidget:
    """Tests for SystemMessage widget."""

    def test_system_message_stores_data(self):
        """Test that SystemMessage stores message data."""
        msg = SystemMessage(message="User joined", message_type="info")
        assert msg.message == "User joined"
        assert msg.message_type == "info"

    def test_system_message_default_type(self):
        """Test SystemMessage default message type."""
        msg = SystemMessage(message="Some notification")
        assert msg.message_type == "info"

    def test_system_message_warning_type(self):
        """Test SystemMessage with warning type."""
        msg = SystemMessage(message="Warning!", message_type="warning")
        assert msg.message_type == "warning"

    def test_system_message_error_type(self):
        """Test SystemMessage with error type."""
        msg = SystemMessage(message="Error occurred", message_type="error")
        assert msg.message_type == "error"


class TestUIPackageExports:
    """Tests for UI package exports."""

    def test_ui_package_exports_chat_app(self):
        """Test that UI package exports ChatApp."""
        from src.client.ui import ChatApp as ImportedChatApp

        assert ImportedChatApp is ChatApp
