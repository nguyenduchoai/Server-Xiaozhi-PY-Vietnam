/**
 * MCP Endpoint Page - Semi Design implementation
 */

import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
  Server,
  Activity,
  Wifi,
  WifiOff,
  RefreshCw,
  Settings,
  Users,
  Wrench,
  Copy,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink,
} from "lucide-react";

import { PageHead } from "@/components";
import { Button, Card, Banner, Typography, Spin } from "@douyinfe/semi-ui";
import { cn } from "@/lib/utils";
import mcpEndpointService, {
  type MCPServerInfo,
  type MCPHealthResponse,
  type MCPStatsResponse,
  type MCPConfigResponse,
} from "@/services/mcpEndpointService";

const { Text } = Typography;

type ConnectionStatus = "loading" | "connected" | "disconnected" | "error";

export function McpEndpointPage() {
  useTranslation(["common"]);

  const [status, setStatus] = useState<ConnectionStatus>("loading");
  const [serverInfo, setServerInfo] = useState<MCPServerInfo | null>(null);
  const [health, setHealth] = useState<MCPHealthResponse | null>(null);
  const [stats, setStats] = useState<MCPStatsResponse | null>(null);
  const [config, setConfig] = useState<MCPConfigResponse | null>(null);
  const [error, setError] = useState<string>("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setIsRefreshing(true);
    setError("");

    try {
      const [infoResult, healthResult, statsResult, configResult] = await Promise.allSettled([
        mcpEndpointService.getInfo(),
        mcpEndpointService.getHealth(),
        mcpEndpointService.getStats(),
        mcpEndpointService.getConfig(),
      ]);

      if (infoResult.status === "fulfilled") {
        setServerInfo(infoResult.value);
        setStatus("connected");
      } else {
        setStatus("disconnected");
      }

      if (healthResult.status === "fulfilled") {
        setHealth(healthResult.value);
        if (healthResult.value.status === "error" || healthResult.value.error) {
          setError(healthResult.value.error || "Health check failed");
        }
      }

      if (statsResult.status === "fulfilled") {
        setStats(statsResult.value);
      }

      if (configResult.status === "fulfilled") {
        setConfig(configResult.value);
      }

      setLastUpdated(new Date());
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Failed to fetch MCP data");
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const copyToClipboard = async (text: string, field: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedField(field);
      setTimeout(() => setCopiedField(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const renderStatusBadge = () => {
    const statusConfig = {
      loading: { icon: Loader2, color: "text-gray-500", bg: "bg-gray-100", label: "Đang tải..." },
      connected: { icon: Wifi, color: "text-green-500", bg: "bg-green-100", label: "Đang hoạt động" },
      disconnected: { icon: WifiOff, color: "text-red-500", bg: "bg-red-100", label: "Không kết nối" },
      error: { icon: AlertCircle, color: "text-yellow-500", bg: "bg-yellow-100", label: "Lỗi" },
    };

    const cfg = statusConfig[status];
    const Icon = cfg.icon;
    const isAnimating = status === "loading";

    return (
      <div className={cn("inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium", cfg.bg, cfg.color)}>
        <Icon className={cn("h-4 w-4", isAnimating && "animate-spin")} />
        {cfg.label}
      </div>
    );
  };

  const StatCard = ({ title, value, icon: Icon, description }: { title: string; value: number | string; icon: React.ElementType; description?: string; }) => (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-2">
        <Text type="tertiary" size="small">{title}</Text>
        <Icon className="h-4 w-4 text-gray-400" />
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {description && <Text type="tertiary" size="small" className="mt-1 block">{description}</Text>}
    </Card>
  );

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <PageHead
          title="MCP Endpoint Server"
          description="Quản lý và giám sát MCP connections"
        />
        <div className="flex items-center gap-4">
          {renderStatusBadge()}
          <Button
            icon={<RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />}
            onClick={fetchData}
            disabled={isRefreshing}
          >
            Làm mới
          </Button>
        </div>
      </div>

      {error && (
        <Banner type="danger" description={error} closeIcon={null} />
      )}

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Tổng kết nối" value={stats?.total_connections ?? 0} icon={Activity} description="Tất cả WebSocket connections" />
        <StatCard title="Tool Connections" value={stats?.tool_connections ?? 0} icon={Wrench} description="MCP Tools đang kết nối" />
        <StatCard title="Robot Connections" value={stats?.robot_connections ?? 0} icon={Users} description="Thiết bị ESP32 đang kết nối" />
        <StatCard title="Phiên bản" value={serverInfo?.version ?? "N/A"} icon={Server} description={serverInfo?.status ?? "Unknown"} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Server Info Card */}
        <Card title={<div className="flex items-center gap-2"><Server className="h-5 w-5" />Thông tin Server</div>}>
          <Text type="tertiary" size="small" className="block mb-4">Chi tiết về MCP Endpoint Server</Text>
          <div className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b">
              <Text type="tertiary" size="small">Trạng thái</Text>
              <Text className={health?.status === "success" ? "text-green-500" : "text-yellow-500"}>
                {health?.status ?? "Unknown"}
              </Text>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <Text type="tertiary" size="small">Phiên bản</Text>
              <code className="text-sm">{serverInfo?.version ?? "N/A"}</code>
            </div>
            <div className="flex justify-between items-center py-2 border-b">
              <Text type="tertiary" size="small">Message</Text>
              <Text size="small">{serverInfo?.message ?? "N/A"}</Text>
            </div>
            {lastUpdated && (
              <div className="flex justify-between items-center py-2">
                <Text type="tertiary" size="small">Cập nhật lần cuối</Text>
                <Text size="small">{lastUpdated.toLocaleTimeString()}</Text>
              </div>
            )}
          </div>
        </Card>

        {/* Configuration Card */}
        <Card title={<div className="flex items-center gap-2"><Settings className="h-5 w-5" />Cấu hình kết nối</div>}>
          <Text type="tertiary" size="small" className="block mb-4">WebSocket URLs để kết nối MCP</Text>
          {config ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Text strong size="small">Tool WebSocket URL</Text>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-md text-xs font-mono truncate">
                    {config.websocket_tool_url}
                  </code>
                  <Button theme="borderless" icon={copiedField === "tool" ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />} onClick={() => copyToClipboard(config.websocket_tool_url, "tool")} />
                </div>
                <Text type="tertiary" size="small">Dùng cho MCP Tools kết nối</Text>
              </div>

              <div className="space-y-2">
                <Text strong size="small">Robot WebSocket URL</Text>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-md text-xs font-mono truncate">
                    {config.websocket_robot_url}
                  </code>
                  <Button theme="borderless" icon={copiedField === "robot" ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />} onClick={() => copyToClipboard(config.websocket_robot_url, "robot")} />
                </div>
                <Text type="tertiary" size="small">Dùng cho thiết bị ESP32/Robot kết nối</Text>
              </div>

              <div className="space-y-2">
                <Text strong size="small">Health Check URL</Text>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-md text-xs font-mono truncate">
                    {config.health_url}
                  </code>
                  <Button theme="borderless" icon={copiedField === "health" ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />} onClick={() => copyToClipboard(config.health_url, "health")} />
                  <a href={config.health_url} target="_blank" rel="noopener noreferrer">
                    <Button theme="borderless" icon={<ExternalLink className="h-4 w-4" />} />
                  </a>
                </div>
              </div>

              {config.key && (
                <div className="space-y-2">
                  <Text strong size="small">API Key</Text>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-md text-xs font-mono truncate">
                      {config.key.substring(0, 8)}...{config.key.substring(config.key.length - 8)}
                    </code>
                    <Button theme="borderless" icon={copiedField === "key" ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />} onClick={() => copyToClipboard(config.key!, "key")} />
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center py-8 text-gray-500">
              <Spin className="mr-2" />
              Đang tải cấu hình...
            </div>
          )}
        </Card>
      </div>

      {/* Robot Connections by Agent */}
      {stats && Object.keys(stats.robot_connections_by_agent).length > 0 && (
        <Card title={<div className="flex items-center gap-2"><Users className="h-5 w-5" />Kết nối theo Agent</div>}>
          <Text type="tertiary" size="small" className="block mb-4">Phân bố thiết bị kết nối theo từng Agent ID</Text>
          <div className="grid gap-2">
            {Object.entries(stats.robot_connections_by_agent).map(([agentId, count]) => (
              <div key={agentId} className="flex items-center justify-between py-2 px-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <code className="text-sm">{agentId}</code>
                <span className="text-sm font-medium bg-blue-100 text-blue-600 px-2 py-0.5 rounded">
                  {count as number} kết nối
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Info Alert */}
      <Banner
        type="info"
        title="Hướng dẫn sử dụng"
        description={
          <div className="text-sm space-y-2">
            <p><strong>MCP Endpoint Server</strong> là dịch vụ trung gian cho phép các MCP Tools giao tiếp với thiết bị ESP32/Robot thông qua WebSocket.</p>
            <ul className="list-disc list-inside space-y-1 text-gray-600">
              <li><strong>Tool URL</strong>: Dùng cho MCP server (như n8n, Langchain) kết nối để cung cấp tools</li>
              <li><strong>Robot URL</strong>: Dùng cho firmware ESP32 kết nối để nhận lệnh từ tools</li>
              <li>Tất cả kết nối cần token xác thực (encrypted agentId)</li>
            </ul>
          </div>
        }
        closeIcon={null}
      />
    </div>
  );
}

export default McpEndpointPage;
