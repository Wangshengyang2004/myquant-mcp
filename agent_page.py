#!/usr/bin/env python3
"""
Agent Chat Page - Claude Desktop-like interface with persistent client connections

This module has been refactored into smaller, more maintainable modules:
- utils/title.py - Conversation title generation
- services/tools.py - SDK tools creation
- services/client.py - Client management (ConversationClient, ClientManager)
- api/routes.py - API route handlers
- storage.py - SQLite storage layer

Import routes and startup function from api.routes for integration.
"""
from pathlib import Path

# Import routes and startup from the refactored modules
# Import routes and startup from the refactored modules
from api.routes import ROUTES, startup

# Alias for backward compatibility if needed, though app.py uses 'startup'
agent_startup = startup

# For backward compatibility, expose the main components
__all__ = ["ROUTES", "startup", "agent_startup"]
