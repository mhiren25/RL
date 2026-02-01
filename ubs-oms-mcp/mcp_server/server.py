#!/usr/bin/env python3
"""
UBS OMS MCP Server
Exposes trading tools via Model Context Protocol
"""
import asyncio
import json
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from tools.order_parser import parse_order_tool
from tools.other_tools import (
    parse_trader_text_tool,
    autocomplete_tool,
    get_securities_tool,
    get_security_tool
)
from tools.strategy import smart_suggestion_tool

# Initialize MCP server
app = Server("ubs-oms-mcp")

# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

TOOLS = [
    Tool(
        name="parse_order",
        description="Parse natural language order text into structured format. "
                    "Extracts symbol, quantity, side (BUY/SELL), price, time-in-force, and requested strategy.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Natural language order description (e.g., 'buy 100 AAPL at 150')"
                }
            },
            "required": ["text"]
        }
    ),
    
    Tool(
        name="parse_trader_text",
        description="Parse trader execution instructions into structured algorithm details. "
                    "Identifies VWAP, TWAP, POV, MOC strategies and extracts parameters.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Trader instructions (e.g., 'VWAP Market Close', 'TWAP over 2 hours')"
                },
                "context": {
                    "type": "object",
                    "description": "Optional context (symbol, quantity)",
                    "properties": {
                        "symbol": {"type": "string"},
                        "quantity": {"type": "number"}
                    }
                }
            },
            "required": ["text"]
        }
    ),
    
    Tool(
        name="smart_suggestion",
        description="Get AI-powered execution strategy recommendation based on order details and trader history. "
                    "Analyzes order size vs ADV, volatility, and past preferences. "
                    "THIS TOOL SUPPORTS CORRECTION CAPTURE for offline learning.",
        inputSchema={
            "type": "object",
            "properties": {
                "security": {
                    "type": "string",
                    "description": "Security symbol (e.g., AAPL)"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of shares"
                },
                "timeInForce": {
                    "type": "string",
                    "enum": ["DAY", "GTC", "GTD", "FOK"],
                    "description": "Order time in force",
                    "default": "DAY"
                }
            },
            "required": ["security", "quantity"]
        }
    ),
    
    Tool(
        name="autocomplete",
        description="Get autocomplete suggestions for trader text input. "
                    "Provides common completions for VWAP, TWAP, POV, MOC strategies.",
        inputSchema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Partial text input (minimum 2 characters)"
                }
            },
            "required": ["text"]
        }
    ),
    
    Tool(
        name="get_securities",
        description="Get list of all available securities with current prices and market info.",
        inputSchema={
            "type": "object",
            "properties": {}
        }
    ),
    
    Tool(
        name="get_security",
        description="Get detailed information for a specific security by symbol.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Security symbol (e.g., AAPL, MSFT)"
                }
            },
            "required": ["symbol"]
        }
    )
]

# ============================================================================
# MCP HANDLERS
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools"""
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """
    Handle tool calls
    
    Args:
        name: Tool name
        arguments: Tool arguments
    
    Returns:
        Tool response as TextContent
    """
    try:
        result = None
        
        if name == "parse_order":
            result = await parse_order_tool(arguments["text"])
        
        elif name == "parse_trader_text":
            context = arguments.get("context", None)
            result = await parse_trader_text_tool(arguments["text"], context)
        
        elif name == "smart_suggestion":
            result = await smart_suggestion_tool(
                security=arguments["security"],
                quantity=arguments["quantity"],
                timeInForce=arguments.get("timeInForce", "DAY")
            )
        
        elif name == "autocomplete":
            result = await autocomplete_tool(arguments["text"])
        
        elif name == "get_securities":
            result = await get_securities_tool()
        
        elif name == "get_security":
            result = await get_security_tool(arguments["symbol"])
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]
        
        # Return result as JSON text
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
    
    except Exception as e:
        error_response = {
            "error": str(e),
            "tool": name,
            "arguments": arguments
        }
        return [TextContent(
            type="text",
            text=json.dumps(error_response, indent=2)
        )]


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run MCP server"""
    print("🚀 UBS OMS MCP Server starting...", flush=True)
    print("📊 Tools available:", flush=True)
    for tool in TOOLS:
        print(f"   - {tool.name}: {tool.description[:60]}...", flush=True)
    print("", flush=True)
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
