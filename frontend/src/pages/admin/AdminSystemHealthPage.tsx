/**
 * AdminSystemHealthPage - System Health Dashboard
 * Displays real-time health status of all core system components
 */

import { useState, useEffect, useCallback } from "react";
import {
    Card,
    Typography,
    Tag,
    Spin,
    Button,
    Progress,
    Descriptions,
    Empty,
    Banner,
} from "@douyinfe/semi-ui";
import {
    IconRefresh,
    IconTick,
    IconClose,
    IconAlertTriangle,
} from "@douyinfe/semi-icons";
import {
    Database,
    Server,
    Wifi,
    Radio,
    Brain,
    Clock,
    Cpu,
    HardDrive,
} from "lucide-react";
import { toast } from "sonner";
import {
    getDetailedHealth,
    formatUptime,
    type DetailedHealthCheck,
    type ComponentHealth,
} from "@/services/healthService";

const { Title, Text } = Typography;

// Icon mapping for each component
const COMPONENT_ICONS: Record<string, React.ReactNode> = {
    // Core Infrastructure
    database: <Database size={24} />,
    redis: <HardDrive size={24} />,
    mqtt: <Radio size={24} />,

    // AI Services
    openmemory: <Brain size={24} />,

    // Node.js Services
    mcp_endpoint: <Server size={24} />,
    phatnguoi_api: <Server size={24} />,
};

// Vietnamese labels for components
const COMPONENT_LABELS: Record<string, string> = {
    // Core Infrastructure
    database: "PostgreSQL Database",
    redis: "Redis Cache",
    mqtt: "MQTT Broker (EMQX)",

    // AI Services
    openmemory: "OpenMemory AI",

    // Node.js Services
    mcp_endpoint: "MCP Endpoint Server",
    phatnguoi_api: "Phạt Nguội API",
};

// Status badge colors
const getStatusTagColor = (status: string): "green" | "orange" | "red" | "grey" => {
    switch (status) {
        case "healthy":
            return "green";
        case "degraded":
            return "orange";
        case "unhealthy":
            return "red";
        default:
            return "grey";
    }
};

// Status icon
const getStatusIcon = (status: string) => {
    switch (status) {
        case "healthy":
            return <IconTick style={{ color: "#52c41a" }} />;
        case "degraded":
            return <IconAlertTriangle style={{ color: "#faad14" }} />;
        case "unhealthy":
            return <IconClose style={{ color: "#ff4d4f" }} />;
        default:
            return null;
    }
};

// Status text
const getStatusText = (status: string): string => {
    switch (status) {
        case "healthy":
            return "Hoạt động";
        case "degraded":
            return "Giảm hiệu năng";
        case "unhealthy":
            return "Không hoạt động";
        default:
            return "Không xác định";
    }
};

// Component Card
interface ComponentCardProps {
    name: string;
    health: ComponentHealth;
}

function ComponentCard({ name, health }: ComponentCardProps) {
    const icon = COMPONENT_ICONS[name] || <Server size={24} />;
    const label = COMPONENT_LABELS[name] || name;
    const statusColor = getStatusTagColor(health.status);

    return (
        <Card
            style={{
                borderLeft: `4px solid ${statusColor === "green"
                    ? "#52c41a"
                    : statusColor === "orange"
                        ? "#faad14"
                        : statusColor === "red"
                            ? "#ff4d4f"
                            : "#d9d9d9"
                    }`,
            }}
            bodyStyle={{ padding: "16px" }}
        >
            <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                    <div
                        className="p-2 rounded-lg"
                        style={{
                            backgroundColor:
                                statusColor === "green"
                                    ? "#f6ffed"
                                    : statusColor === "orange"
                                        ? "#fffbe6"
                                        : statusColor === "red"
                                            ? "#fff1f0"
                                            : "#fafafa",
                        }}
                    >
                        {icon}
                    </div>
                    <div>
                        <Text strong style={{ fontSize: 16 }}>
                            {label}
                        </Text>
                        <div className="flex items-center gap-2 mt-1">
                            <Tag color={statusColor} size="small">
                                {getStatusIcon(health.status)}
                                <span style={{ marginLeft: 4 }}>{getStatusText(health.status)}</span>
                            </Tag>
                            {health.latency_ms && (
                                <Text type="tertiary" size="small">
                                    {health.latency_ms.toFixed(1)}ms
                                </Text>
                            )}
                        </div>
                    </div>
                </div>
            </div>
            {health.details && (
                <div
                    className="mt-3 p-2 rounded"
                    style={{ backgroundColor: "var(--semi-color-fill-0)" }}
                >
                    <Text type="secondary" size="small">
                        {health.details}
                    </Text>
                </div>
            )}
            {health.last_check && (
                <div className="mt-2 flex items-center gap-1">
                    <Clock size={12} className="text-gray-400" />
                    <Text type="tertiary" size="small">
                        Kiểm tra lúc:{" "}
                        {new Date(health.last_check).toLocaleTimeString("vi-VN")}
                    </Text>
                </div>
            )}
        </Card>
    );
}

// Main Page Component
export function AdminSystemHealthPage() {
    const [healthData, setHealthData] = useState<DetailedHealthCheck | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
    const [autoRefresh, setAutoRefresh] = useState(() => {
        const saved = localStorage.getItem("admin_health_autoRefresh");
        return saved !== null ? saved === "true" : true;
    });

    const fetchHealth = useCallback(async () => {
        try {
            setError(null);
            const health = await getDetailedHealth();
            setHealthData(health);
            setLastRefresh(new Date());
        } catch (err: any) {
            console.error("Failed to fetch health data:", err);
            setError(err.response?.data?.detail || "Không thể tải dữ liệu sức khỏe hệ thống");
            toast.error("Không thể tải dữ liệu sức khỏe hệ thống");
        } finally {
            setLoading(false);
        }
    }, []);

    // Initial load
    useEffect(() => {
        fetchHealth();
    }, [fetchHealth]);

    // Auto-refresh every 30 seconds
    useEffect(() => {
        if (!autoRefresh) return;

        const interval = setInterval(() => {
            fetchHealth();
        }, 30000);

        return () => clearInterval(interval);
    }, [autoRefresh, fetchHealth]);

    // Calculate overall health stats
    const getHealthStats = () => {
        if (!healthData?.components) return { healthy: 0, degraded: 0, unhealthy: 0, total: 0 };

        const components = Object.values(healthData.components);
        return {
            healthy: components.filter((c) => c.status === "healthy").length,
            degraded: components.filter((c) => c.status === "degraded").length,
            unhealthy: components.filter((c) => c.status === "unhealthy").length,
            total: components.length,
        };
    };

    const stats = getHealthStats();
    const healthPercent = stats.total > 0 ? (stats.healthy / stats.total) * 100 : 0;

    if (loading && !healthData) {
        return (
            <div className="flex items-center justify-center h-96">
                <Spin size="large" tip="Đang kiểm tra sức khỏe hệ thống..." />
            </div>
        );
    }

    if (error && !healthData) {
        return (
            <div className="p-6">
                <Empty
                    title="Không thể tải dữ liệu"
                    description={error}
                    style={{ padding: 40 }}
                />
                <div className="flex justify-center mt-4">
                    <Button onClick={fetchHealth} icon={<IconRefresh />} theme="solid">
                        Thử lại
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div>
                    <Title heading={3} style={{ margin: 0 }}>
                        <Cpu size={28} className="inline-block mr-2" />
                        System Health Dashboard
                    </Title>
                    <Text type="secondary">
                        Giám sát trạng thái các thành phần core của hệ thống IOT AI
                    </Text>
                </div>
                <div className="flex items-center gap-3">
                    {lastRefresh && (
                        <Text type="tertiary" size="small">
                            Cập nhật: {lastRefresh.toLocaleTimeString("vi-VN")}
                        </Text>
                    )}
                    <Button
                        icon={<IconRefresh spin={loading} />}
                        onClick={fetchHealth}
                        loading={loading}
                    >
                        Làm mới
                    </Button>
                </div>
            </div>

            {/* Overall Status Banner */}
            {healthData && (
                <Banner
                    type={
                        healthData.status === "healthy"
                            ? "success"
                            : healthData.status === "degraded"
                                ? "warning"
                                : "danger"
                    }
                    description={
                        <div className="flex items-center justify-between">
                            <div>
                                <Text strong style={{ fontSize: 16 }}>
                                    Trạng thái tổng thể:{" "}
                                    {healthData.status === "healthy"
                                        ? "✅ Hệ thống hoạt động bình thường"
                                        : healthData.status === "degraded"
                                            ? "⚠️ Một số thành phần chưa sẵn sàng"
                                            : "❌ Hệ thống gặp sự cố"}
                                </Text>
                                <div className="flex gap-4 mt-2">
                                    <Text size="small">Version: {healthData.version}</Text>
                                    <Text size="small">Environment: {healthData.environment}</Text>
                                    <Text size="small">
                                        Uptime: {formatUptime(healthData.uptime_seconds)}
                                    </Text>
                                </div>
                            </div>
                            <Progress
                                percent={Math.round(healthPercent)}
                                type="circle"
                                size="small"
                                showInfo
                                stroke={
                                    healthPercent === 100
                                        ? "#52c41a"
                                        : healthPercent >= 70
                                            ? "#faad14"
                                            : "#ff4d4f"
                                }
                            />
                        </div>
                    }
                />
            )}

            {/* Stats Summary */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card bodyStyle={{ padding: 16, textAlign: "center" }}>
                    <Text type="tertiary">Tổng Components</Text>
                    <Title heading={2} style={{ margin: "8px 0 0 0" }}>
                        {stats.total}
                    </Title>
                </Card>
                <Card
                    bodyStyle={{ padding: 16, textAlign: "center" }}
                    style={{ borderLeft: "4px solid #52c41a" }}
                >
                    <Text type="tertiary">Hoạt động</Text>
                    <Title heading={2} style={{ margin: "8px 0 0 0", color: "#52c41a" }}>
                        {stats.healthy}
                    </Title>
                </Card>
                <Card
                    bodyStyle={{ padding: 16, textAlign: "center" }}
                    style={{ borderLeft: "4px solid #faad14" }}
                >
                    <Text type="tertiary">Giảm hiệu năng</Text>
                    <Title heading={2} style={{ margin: "8px 0 0 0", color: "#faad14" }}>
                        {stats.degraded}
                    </Title>
                </Card>
                <Card
                    bodyStyle={{ padding: 16, textAlign: "center" }}
                    style={{ borderLeft: "4px solid #ff4d4f" }}
                >
                    <Text type="tertiary">Không hoạt động</Text>
                    <Title heading={2} style={{ margin: "8px 0 0 0", color: "#ff4d4f" }}>
                        {stats.unhealthy}
                    </Title>
                </Card>
            </div>

            {/* Component Grid */}
            <Card
                title={
                    <div className="flex items-center gap-2">
                        <Server size={20} />
                        <span>Chi tiết Components ({stats.total})</span>
                    </div>
                }
                headerExtraContent={
                    <div className="flex items-center gap-2">
                        <input
                            type="checkbox"
                            id="autoRefresh"
                            checked={autoRefresh}
                            onChange={(e) => {
                                setAutoRefresh(e.target.checked);
                                localStorage.setItem("admin_health_autoRefresh", String(e.target.checked));
                            }}
                        />
                        <label htmlFor="autoRefresh" className="text-sm cursor-pointer">
                            Tự động làm mới (30s)
                        </label>
                    </div>
                }
                bodyStyle={{ padding: 16 }}
            >
                {healthData?.components ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Object.entries(healthData.components).map(([name, health]) => (
                            <ComponentCard key={name} name={name} health={health} />
                        ))}
                    </div>
                ) : (
                    <Empty title="Không có dữ liệu components" />
                )}
            </Card>

            {/* System Info */}
            {healthData && (
                <Card title="Thông tin hệ thống" bodyStyle={{ padding: 16 }}>
                    <Descriptions
                        data={[
                            { key: "Version", value: healthData.version },
                            { key: "Environment", value: healthData.environment },
                            { key: "Uptime", value: formatUptime(healthData.uptime_seconds) },
                            {
                                key: "Last Check",
                                value: new Date(healthData.timestamp).toLocaleString("vi-VN"),
                            },
                            { key: "Overall Status", value: getStatusText(healthData.status) },
                        ]}
                    />
                </Card>
            )}
        </div>
    );
}

export default AdminSystemHealthPage;
