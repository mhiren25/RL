"""
MCP Client for FastAPI Gateway
Communicates with MCP server via stdio
"""
import asyncio
import json
from typing import Dict, Any, List, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Client for communicating with MCP server"""
    
    def __init__(self, server_script_path: str = "../mcp_server/server.py"):
        self.server_script_path = server_script_path
        self.session: Optional[ClientSession] = None
        self._lock = asyncio.Lock()
    
    async def connect(self):
        """Connect to MCP server"""
        async with self._lock:
            if self.session is not None:
                return
            
            # Create server parameters
            server_params = StdioServerParameters(
                command="python",
                args=[self.server_script_path],
                env=None
            )
            
            # Connect via stdio
            stdio_transport = await stdio_client(server_params)
            self.read_stream, self.write_stream = stdio_transport
            
            # Create session
            self.session = ClientSession(self.read_stream, self.write_stream)
            await self.session.initialize()
            
            print("✅ Connected to MCP server")
    
    async def close(self):
        """Close connection to MCP server"""
        async with self._lock:
            if self.session:
                await self.session.__aexit__(None, None, None)
                self.session = None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server
        
        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
        
        Returns:
            Tool response
        """
        if self.session is None:
            await self.connect()
        
        try:
            result = await self.session.call_tool(tool_name, arguments)
            
            # Parse response
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, 'text'):
                    return json.loads(content.text)
            
            return None
        
        except Exception as e:
            print(f"MCP tool call error ({tool_name}): {e}")
            raise
    
    async def parse_order(self, text: str) -> Dict[str, Any]:
        """Parse natural language order"""
        return await self.call_tool("parse_order", {"text": text})
    
    async def parse_trader_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse trader execution instructions"""
        args = {"text": text}
        if context:
            args["context"] = context
        return await self.call_tool("parse_trader_text", args)
    
    async def smart_suggestion(self, security: str, quantity: int, time_in_force: str = "DAY") -> Dict[str, Any]:
        """Get smart strategy suggestion"""
        return await self.call_tool("smart_suggestion", {
            "security": security,
            "quantity": quantity,
            "timeInForce": time_in_force
        })
    
    async def autocomplete(self, text: str) -> List[str]:
        """Get autocomplete suggestions"""
        return await self.call_tool("autocomplete", {"text": text})
    
    async def get_securities(self) -> List[Dict[str, Any]]:
        """Get all securities"""
        return await self.call_tool("get_securities", {})
    
    async def get_security(self, symbol: str) -> Dict[str, Any]:
        """Get specific security"""
        return await self.call_tool("get_security", {"symbol": symbol})


# Singleton instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """Get or create MCP client singleton"""
    global _mcp_client
    if _mcp_client is None:
        import os
        from pathlib import Path
        
        # Find server.py relative to this file
        current_dir = Path(__file__).parent
        server_path = current_dir.parent / "mcp_server" / "server.py"
        
        _mcp_client = MCPClient(str(server_path))
    
    return _mcp_client
