#!/usr/bin/env python3
"""Entry point for Google MCP Server to be used with `mcp run server.py`"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from google_mcp_server.server import mcp

# Export for mcp run (FastMCP server)
app = mcp