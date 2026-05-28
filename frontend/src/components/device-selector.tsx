/**
 * DeviceSelector - Semi Design implementation
 * Combobox component for selecting a device
 */

import { useState, useMemo } from "react";
import { useTranslation } from "react-i18next";

import type { Device } from "@/types";
import { Select, Skeleton, Banner, Typography, Empty } from "@douyinfe/semi-ui";
import { IconAlertCircle } from "@douyinfe/semi-icons";

const { Text } = Typography;

interface DeviceSelectorProps {
  devices: Device[];
  selectedDeviceId?: string;
  onSelectDevice: (device: Device) => void;
  isLoading?: boolean;
  error?: Error | null;
  disabled?: boolean;
}

export function DeviceSelector({
  devices,
  selectedDeviceId,
  onSelectDevice,
  isLoading = false,
  error = null,
  disabled = false,
}: DeviceSelectorProps) {
  const { t } = useTranslation(["chat", "common"]);
  const [searchValue, setSearchValue] = useState("");

  const filteredDevices = useMemo(() => {
    if (!searchValue) return devices;
    return devices.filter(
      (device) =>
        device.device_name?.toLowerCase().includes(searchValue.toLowerCase()) ||
        device.mac_address.toLowerCase().includes(searchValue.toLowerCase())
    );
  }, [devices, searchValue]);

  const handleSelectDevice = (deviceId: string) => {
    const device = devices.find((d) => d.id === deviceId);
    if (device) {
      onSelectDevice(device);
    }
  };

  if (isLoading) {
    return <Skeleton.Paragraph rows={1} />;
  }

  if (error) {
    return (
      <Banner
        type="danger"
        icon={<IconAlertCircle />}
        title={t("common:error")}
        description={error instanceof Error ? error.message : t("error_loading_devices")}
      />
    );
  }

  if (devices.length === 0) {
    return (
      <Banner
        type="info"
        icon={<IconAlertCircle />}
        title={t("no_devices")}
        description={t("no_devices_desc")}
      />
    );
  }

  return (
    <Select
      style={{ width: "100%" }}
      value={selectedDeviceId}
      onChange={(value) => handleSelectDevice(value as string)}
      placeholder={t("select_device_placeholder")}
      disabled={disabled || devices.length === 0}
      filter
      onSearch={(value) => setSearchValue(value)}
      emptyContent={<Empty title={t("no_devices_found")} />}
      optionList={filteredDevices.map((device) => ({
        value: device.id,
        label: device.device_name || "Unnamed Device",
        showTick: true,
      }))}
      renderSelectedItem={(optionNode: { value?: string } | null) => {
        const device = devices.find((d) => d.id === optionNode?.value);
        return device?.device_name || device?.mac_address || t("select_device_placeholder");
      }}
      renderOptionItem={(renderProps) => {
        const { disabled, selected, label, value, ...rest } = renderProps;
        const device = devices.find((d) => d.id === value);
        return (
          <Select.Option {...rest} value={value} showTick>
            <div className="flex flex-col py-1">
              <Text strong className="text-sm">{device?.device_name || "Unnamed Device"}</Text>
              <Text type="tertiary" size="small">{device?.mac_address}</Text>
            </div>
          </Select.Option>
        );
      }}
    />
  );
}
