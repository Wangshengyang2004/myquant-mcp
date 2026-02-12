"""
API routes for the agent page.

Handles all HTTP endpoints for the agent chat interface.
"""
import json
import os
import traceback
from typing import AsyncGenerator

from starlette.requests import Request
from starlette.responses import HTMLResponse, StreamingResponse, JSONResponse

from server.log_config import logger
from server.storage import conversation_storage
from services.client import client_manager
from utils.title import generate_conversation_title

# Import SDK message types (Claude Agent SDK required)
from claude_agent_sdk import (
    SystemMessage, UserMessage, AssistantMessage, ResultMessage,
    TextBlock, ToolUseBlock
)

# HTML cache
_AGENT_HTML_CACHE = None


def load_agent_html() -> str:
    """Load and cache agent.html"""
    global _AGENT_HTML_CACHE
    if _AGENT_HTML_CACHE is None:
        try:
            from pathlib import Path
            BASE_DIR = Path(__file__).resolve().parent.parent
            _AGENT_HTML_CACHE = (BASE_DIR / "server" / "agent.html").read_text(encoding="utf-8")
        except FileNotFoundError:
            _AGENT_HTML_CACHE = "<h1>MyQuant Agent</h1><p>agent.html not found.</p>"
    return _AGENT_HTML_CACHE


async def agent_home(request: Request) -> HTMLResponse:
    """Serve the agent chat UI"""
    return HTMLResponse(content=load_agent_html())


async def agent_api_conversations(request: Request) -> JSONResponse:
    """Get all conversations"""
    return JSONResponse({"conversations": conversation_storage.get_all()})


async def agent_api_conversation_get(request: Request) -> JSONResponse:
    """Get a specific conversation's messages"""
    conv_id = request.path_params.get("id")
    # Check both sessions and storage
    conv = client_manager.sessions.get(conv_id) or conversation_storage.get(conv_id)
    if not conv:
        return JSONResponse({"error": "Conversation not found"}, status_code=404)
    return JSONResponse({"conversation": conv})


async def agent_api_conversation_delete(request: Request) -> JSONResponse:
    """Delete a conversation"""
    conv_id = request.path_params.get("id")

    # Delete from sessions
    if conv_id in client_manager.sessions:
        del client_manager.sessions[conv_id]

    # Delete from storage
    conversation_storage.delete(conv_id)
    await conversation_storage.save()

    # Close client if exists
    if conv_id in client_manager.conversations:
        await client_manager.close_client(conv_id)

    return JSONResponse({"success": True})


async def agent_api_interrupt(request: Request) -> JSONResponse:
    """Interrupt a running conversation"""
    body = await request.json()
    conv_id = body.get("conversation_id")

    if not conv_id:
        return JSONResponse({"error": "conversation_id is required"}, status_code=400)

    success = await client_manager.interrupt_client(conv_id)

    if not success:
        return JSONResponse({"error": "Conversation not found or not active"}, status_code=404)

    return JSONResponse({"success": True, "message": "Conversation interrupted"})


async def agent_chat(request: Request) -> StreamingResponse | JSONResponse:
    """Handle chat requests with persistent client"""

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return JSONResponse({"error": "ANTHROPIC_API_KEY not set"}, status_code=503)

    try:
        body = await request.json()
        user_message = body.get("message", "")
        conversation_id = body.get("conversation_id")
    except Exception as e:
        return JSONResponse({"error": f"Invalid request: {str(e)}"}, status_code=400)

    if not user_message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    logger.info(f"Message: {user_message[:50]}..., conversation: {conversation_id}")

    async def stream_response() -> AsyncGenerator[str, None]:
        nonlocal conversation_id

        try:
            # Get or create client
            conv_id, conv_client, is_new = await client_manager.get_or_create_client(conversation_id)
            conversation_id = conv_id

            # Send the query
            await conv_client.send_query(user_message)

            # Store user message
            if conversation_id in client_manager.sessions:
                import uuid
                client_manager.sessions[conversation_id]["messages"].append({
                    "id": str(uuid.uuid4()),
                    "role": "user",
                    "content": user_message
                })

            # Stream messages from the queue
            async for msg in conv_client.get_messages():
                # Handle dict messages (ping, error, done)
                if isinstance(msg, dict):
                    if msg.get("type") == "ping":
                        # Keepalive - can be ignored
                        continue

                    if msg.get("error"):
                        yield f"event: error\n"
                        yield f"data: {json.dumps({'type': 'error', 'message': msg['error']})}\n\n"
                        break

                    if msg.get("type") == "done":
                        # End of this query response
                        yield f"event: done\n"
                        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
                        break

                # Handle SDK message objects
                if isinstance(msg, SystemMessage) and msg.subtype == "init":
                    session_id = msg.data.get("session_id")
                    logger.info(f"Session ID: {session_id}")

                    # Remap if needed
                    if session_id != conv_id:
                        if conv_id in client_manager.conversations:
                            client_manager.conversations[session_id] = client_manager.conversations.pop(conv_id)
                        if conv_id in client_manager.sessions:
                            client_manager.sessions[session_id] = client_manager.sessions.pop(conv_id)
                        conversation_id = session_id

                    # Initialize session if new
                    if session_id not in client_manager.sessions:
                        import time
                        client_manager.sessions[session_id] = {
                            "id": session_id,
                            "title": generate_conversation_title(user_message),
                            "created_at": int(time.time()),
                            "updated_at": int(time.time()),
                            "messages": []
                        }
                        logger.info(f"Created new session with title: {client_manager.sessions[session_id]['title']}")

                    yield f"event: session_id\n"
                    yield f"data: {json.dumps({'type': 'session_id', 'id': session_id})}\n\n"

                elif isinstance(msg, UserMessage):
                    # UserMessage means a new turn is starting
                    # Signal UI to close previous turn's tools
                    logger.info(f"UserMessage received, ending previous turn")
                    yield f"event: turn_end\n"
                    yield f"data: {json.dumps({'type': 'turn_end'})}\n\n"

                elif isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            text = block.text

                            # Store message
                            if conversation_id in client_manager.sessions:
                                import uuid
                                client_manager.sessions[conversation_id]["messages"].append({
                                    "id": str(uuid.uuid4()),
                                    "role": "assistant",
                                    "content": text
                                })
                                import time
                                client_manager.sessions[conversation_id]["updated_at"] = int(time.time())

                            yield f"event: message\n"
                            yield f"data: {json.dumps({'type': 'text', 'content': text})}\n\n"

                        elif isinstance(block, ToolUseBlock):
                            logger.info(f"ToolUse: {block.name}")

                            if conversation_id in client_manager.sessions:
                                import uuid
                                client_manager.sessions[conversation_id]["messages"].append({
                                    "id": str(uuid.uuid4()),
                                    "role": "tool",
                                    "name": block.name,
                                    "input": str(block.input)
                                })

                            yield f"event: tool_use\n"
                            yield f"data: {json.dumps({'type': 'tool', 'name': block.name, 'input': str(block.input)})}\n\n"

                elif isinstance(msg, ResultMessage):
                    # ResultMessage indicates the end of the entire conversation
                    logger.info(f"ResultMessage received, conversation ending. Total cost: ${msg.total_cost_usd:.4f}")

                    # Save to storage at end of conversation
                    await client_manager.save_to_storage()

                    yield f"event: done\n"
                    yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
                    break

        except Exception as e:
            logger.error(f"Error: {e}\n{traceback.format_exc()}")
            yield f"event: error\n"
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# Route handlers for import
ROUTES = [
    ("/agent", agent_home, ["GET"]),
    ("/agent/api/chat", agent_chat, ["POST"]),
    ("/agent/api/conversations", agent_api_conversations, ["GET"]),
    ("/agent/api/conversations/{id}", agent_api_conversation_get, ["GET"]),
    ("/agent/api/conversations/{id}", agent_api_conversation_delete, ["DELETE"]),
    ("/agent/api/interrupt", agent_api_interrupt, ["POST"]),
]


# Startup function
async def startup():
    """Startup handler - load conversations from storage"""
    from services.client import startup as client_startup
    await client_startup()
