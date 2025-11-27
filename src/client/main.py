#!/usr/bin/env python3
"""
Chat Client Application

Client application for connecting to the distributed chat system.
Provides a terminal-based user interface using the Textual framework.
"""

import logging
import sys

# Configure logging to file to avoid interfering with UI
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("chat_client.log", mode="a")],
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the chat client."""
    logger.info("Starting chat client...")

    try:
        from .ui import ChatApp

        app = ChatApp()
        app.run()
    except ImportError as e:
        print(f"Error: Could not import UI components: {e}")
        print("Make sure textual is installed: pip install textual")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()
