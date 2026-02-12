"""
Client management service.

Manages ConversationClient instances with persistent connections to Claude Agent SDK.
"""
import asyncio
import os
import time
from typing import AsyncGenerator, Dict, Optional, TYPE_CHECKING

from server.log_config import logger
from server.storage import SQLiteStorage, conversation_storage, CONVERSATIONS_DIR
from server.config import CLAUDE_AGENT_SYSTEM_PROMPT, CHROME_DEVTOOLS_MCP_CONFIG

# Type checking imports
if TYPE_CHECKING:
    from claude_agent_sdk import ClaudeSDKClient

# Import tools and decorators (Claude Agent SDK required)
from claude_agent_sdk import (
    ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server, tool,
    AssistantMessage, TextBlock, ToolUseBlock, ResultMessage
)

# Import tools
from services.tools import _ALL_SDK_TOOLS

# Backward compatibility
OLD_JSONL_FILE = CONVERSATIONS_DIR / "conversations.jsonl"


class ConversationClient:
    """Wraps a ClaudeSDKClient with continuous message reception"""

    def __init__(self, client: "ClaudeSDKClient", conv_id: str):
        self.client = client
        self.conv_id = conv_id
        self.message_queue = asyncio.Queue()
        self.receive_task = None
        self.is_running = False
        self.total_cost_usd: float = 0.0

    async def start_receiving(self):
        """Start the background task to continuously receive messages"""
        self.is_running = True
        self.receive_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self):
        """Continuously receive messages and queue them"""
        try:
            async for message in self.client.receive_response():
                if not self.is_running:
                    break
                # Track cost from ResultMessage
                if isinstance(message, ResultMessage):
                    self.total_cost_usd = message.total_cost_usd or 0.0
                    logger.info(f"Cost: ${self.total_cost_usd:.4f}")
                await self.message_queue.put(message)
        except Exception as e:
            logger.error(f"Error in receive loop: {e}")
            if self.is_running:
                await self.message_queue.put({"error": str(e)})

    async def send_query(self, message: str):
        """Send a query to Claude"""
        await self.client.query(message)

    async def interrupt(self):
        """Interrupt the current query"""
        logger.info(f"Interrupting conversation: {self.conv_id}")
        try:
            await self.client.interrupt()
        except Exception as e:
            logger.error(f"Error interrupting client: {e}")
            # Put an error message in the queue
            await self.message_queue.put({"error": f"Interrupted: {str(e)}"})

    async def get_messages(self):
        """Get messages from the queue"""
        while True:
            try:
                msg = await asyncio.wait_for(self.message_queue.get(), timeout=60.0)
                # Yield SDK message objects directly - let routes.py handle type checks
                yield msg
            except asyncio.TimeoutError:
                # No messages for 60 seconds - send keepalive or check status
                yield {"type": "ping"}
            except Exception as e:
                logger.error(f"Error getting message: {e}")
                break

    async def close(self):
        """Close the client"""
        self.is_running = False
        if self.receive_task:
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass
        try:
            await self.client.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"Error closing client: {e}")


class ClientManager:
    """Manages persistent ConversationClient instances"""

    def __init__(self):
        self.conversations: Dict[str, ConversationClient] = {}
        self.sessions: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def load_from_storage(self):
        """Load conversations from SQLite storage"""
        # Migrate from JSONL if exists
        if OLD_JSONL_FILE.exists():
            logger.info(f"Found old JSONL file, migrating to SQLite...")
            count = await conversation_storage.migrate_from_jsonl(OLD_JSONL_FILE)
            logger.info(f"Migration complete: {count} conversations migrated")
        # Load from storage
        await conversation_storage.load()
        # Restore sessions from storage (but not the clients, they'll be recreated on demand)
        for conv in conversation_storage.get_all():
            conv_id = conv['id']
            if conv_id not in self.sessions:
                self.sessions[conv_id] = conv
        logger.debug(f"Restored {len(self.sessions)} conversations from storage")

    async def save_to_storage(self):
        """Save conversations to SQLite storage"""
        # Sync sessions to storage
        for conv_id, session in self.sessions.items():
            conversation_storage.set(session)
        await conversation_storage.save()

    async def get_or_create_client(self, conversation_id: Optional[str]) -> tuple[str, ConversationClient, bool]:
        """Get existing client or create new one. Returns (conv_id, client_wrapper, is_new)"""
        async with self._lock:
            # If conversation exists, return it
            if conversation_id and conversation_id in self.conversations:
                logger.info(f"Reusing existing client for: {conversation_id}")
                return conversation_id, self.conversations[conversation_id], False

            # Check if conversation exists in storage
            if conversation_id:
                stored_conv = conversation_storage.get(conversation_id)
                if stored_conv:
                    # Restore session data
                    self.sessions[conversation_id] = stored_conv

            # Create new client
            logger.info("Creating new ClaudeSDKClient")
            logger.info(f"ANTHROPIC_BASE_URL: {os.getenv('ANTHROPIC_BASE_URL', 'NOT SET')}")
            logger.info(f"ANTHROPIC_API_KEY: {'***' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")

            # Create MCP server
            myquant_server = create_sdk_mcp_server(
                name="myquant",
                version="1.0.0",
                tools=_ALL_SDK_TOOLS
            )

            options = ClaudeAgentOptions(
                mcp_servers={
                    "myquant": myquant_server,
                    "chrome-devtools": CHROME_DEVTOOLS_MCP_CONFIG
                },
                system_prompt=CLAUDE_AGENT_SYSTEM_PROMPT,
                permission_mode="bypassPermissions",
                max_turns=50,
                include_partial_messages=True,
            )

            raw_client = ClaudeSDKClient(options=options)
            await raw_client.__aenter__()

            new_conv_id = conversation_id or f"temp_{id(raw_client)}"

            # Create wrapper
            conv_client = ConversationClient(raw_client, new_conv_id)
            await conv_client.start_receiving()

            self.conversations[new_conv_id] = conv_client

            # Initialize or restore session data
            if new_conv_id in self.sessions:
                # Restored from storage
                session = self.sessions[new_conv_id]
                session['updated_at'] = int(time.time())
            else:
                # New session
                self.sessions[new_conv_id] = {
                    "id": new_conv_id,
                    "title": "New Conversation",
                    "created_at": int(time.time()),
                    "updated_at": int(time.time()),
                    "messages": []
                }

            # Save to storage
            await self.save_to_storage()

            return new_conv_id, conv_client, True

    async def close_client(self, conv_id: str):
        """Close a specific client"""
        if conv_id in self.conversations:
            await self.conversations[conv_id].close()
            del self.conversations[conv_id]
            # Save final state
            await self.save_to_storage()

    async def interrupt_client(self, conv_id: str) -> bool:
        """Interrupt a running conversation. Returns True if client exists and was interrupted."""
        if conv_id in self.conversations:
            await self.conversations[conv_id].interrupt()
            return True
        return False


# Global client manager
client_manager = ClientManager()


async def startup():
    """Startup handler - load conversations from storage"""
    logger.info("Loading conversations from storage...")
    await client_manager.load_from_storage()
    logger.info("Client service startup complete")
