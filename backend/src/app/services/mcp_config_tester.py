"""
MCP configuration tester service.

Tests MCP server connections and retrieves available tools.
"""

import asyncio
from typing import Any, Dict

from ..core.logger import get_logger
from ..schemas.server_mcp_config import ServerMCPConfigCreate, ServerMCPConfigRead

logger = get_logger(__name__)


class MCPConfigTester:
    """Tester for MCP server configurations."""

    # Default timeout for connections
    DEFAULT_TIMEOUT = 30

    @classmethod
    async def test_config(
        cls,
        config: ServerMCPConfigCreate | ServerMCPConfigRead,
    ) -> Dict[str, Any]:
        """
        Test MCP configuration by connecting to the server and retrieving tools.

        Args:
            config: MCP configuration to test

        Returns:
            Dict with test results:
                - success: bool
                - message: str
                - name: str (server name)
                - display_name: str
                - tools: list of tool definitions
                - error: optional error message
        """
        try:
            # Get config as dict
            config_dict = config.model_dump() if hasattr(config, "model_dump") else config

            server_name = config_dict.get("name", "unknown")
            display_name = config_dict.get("display_name") or server_name
            server_type = config_dict.get("type", "stdio")

            logger.debug(f"Testing MCP config: {server_name} (type: {server_type})")

            # Test based on transport type
            if server_type == "stdio":
                result = await cls._test_stdio(config_dict)
            elif server_type in ("sse", "http"):
                result = await cls._test_http(config_dict)
            else:
                return {
                    "success": False,
                    "message": f"Unknown transport type: {server_type}",
                    "name": server_name,
                    "display_name": display_name,
                    "tools": [],
                    "error": f"Unknown transport type: {server_type}",
                }

            # Add server info to result
            result["name"] = server_name
            result["display_name"] = display_name

            return result

        except Exception as e:
            logger.error(f"Error testing MCP config: {str(e)}")
            return {
                "success": False,
                "message": f"Test failed: {str(e)}",
                "name": config.name if hasattr(config, "name") else "unknown",
                "display_name": getattr(config, "display_name", None) or getattr(config, "name", "unknown"),
                "tools": [],
                "error": str(e),
            }

    @classmethod
    async def _test_stdio(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test stdio transport MCP server."""
        command = config.get("command")
        args = config.get("args", [])
        env = config.get("env", {})

        if not command:
            return {
                "success": False,
                "message": "Command not specified",
                "tools": [],
                "error": "Command is required for stdio transport",
            }

        try:
            import os
            import json

            # Prepare environment
            process_env = os.environ.copy()
            if env:
                process_env.update(env)

            # Try to connect to MCP server using subprocess
            # Send initialize request and get tools
            cmd_list = [command] + (args if args else [])
            
            logger.debug(f"Testing stdio MCP: {' '.join(cmd_list)}")

            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd_list,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
            )

            # Send MCP initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "xiaozhi-tester", "version": "1.0.0"},
                },
            }
            
            request_line = json.dumps(init_request) + "\n"
            process.stdin.write(request_line.encode())
            await process.stdin.drain()

            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=cls.DEFAULT_TIMEOUT
                )
                
                if response_line:
                    init_response = json.loads(response_line.decode())
                    logger.debug(f"MCP init response: {init_response}")
                    
                    # Send tools/list request
                    tools_request = {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                        "params": {},
                    }
                    
                    request_line = json.dumps(tools_request) + "\n"
                    process.stdin.write(request_line.encode())
                    await process.stdin.drain()
                    
                    # Read tools response
                    tools_response_line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=cls.DEFAULT_TIMEOUT
                    )
                    
                    if tools_response_line:
                        tools_response = json.loads(tools_response_line.decode())
                        tools = tools_response.get("result", {}).get("tools", [])
                        
                        # Terminate process
                        process.terminate()
                        
                        return {
                            "success": True,
                            "message": f"Connected successfully. Found {len(tools)} tools.",
                            "tools": tools,
                            "error": None,
                        }

            except asyncio.TimeoutError:
                process.terminate()
                return {
                    "success": False,
                    "message": "Connection timeout",
                    "tools": [],
                    "error": f"Timeout after {cls.DEFAULT_TIMEOUT}s",
                }

            # If we get here without getting tools, try stderr
            process.terminate()
            stderr = await process.stderr.read()
            
            return {
                "success": False,
                "message": "No response from MCP server",
                "tools": [],
                "error": stderr.decode() if stderr else "No response received",
            }

        except FileNotFoundError:
            return {
                "success": False,
                "message": f"Command not found: {command}",
                "tools": [],
                "error": f"Command '{command}' not found. Make sure it is installed.",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "tools": [],
                "error": str(e),
            }

    @classmethod
    async def _test_http(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test HTTP/SSE transport MCP server."""
        url = config.get("url")
        headers = config.get("headers", {})

        if not url:
            return {
                "success": False,
                "message": "URL not specified",
                "tools": [],
                "error": "URL is required for HTTP/SSE transport",
            }

        try:
            import httpx

            # Try to connect to HTTP MCP server
            async with httpx.AsyncClient(timeout=cls.DEFAULT_TIMEOUT) as client:
                # First, try to get server info / tools
                # SSE endpoint typically uses /sse or /events
                # HTTP endpoint uses /mcp or similar

                # Try common endpoints
                endpoints_to_try = [
                    url,  # Base URL
                    f"{url.rstrip('/')}/tools",
                    f"{url.rstrip('/')}/mcp",
                ]

                for endpoint in endpoints_to_try:
                    try:
                        # Try POST with tools/list request
                        response = await client.post(
                            endpoint,
                            headers=headers,
                            json={
                                "jsonrpc": "2.0",
                                "id": 1,
                                "method": "tools/list",
                                "params": {},
                            },
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            tools = data.get("result", {}).get("tools", [])
                            
                            return {
                                "success": True,
                                "message": f"Connected successfully. Found {len(tools)} tools.",
                                "tools": tools,
                                "error": None,
                            }
                    except Exception:
                        continue

                # If POST didn't work, try GET for health check
                try:
                    response = await client.get(url, headers=headers)
                    if response.status_code == 200:
                        return {
                            "success": True,
                            "message": "Server is reachable but could not list tools",
                            "tools": [],
                            "error": None,
                        }
                except Exception:
                    pass

                return {
                    "success": False,
                    "message": "Could not connect to MCP server",
                    "tools": [],
                    "error": "Server not responding or invalid endpoint",
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "message": "Connection timeout",
                "tools": [],
                "error": f"Timeout after {cls.DEFAULT_TIMEOUT}s",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "tools": [],
                "error": str(e),
            }
