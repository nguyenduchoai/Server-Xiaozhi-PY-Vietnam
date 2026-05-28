
"use client";

import { useTranslation } from "react-i18next";
import { Button, Select, Typography, Space, Badge } from "@douyinfe/semi-ui";
import { IconSignal } from "@douyinfe/semi-icons";
import type { Device } from "@/types";

type ChatHeaderProps = {
  userName?: string;
  isConnected: boolean;
  isConnecting: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  selectedDevice?: Device | null;
  devices?: Device[];
  isLoadingDevices?: boolean;
  deviceError?: Error | null;
  onSelectDevice?: (device: Device) => void;
};

export function ChatHeader(props: ChatHeaderProps) {
  const { t } = useTranslation("chat");
  const {
    userName = "User",
    isConnected,
    isConnecting,
    onConnect,
    onDisconnect,
    selectedDevice,
    devices = [],
    isLoadingDevices = false,
    onSelectDevice,
  } = props;

  // Transform devices for Select
  const deviceOptions = devices.map((d) => ({
    label: d.device_name || d.mac_address,
    value: d.id,
    extra: d // Keep full object ref if needed
  }));

  const handleDeviceChange = (val: string | number | any[]) => {
    const selected = devices.find(d => d.id === val);
    if (selected && onSelectDevice) {
      onSelectDevice(selected);
    }
  }

  return (
    <div style={{ padding: '12px 24px', backgroundColor: 'var(--semi-color-bg-0)', borderBottom: '1px solid var(--semi-color-border)' }}>
      <div className="flex items-center justify-between">
        <div>
          <Typography.Title heading={4} style={{ margin: 0 }}>{t("chat_title")}</Typography.Title>
          <div className="flex items-center gap-2 mt-1">
            <Typography.Text type="secondary">
              {t("chat_welcome", { name: userName })}
            </Typography.Text>
            {selectedDevice && (
              <Badge count={selectedDevice.device_name || selectedDevice.mac_address} theme="solid" type="primary" />
            )}
          </div>
        </div>

        <Space spacing="medium">
          {onSelectDevice && (
            <Select
              placeholder={t("select_device", "Chọn thiết bị")}
              optionList={deviceOptions}
              value={selectedDevice?.id}
              onChange={(val: any) => handleDeviceChange(val)}
              loading={isLoadingDevices}
              disabled={isConnected}
              style={{ width: 200 }}
              prefix={<IconSignal />}
            />
          )}

          <Space>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor: isConnected ? 'var(--semi-color-success)' : isConnecting ? 'var(--semi-color-warning)' : 'var(--semi-color-danger)'
              }}
            />
            <Button
              onClick={isConnected ? onDisconnect : onConnect}
              loading={isConnecting}
              theme="solid"
              type={isConnected ? "danger" : "primary"}
            >
              {isConnecting
                ? t("connecting")
                : isConnected
                  ? t("disconnect")
                  : t("connect")}
            </Button>
          </Space>
        </Space>
      </div>
    </div>
  );
}
