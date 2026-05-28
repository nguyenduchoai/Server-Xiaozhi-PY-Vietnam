import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
  Card,
  Typography,
  Spin,
  Tag,
  Table,
  Progress,
  Empty,
  Button,
  Modal,
  Form,
  Select,
  InputNumber,
  Switch,
  Tooltip,
  Tabs,
  TabPane,
} from "@douyinfe/semi-ui";
import {
  IconServer,
  IconDesktop,
  IconRefresh,
  IconActivity,
  IconShield,
} from "@douyinfe/semi-icons";
import type {
  OTAStats,
  LicenseInfo,
  DeviceLicenseUpdate,
} from "@/services/otaDashboardService";
import {
  otaDashboardService,
  DEFAULT_FEATURES,
  FEATURE_LABELS,
  LICENSE_TYPE_LABELS,
} from "@/services/otaDashboardService";

const { Text, Title } = Typography;

// ============ Stat Card Component ============

function StatCard({
  icon,
  title,
  value,
  subtitle,
  color,
}: {
  icon: React.ReactNode;
  title: string;
  value: number | string;
  subtitle?: string;
  color: string;
}) {
  return (
    <div
      style={{
        background: `linear-gradient(135deg, ${color}15 0%, ${color}08 100%)`,
        border: `1px solid ${color}30`,
        borderRadius: 16,
        padding: "20px 24px",
        flex: 1,
        minWidth: 200,
        transition: "transform 0.2s, box-shadow 0.2s",
        cursor: "default",
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
        (e.currentTarget as HTMLElement).style.boxShadow = `0 8px 24px ${color}20`;
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.transform = "";
        (e.currentTarget as HTMLElement).style.boxShadow = "";
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 12,
            background: `linear-gradient(135deg, ${color} 0%, ${color}CC 100%)`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontSize: 18,
          }}
        >
          {icon}
        </div>
        <Text type="tertiary" size="small">
          {title}
        </Text>
      </div>
      <Title heading={2} style={{ margin: 0, color }}>
        {value}
      </Title>
      {subtitle && (
        <Text size="small" type="tertiary" style={{ marginTop: 4 }}>
          {subtitle}
        </Text>
      )}
    </div>
  );
}

// ============ Activity Chart (CSS only) ============

function ActivityChart({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data);
  const maxVal = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 120, padding: "0 8px" }}>
      {entries.map(([date, count]) => {
        const height = Math.max((count / maxVal) * 100, 4);
        const label = date.slice(5); // MM-DD
        return (
          <Tooltip key={date} content={`${date}: ${count} thiết bị`}>
            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 4,
              }}
            >
              <Text size="small" type="tertiary">
                {count}
              </Text>
              <div
                style={{
                  width: "100%",
                  maxWidth: 48,
                  height: `${height}px`,
                  borderRadius: "8px 8px 4px 4px",
                  background: "linear-gradient(180deg, #6366F1 0%, #818CF8 100%)",
                  transition: "height 0.3s ease",
                }}
              />
              <Text size="small" type="tertiary">
                {label}
              </Text>
            </div>
          </Tooltip>
        );
      })}
    </div>
  );
}

// ============ Board Distribution ============

function BoardDistribution({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  const colors = ["#6366F1", "#EC4899", "#F59E0B", "#10B981", "#3B82F6", "#8B5CF6"];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {Object.entries(data).map(([board, count], i) => (
        <div key={board}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <Text size="small">{board}</Text>
            <Text size="small" type="tertiary">
              {count} ({Math.round((count / total) * 100)}%)
            </Text>
          </div>
          <Progress
            percent={Math.round((count / total) * 100)}
            showInfo={false}
            stroke={colors[i % colors.length]}
            size="small"
          />
        </div>
      ))}
    </div>
  );
}

// ============ License Editor Dialog ============

function LicenseEditorDialog({
  visible,
  deviceId,
  deviceName,
  onClose,
  onSaved,
}: {
  visible: boolean;
  deviceId: string;
  deviceName: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [licenseInfo, setLicenseInfo] = useState<LicenseInfo | null>(null);
  const [licenseType, setLicenseType] = useState("unlimited");
  const [licenseValue, setLicenseValue] = useState<number | null>(null);

  useEffect(() => {
    if (visible && deviceId) {
      setLoading(true);
      otaDashboardService
        .getDeviceLicense(deviceId)
        .then((info) => {
          setLicenseInfo(info);
          setLicenseType(info.license_type);
        })
        .catch((err) => toast.error("Không thể tải license: " + err.message))
        .finally(() => setLoading(false));
    }
  }, [visible, deviceId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const data: DeviceLicenseUpdate = {
        license_type: licenseType,
        license_value: licenseValue,
      };
      await otaDashboardService.updateDeviceLicense(deviceId, data);
      toast.success("Đã cập nhật license!");
      onSaved();
      onClose();
    } catch (err: any) {
      toast.error("Lỗi cập nhật: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={`🔑 License — ${deviceName}`}
      visible={visible}
      onCancel={onClose}
      onOk={handleSave}
      okText="Lưu"
      cancelText="Hủy"
      confirmLoading={saving}
      style={{ maxWidth: 480 }}
    >
      {loading ? (
        <div style={{ textAlign: "center", padding: 32 }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          {licenseInfo && (
            <div
              style={{
                padding: 16,
                borderRadius: 12,
                background: licenseInfo.is_valid
                  ? "rgba(16, 185, 129, 0.08)"
                  : "rgba(239, 68, 68, 0.08)",
                border: `1px solid ${
                  licenseInfo.is_valid ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"
                }`,
                marginBottom: 16,
              }}
            >
              <Tag color={licenseInfo.is_valid ? "green" : "red"} size="large">
                {licenseInfo.is_valid ? "✅ Có hiệu lực" : "❌ Hết hạn"}
              </Tag>
              <Text style={{ marginLeft: 8 }}>{licenseInfo.message}</Text>
            </div>
          )}

          <Form layout="vertical">
            <Form.Slot label="Loại License">
              <Select
                value={licenseType}
                onChange={(val) => setLicenseType(val as string)}
                style={{ width: "100%" }}
              >
                {Object.entries(LICENSE_TYPE_LABELS).map(([key, label]) => (
                  <Select.Option key={key} value={key}>
                    {label}
                  </Select.Option>
                ))}
              </Select>
            </Form.Slot>

            {(licenseType === "days" || licenseType === "months" || licenseType === "years") && (
              <Form.Slot label={`Giá trị (${licenseType})`}>
                <InputNumber
                  value={licenseValue ?? undefined}
                  onChange={(val) => setLicenseValue(val as number)}
                  min={1}
                  max={9999}
                  style={{ width: "100%" }}
                />
              </Form.Slot>
            )}
          </Form>
        </>
      )}
    </Modal>
  );
}

// ============ Features Editor Dialog ============

function FeaturesEditorDialog({
  visible,
  deviceId,
  deviceName,
  onClose,
  onSaved,
}: {
  visible: boolean;
  deviceId: string;
  deviceName: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [features, setFeatures] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (visible && deviceId) {
      setLoading(true);
      otaDashboardService
        .getDeviceFeatures(deviceId)
        .then((data) => {
          // Merge defaults with device features
          const merged = { ...DEFAULT_FEATURES, ...data.device_features };
          setFeatures(merged);
        })
        .catch((err) => toast.error("Không thể tải features: " + err.message))
        .finally(() => setLoading(false));
    }
  }, [visible, deviceId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await otaDashboardService.updateDeviceFeatures(deviceId, { features });
      toast.success("Đã cập nhật tính năng!");
      onSaved();
      onClose();
    } catch (err: any) {
      toast.error("Lỗi cập nhật: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={`⚙️ Tính năng — ${deviceName}`}
      visible={visible}
      onCancel={onClose}
      onOk={handleSave}
      okText="Lưu"
      cancelText="Hủy"
      confirmLoading={saving}
      style={{ maxWidth: 480 }}
    >
      {loading ? (
        <div style={{ textAlign: "center", padding: 32 }}>
          <Spin size="large" />
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 12,
          }}
        >
          {Object.entries(FEATURE_LABELS).map(([key, label]) => (
            <div
              key={key}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "8px 12px",
                borderRadius: 8,
                background: features[key]
                  ? "rgba(16, 185, 129, 0.06)"
                  : "rgba(107, 114, 128, 0.06)",
                border: `1px solid ${
                  features[key] ? "rgba(16, 185, 129, 0.2)" : "rgba(107, 114, 128, 0.15)"
                }`,
              }}
            >
              <Text size="small">{label}</Text>
              <Switch
                size="small"
                checked={features[key] ?? true}
                onChange={(val) =>
                  setFeatures((prev) => ({ ...prev, [key]: val }))
                }
              />
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

// ============ Main OTA Dashboard Page ============

export default function OTADashboardPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<OTAStats | null>(null);
  const [licenseModal, setLicenseModal] = useState<{
    visible: boolean;
    deviceId: string;
    deviceName: string;
  }>({ visible: false, deviceId: "", deviceName: "" });
  const [featuresModal, setFeaturesModal] = useState<{
    visible: boolean;
    deviceId: string;
    deviceName: string;
  }>({ visible: false, deviceId: "", deviceName: "" });

  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      const data = await otaDashboardService.getStats();
      setStats(data);
    } catch (err: any) {
      toast.error("Lỗi tải dữ liệu: " + err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  if (loading || !stats) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <Spin size="large" tip="Đang tải OTA Dashboard..." />
      </div>
    );
  }

  const recentColumns = [
    {
      title: "Thiết bị",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: any) => (
        <div>
          <Text strong>{name || record.mac}</Text>
          <br />
          <Text size="small" type="tertiary">
            {record.mac}
          </Text>
        </div>
      ),
    },
    {
      title: "Board",
      dataIndex: "board",
      key: "board",
      render: (board: string) => <Tag>{board}</Tag>,
    },
    {
      title: "Firmware",
      dataIndex: "firmware_version",
      key: "firmware_version",
      render: (v: string) => v || "-",
    },
    {
      title: "License",
      dataIndex: "license_type",
      key: "license_type",
      render: (lt: string) => (
        <Tag color={lt === "unlimited" ? "green" : lt === "days" ? "orange" : "blue"}>
          {LICENSE_TYPE_LABELS[lt] || lt}
        </Tag>
      ),
    },
    {
      title: "Hoạt động",
      dataIndex: "last_seen",
      key: "last_seen",
      render: (d: string | null) =>
        d ? new Date(d).toLocaleString("vi-VN") : "-",
    },
    {
      title: "Hành động",
      key: "actions",
      width: 280,
      render: (_: any, record: any) => (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <Button
            size="small"
            theme="light"
            type="primary"
            onClick={() =>
              setLicenseModal({
                visible: true,
                deviceId: record.mac,
                deviceName: record.name || record.mac,
              })
            }
          >
            🔑 License
          </Button>
          <Button
            size="small"
            theme="light"
            type="secondary"
            onClick={() =>
              setFeaturesModal({
                visible: true,
                deviceId: record.mac,
                deviceName: record.name || record.mac,
              })
            }
          >
            ⚙️ Tính năng
          </Button>
        </div>
      ),
    },
  ];


  return (
    <div style={{ padding: "24px", maxWidth: 1400, margin: "0 auto" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 24,
        }}
      >
        <div>
          <Title heading={3} style={{ margin: 0 }}>
            📡 OTA Dashboard
          </Title>
          <Text type="tertiary">
            Quản lý firmware, license và tính năng thiết bị IoT
          </Text>
        </div>
        <Button
          icon={<IconRefresh />}
          onClick={fetchStats}
          loading={loading}
        >
          Làm mới
        </Button>
      </div>

      {/* Stats Cards */}
      <div
        style={{
          display: "flex",
          gap: 16,
          flexWrap: "wrap",
          marginBottom: 24,
        }}
      >
        <StatCard
          icon={<IconDesktop />}
          title="Tổng thiết bị"
          value={stats.total_devices}
          subtitle={`${stats.enabled_devices} kích hoạt`}
          color="#6366F1"
        />
        <StatCard
          icon={<IconActivity />}
          title="Hoạt động hôm nay"
          value={stats.active_today}
          subtitle={`${stats.active_this_week} tuần này`}
          color="#10B981"
        />
        <StatCard
          icon={<IconServer />}
          title="Firmware"
          value={stats.total_firmware}
          subtitle="versions"
          color="#F59E0B"
        />
        <StatCard
          icon={<IconShield />}
          title="License"
          value={`${stats.valid_licenses}/${stats.total_devices}`}
          subtitle={`${stats.expired_licenses} hết hạn`}
          color={stats.expired_licenses > 0 ? "#EF4444" : "#10B981"}
        />
      </div>

      {/* Tabs */}
      <Tabs defaultActiveKey="overview" type="line">
        <TabPane tab="📊 Tổng quan" itemKey="overview">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1fr",
              gap: 16,
              marginTop: 16,
            }}
          >
            {/* Activity Chart */}
            <Card
              title="📈 Hoạt động 7 ngày"
              headerStyle={{ padding: "12px 20px" }}
              bodyStyle={{ padding: "16px 20px" }}
            >
              <ActivityChart data={stats.activity_by_day} />
            </Card>

            {/* Board Distribution */}
            <Card
              title="🧩 Phân bố Board"
              headerStyle={{ padding: "12px 20px" }}
              bodyStyle={{ padding: "16px 20px" }}
            >
              {Object.keys(stats.board_type_count).length > 0 ? (
                <BoardDistribution data={stats.board_type_count} />
              ) : (
                <Empty description="Chưa có dữ liệu" />
              )}
            </Card>
          </div>

          {/* License Summary */}
          <Card
            title="🔑 License"
            style={{ marginTop: 16 }}
            headerStyle={{ padding: "12px 20px" }}
            bodyStyle={{ padding: "16px 20px" }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: 16,
              }}
            >
              <div
                style={{
                  textAlign: "center",
                  padding: 16,
                  borderRadius: 12,
                  background: "rgba(16, 185, 129, 0.06)",
                }}
              >
                <Title heading={2} style={{ color: "#10B981", margin: 0 }}>
                  {stats.valid_licenses}
                </Title>
                <Text size="small" type="tertiary">
                  Có hiệu lực
                </Text>
              </div>
              <div
                style={{
                  textAlign: "center",
                  padding: 16,
                  borderRadius: 12,
                  background: "rgba(239, 68, 68, 0.06)",
                }}
              >
                <Title heading={2} style={{ color: "#EF4444", margin: 0 }}>
                  {stats.expired_licenses}
                </Title>
                <Text size="small" type="tertiary">
                  Hết hạn
                </Text>
              </div>
              <div
                style={{
                  textAlign: "center",
                  padding: 16,
                  borderRadius: 12,
                  background: "rgba(99, 102, 241, 0.06)",
                }}
              >
                <Title heading={2} style={{ color: "#6366F1", margin: 0 }}>
                  {stats.unlimited_licenses}
                </Title>
                <Text size="small" type="tertiary">
                  Không giới hạn
                </Text>
              </div>
              <div
                style={{
                  textAlign: "center",
                  padding: 16,
                  borderRadius: 12,
                  background: "rgba(245, 158, 11, 0.06)",
                }}
              >
                <Title heading={2} style={{ color: "#F59E0B", margin: 0 }}>
                  {stats.trial_licenses}
                </Title>
                <Text size="small" type="tertiary">
                  Dùng thử
                </Text>
              </div>
            </div>
          </Card>
        </TabPane>

        <TabPane tab="🔑 License & Tính năng" itemKey="licenses">
          <Card
            style={{ marginTop: 16 }}
            bodyStyle={{ padding: 0 }}
          >
            <Table
              dataSource={stats.recent_devices}
              columns={recentColumns}
              pagination={false}
              size="small"
              empty={<Empty description="Chưa có thiết bị" />}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* License Editor Modal */}
      <LicenseEditorDialog
        visible={licenseModal.visible}
        deviceId={licenseModal.deviceId}
        deviceName={licenseModal.deviceName}
        onClose={() => setLicenseModal({ visible: false, deviceId: "", deviceName: "" })}
        onSaved={fetchStats}
      />

      {/* Features Editor Modal */}
      <FeaturesEditorDialog
        visible={featuresModal.visible}
        deviceId={featuresModal.deviceId}
        deviceName={featuresModal.deviceName}
        onClose={() => setFeaturesModal({ visible: false, deviceId: "", deviceName: "" })}
        onSaved={fetchStats}
      />
    </div>
  );
}
