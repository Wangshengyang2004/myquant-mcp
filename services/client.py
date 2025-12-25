"""
Client management service.

Manages ConversationClient instances with persistent connections to Claude Agent SDK.
"""
import asyncio
import time
from typing import AsyncGenerator, Dict, Optional, TYPE_CHECKING
from pathlib import Path

from log_config import logger
from storage import SQLiteStorage, conversation_storage, CONVERSATIONS_DIR

# Type checking imports
if TYPE_CHECKING:
    from claude_agent_sdk import ClaudeSDKClient

# Import tools and decorators
try:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server, tool
    CLAUDE_SDK_AVAILABLE = True
except ImportError as e:
    CLAUDE_SDK_AVAILABLE = False
    logger.warning(f"Claude Agent SDK not available: {e.__class__.__name__}: {e}")

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

    async def start_receiving(self):
        """Start the background task to continuously receive messages"""
        self.is_running = True
        self.receive_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self):
        """Continuously receive messages and queue them"""
        try:
            async for message in self.client.receive_messages():
                if not self.is_running:
                    break
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
        logger.info(f"Restored {len(self.sessions)} conversations from storage")

    async def save_to_storage(self):
        """Save conversations to SQLite storage"""
        # Sync sessions to storage
        for conv_id, session in self.sessions.items():
            conversation_storage.set(session)
        await conversation_storage.save()

    async def get_or_create_client(self, conversation_id: Optional[str]) -> tuple[str, ConversationClient, bool]:
        """Get existing client or create new one. Returns (conv_id, client_wrapper, is_new)"""
        if not CLAUDE_SDK_AVAILABLE:
            raise RuntimeError("Claude Agent SDK is not available")

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

            # Create MCP server
            myquant_server = create_sdk_mcp_server(
                name="myquant",
                version="1.0.0",
                tools=_ALL_SDK_TOOLS
            )

            options = ClaudeAgentOptions(
                mcp_servers={
                    "myquant": myquant_server,
                    "chrome-devtools": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "chrome-devtools-mcp@latest"]
                    }
                },
                system_prompt="""You are a helpful quantitative trading and financial analysis assistant with access to:

**MyQuant Tools** (Chinese Stock Market):
- history/history_n: Historical OHLCV data
- current: Real-time market snapshot
- get_symbols: List stocks/funds/indices
- stk_get_daily_valuation: PE/PB/PS valuation metrics
  - fields: 'pe_ttm,pe_mrq,pe_lyr,pb_lyr,pb_mrq,ps_ttm,ps_lyr'
- stk_get_daily_basic: Price, turnover, shares data
  - fields: 'tclose,turnrate,ttl_shr,circ_shr'
- stk_get_fundamentals_balance: Balance sheet (assets, liabilities, equity)
  - fields: 'mny_cptl,ttl_ast,ttl_liab,ttl_eqy_pcom,ttl_eqy'
- stk_get_fundamentals_income: Income statement (revenue, profit)
  - fields: 'ttl_inc_oper,inc_oper,net_prof,net_prof_pcom'
- stk_get_money_flow: Money flow analysis
- get_positions: Current trading positions
- get_cash: Account cash balance

**IMPORTANT - Field Names**: Use exact field names as shown above. Common errors:
- Use 'pb_lyr' NOT 'pb'
- Use 'tclose,turnrate,ttl_shr,circ_shr' NOT 'turnover_ratio,volume_ratio,total_share,float_share,total_mv,circ_mv'
- Use 'ttl_ast' NOT 'total_assets'
- Use 'ttl_inc_oper,net_prof' NOT 'total_revenue'

**Chrome DevTools** (Browser Automation):
- Navigate to websites, take screenshots, extract content

You can help users analyze stocks, get market data, evaluate fundamentals, and scrape financial websites.""",
                permission_mode="bypassPermissions",
                max_turns=50,
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
