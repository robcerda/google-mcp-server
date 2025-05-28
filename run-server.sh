#!/bin/bash
cd "$(dirname "$0")"
exec /opt/homebrew/bin/uv run mcp run server.py