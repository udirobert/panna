"""Foundry Toolbox (MCP) integration — stub."""

from __future__ import annotations


class ToolboxClient:
    def __init__(self, endpoint: str = "") -> None:
        self.endpoint = endpoint

    def call_tool(self, name: str, args: dict) -> dict:
        return {"tool": name, "result": "stub", "args": args}
