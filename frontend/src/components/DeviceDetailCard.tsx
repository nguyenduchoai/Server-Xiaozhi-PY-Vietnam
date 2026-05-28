
import { memo, useState } from "react";
import { IconEdit, IconDelete, IconEyeOpened } from "@douyinfe/semi-icons";
import { Monitor, Settings2, Usb, Wifi, WifiOff, Cpu, HardDrive } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Card, Typography, Row, Col, Skeleton, Space, Button, Tooltip } from '@douyinfe/semi-ui';

import type { Device } from "@types";
import { DisplayCustomizerDialog } from "./display-customizer";
import { AssetGeneratorDialog } from "./asset-generator";

const { Text, Title } = Typography;

const formatTimestamp = (value?: string | null) => {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  } catch {
    return value;
  }
};

export interface DeviceDetailCardProps {
  device?: Device | null;
  className?: string;
  isLoading?: boolean;
  onEdit?: () => void;
  onDelete?: (deviceId: string) => void;
  onCustomize?: (device: Device) => void;
}

const DeviceDetailCardComponent = ({
  device,
  className,
  isLoading = false,
  onEdit,
  onDelete,
}: DeviceDetailCardProps) => {
  const navigate = useNavigate();
  const { t } = useTranslation("agents");

  // Dialog states
  const [showDisplayCustomizer, setShowDisplayCustomizer] = useState(false);
  const [showAssetGenerator, setShowAssetGenerator] = useState(false);

  if (isLoading) {
    return (
      <Card className={className} loading={true}>
        <Skeleton placeholder={<Skeleton.Image style={{ height: 200 }} />} active >
          <Skeleton.Paragraph rows={3} />
        </Skeleton>
      </Card>
    );
  }

  if (!device) {
    return (
      <Card
        className={className}
        bodyStyle={{ padding: 24, textAlign: 'center' }}
        style={{
          background: "linear-gradient(135deg, rgba(148,163,184,0.03), rgba(148,163,184,0.06))",
          borderColor: "rgba(148,163,184,0.15)",
          borderLeft: "3px solid #94a3b8",
          borderStyle: "dashed",
        }}
      >
        <Space vertical align="center" spacing="medium">
          <div
            className="flex items-center justify-center w-12 h-12 rounded-xl"
            style={{ background: "rgba(148,163,184,0.10)" }}
          >
            <WifiOff size={24} color="#94a3b8" />
          </div>
          <div>
            <Title heading={6}>{t("no_device_bound")}</Title>
            <Text type="secondary">{t("bind_device")}</Text>
          </div>
        </Space>
      </Card>
    )
  }

  // Device online status
  const isStatusOnline = device.status === 'active' || device.status === 'online';
  const lastSeen = device.last_connected_at ? new Date(device.last_connected_at) : null;
  const isOnline = isStatusOnline || (lastSeen ? (Date.now() - lastSeen.getTime()) < 5 * 60 * 1000 : false);
  const accentColor = isOnline ? "#10b981" : "#3b82f6";

  const deviceBoard = device.board || "ESP-BOX-3";

  return (
    <>
      <div className={className}>
        <Card
          shadows="hover"
          className="cursor-pointer transition-all duration-200 group"
          style={{
            background: `linear-gradient(135deg, ${accentColor}03, ${accentColor}07)`,
            borderColor: `${accentColor}18`,
            borderLeft: `3px solid ${accentColor}`,
          }}
          bodyStyle={{ padding: 16 }}
        >
          {/* Header — Name + Status */}
          <div className="flex items-center justify-between mb-3" onClick={() => navigate(`/devices/${device.id}`)}>
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <div
                className="flex items-center justify-center w-9 h-9 rounded-lg transition-transform duration-200 group-hover:scale-110"
                style={{ background: `${accentColor}12` }}
              >
                {isOnline ? <Wifi size={18} color={accentColor} /> : <HardDrive size={18} color={accentColor} />}
              </div>
              <div className="min-w-0">
                <Title heading={5} style={{ marginBottom: 0 }} className="truncate">
                  {device.device_name || t("device")}
                </Title>
                <div className="flex items-center gap-1.5">
                  <div
                    className={`w-2 h-2 rounded-full ${isOnline ? "animate-pulse" : ""}`}
                    style={{ background: isOnline ? "#10b981" : "#94a3b8" }}
                  />
                  <Text type="tertiary" size="small">{isOnline ? "Online" : "Offline"}</Text>
                </div>
              </div>
            </div>
          </div>

          {/* Device Info Grid */}
          <div className="space-y-2 mb-3" onClick={() => navigate(`/devices/${device.id}`)}>
            <Row gutter={16}>
              <Col span={12}>
                <Text type="tertiary" size="small" className="block" style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {t("mac_address")}
                </Text>
                <Text strong size="small" copyable={{ content: device.mac_address }}>{device.mac_address}</Text>
              </Col>
              <Col span={12}>
                <Text type="tertiary" size="small" className="block" style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {t("board")}
                </Text>
                <div className="flex items-center gap-1.5">
                  <Cpu size={12} color={accentColor} />
                  <Text strong size="small">{device.board || "—"}</Text>
                </div>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Text type="tertiary" size="small" className="block" style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {t("firmware")}
                </Text>
                <Text strong size="small">{device.firmware_version || "—"}</Text>
              </Col>
              <Col span={12}>
                <Text type="tertiary" size="small" className="block" style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {t("last_seen")}
                </Text>
                <Text size="small" type="tertiary">{formatTimestamp(device.last_connected_at)}</Text>
              </Col>
            </Row>
          </div>

          {/* === ACTION BUTTONS — All visible, no hidden dropdown === */}
          <div className="pt-3 space-y-2" style={{ borderTop: `1px solid ${accentColor}10` }}>
            {/* Primary Actions Row */}
            <div className="flex gap-2">
              <Button
                icon={<Monitor className="h-4 w-4" />}
                onClick={(e) => { e.stopPropagation(); navigate(`/devices/${device.id}/customize`); }}
                theme="solid"
                type="primary"
                size="small"
                className="flex-1"
                style={{
                  background: `linear-gradient(135deg, ${accentColor}, ${accentColor}cc)`,
                  border: "none",
                }}
              >
                {t("display_customizer", "Tùy chỉnh")}
              </Button>
              <Button
                icon={<Settings2 className="h-4 w-4" />}
                onClick={(e) => { e.stopPropagation(); setShowDisplayCustomizer(true); }}
                theme="light"
                size="small"
                className="flex-1"
              >
                {t("quick_customize", "Nhanh")}
              </Button>
            </div>

            {/* Secondary Actions Row */}
            <div className="flex gap-2">
              <Tooltip content={t("firmware_flasher", "Nạp Firmware")}>
                <Button
                  icon={<Usb className="h-4 w-4" />}
                  onClick={(e) => { e.stopPropagation(); navigate('/tools/flasher'); }}
                  theme="borderless"
                  type="tertiary"
                  size="small"
                  className="flex-1"
                >
                  {t("firmware_flasher", "Nạp FW")}
                </Button>
              </Tooltip>
              <Tooltip content={t("view_detail", "Xem chi tiết")}>
                <Button
                  icon={<IconEyeOpened />}
                  onClick={(e) => { e.stopPropagation(); navigate(`/devices/${device.id}`); }}
                  theme="borderless"
                  type="tertiary"
                  size="small"
                  className="flex-1"
                >
                  {t("view_detail", "Chi tiết")}
                </Button>
              </Tooltip>
              {onEdit && (
                <Tooltip content={t("edit")}>
                  <Button
                    icon={<IconEdit />}
                    onClick={(e) => { e.stopPropagation(); onEdit(); }}
                    theme="borderless"
                    type="tertiary"
                    size="small"
                  />
                </Tooltip>
              )}
              {onDelete && (
                <Tooltip content={t("delete")}>
                  <Button
                    icon={<IconDelete />}
                    onClick={(e) => { e.stopPropagation(); e.preventDefault?.(); onDelete(device.id); }}
                    theme="borderless"
                    type="danger"
                    size="small"
                  />
                </Tooltip>
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* Display Customizer Dialog */}
      <DisplayCustomizerDialog
        open={showDisplayCustomizer}
        onOpenChange={setShowDisplayCustomizer}
        deviceId={device.id}
        deviceName={device.device_name || device.mac_address}
        deviceBoard={deviceBoard}
        screenWidth={320}
        screenHeight={240}
      />

      {/* Asset Generator Dialog */}
      <AssetGeneratorDialog
        open={showAssetGenerator}
        onOpenChange={setShowAssetGenerator}
        deviceName={device.device_name || device.mac_address}
        deviceBoard={deviceBoard}
      />
    </>
  );
};

export const DeviceDetailCard = memo(DeviceDetailCardComponent);
