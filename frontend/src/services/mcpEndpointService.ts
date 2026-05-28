import { apiClient } from "@/config/axios-instance";

export interface MCPServerInfo {
  message: string;
  version: string;
  status: string;
}

export interface MCPHealthResponse {
  status: string;
  connections?: {
    tool_connections: number;
    robot_connections: number;
    total_connections: number;
    robot_connections_by_agent: Record<string, number>;
  };
  error?: string;
}

export interface MCPStatsResponse {
  tool_connections: number;
  robot_connections: number;
  total_connections: number;
  robot_connections_by_agent: Record<string, number>;
}

export interface MCPConfigResponse {
  key: string | null;
  websocket_tool_url: string;
  websocket_robot_url: string;
  health_url: string;
}

export interface MCPStatusResponse {
  available: boolean;
  version: string | null;
  timestamp: string;
}

export const mcpEndpointService = {
  /**
   * Get MCP server basic info (requires admin)
   */
  getInfo: async (): Promise<MCPServerInfo> => {
    const response = await apiClient.get<MCPServerInfo>("/mcp-endpoint/info");
    return response.data;
  },

  /**
   * Get MCP health status with connection details (requires admin)
   */
  getHealth: async (): Promise<MCPHealthResponse> => {
    const response = await apiClient.get<MCPHealthResponse>("/mcp-endpoint/health");
    return response.data;
  },

  /**
   * Get MCP connection statistics (requires admin)
   */
  getStats: async (): Promise<MCPStatsResponse> => {
    const response = await apiClient.get<MCPStatsResponse>("/mcp-endpoint/stats");
    return response.data;
  },

  /**
   * Get MCP configuration URLs (requires admin)
   */
  getConfig: async (): Promise<MCPConfigResponse> => {
    const response = await apiClient.get<MCPConfigResponse>("/mcp-endpoint/config");
    return response.data;
  },

  /**
   * Simple status check (public)
   */
  getStatus: async (): Promise<MCPStatusResponse> => {
    const response = await apiClient.get<MCPStatusResponse>("/mcp-endpoint/status");
    return response.data;
  },
};

export default mcpEndpointService;
