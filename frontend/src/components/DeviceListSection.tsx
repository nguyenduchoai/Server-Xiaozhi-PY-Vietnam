"use client";

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Card, Typography, Button, Dropdown, Spin, Empty, Toast, Tag } from "@douyinfe/semi-ui";
import { IconPlus, IconMore, IconDelete } from "@douyinfe/semi-icons";
import type { Device } from "@/types";
import { SelectDeviceDialog } from "./SelectDeviceDialog";
import { apiClient } from "@/config/axios-instance";
import { notificationApi } from "@/services/notificationService";

const { Title, Text } = Typography;

interface DeviceListSectionProps {
    agentId: string;
    devices: Device[];
    isLoading?: boolean;
    onRefresh: () => void;
}

export function DeviceListSection({
    agentId,
    devices,
    isLoading = false,
    onRefresh,
}: DeviceListSectionProps) {
    const { t } = useTranslation("agents");
    const [showAddDialog, setShowAddDialog] = useState(false);
    const [addingDevice, setAddingDevice] = useState(false);
    const [removingDeviceId, setRemovingDeviceId] = useState<string | null>(null);
    const [mqttDevices, setMqttDevices] = useState<Set<string>>(new Set());

    // Fetch MQTT connected devices on mount and periodically
    useEffect(() => {
        const fetchMqttDevices = async () => {
            try {
                const data = await notificationApi.getMqttDevices();
                setMqttDevices(new Set(data.mqtt_connected_devices.map(mac => mac.toLowerCase())));
            } catch (error) {
                // Silently fail - MQTT tracking is optional
            }
        };

        fetchMqttDevices();
        const interval = setInterval(fetchMqttDevices, 30000); // Refresh every 30s
        return () => clearInterval(interval);
    }, []);

    const handleAddDevice = async (deviceId: string) => {
        try {
            setAddingDevice(true);
            await apiClient.post(`/agents/${agentId}/devices/${deviceId}`);
            Toast.success(t("device_added", "Đã thêm thiết bị thành công"));
            setShowAddDialog(false);
            onRefresh();
        } catch (error: any) {
            Toast.error(error?.response?.data?.detail || t("device_add_error", "Không thể thêm thiết bị"));
        } finally {
            setAddingDevice(false);
        }
    };

    const handleRemoveDevice = async (deviceId: string) => {
        try {
            setRemovingDeviceId(deviceId);
            await apiClient.delete(`/agents/${agentId}/devices/${deviceId}`);
            Toast.success(t("device_removed", "Đã gỡ thiết bị khỏi agent"));
            onRefresh();
        } catch (error: any) {
            Toast.error(error?.response?.data?.detail || t("device_remove_error", "Không thể gỡ thiết bị"));
        } finally {
            setRemovingDeviceId(null);
        }
    };

    const getDeviceStatus = (device: Device) => {
        const lastConnected = device.last_connected_at
            ? new Date(device.last_connected_at).getTime()
            : 0;
        const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
        const isStatusOnline = device.status === 'active' || device.status === 'online';
        const isOnline = isStatusOnline || lastConnected > fiveMinutesAgo;
        const isMqttConnected = mqttDevices.has(device.mac_address?.toLowerCase() || "");

        // Priority: Online (WebSocket) > Available (MQTT) > Offline
        if (isOnline) {
            return {
                isOnline: true,
                isMqttConnected,
                label: t("online", "Online"),
                color: "text-green-500",
                dot: "🟢",
                tagType: "success" as const,
            };
        } else if (isMqttConnected) {
            return {
                isOnline: false,
                isMqttConnected: true,
                label: t("available", "Available"),
                color: "text-blue-500",
                dot: "🔵",
                tagType: "primary" as const,
            };
        } else {
            return {
                isOnline: false,
                isMqttConnected: false,
                label: t("offline", "Offline"),
                color: "text-gray-400",
                dot: "⚫",
                tagType: "default" as const,
            };
        }
    };

    const formatLastSeen = (date: string | null | undefined) => {
        if (!date) return t("never", "Chưa kết nối");
        const d = new Date(date);
        return d.toLocaleString("vi-VN", {
            hour: "2-digit",
            minute: "2-digit",
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
        });
    };

    return (
        <>
            <Card className="p-0" bodyStyle={{ padding: 0 }}>
                <div className="flex items-center justify-between p-4 border-b">
                    <Title heading={6} className="!mb-0 flex items-center gap-2">
                        📱 {t("devices", "Thiết bị")}
                        <span className="text-xs text-gray-400 font-normal">
                            ({devices.length})
                        </span>
                    </Title>
                    <Button
                        icon={<IconPlus />}
                        theme="solid"
                        size="small"
                        onClick={() => setShowAddDialog(true)}
                    >
                        {t("add_template", "Thêm")}
                    </Button>
                </div>

                <div className="p-4">
                    {isLoading ? (
                        <div className="flex justify-center py-8">
                            <Spin size="large" />
                        </div>
                    ) : devices.length === 0 ? (
                        <Empty
                            description={t("no_devices", "Chưa có thiết bị. Thêm để bắt đầu.")}
                            className="py-8"
                        />
                    ) : (
                        <div className="space-y-3">
                            {devices.map((device) => {
                                const status = getDeviceStatus(device);
                                return (
                                    <div
                                        key={device.id}
                                        className="flex items-center justify-between p-3 rounded-lg border hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                                    >
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <span className="text-lg">📱</span>
                                                <Text strong className="truncate">
                                                    {device.device_name || device.mac_address}
                                                </Text>
                                                {device.board && (
                                                    <span className="text-xs bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 px-2 py-0.5 rounded">
                                                        {device.board}
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                                                <span>MAC: {device.mac_address}</span>
                                                <Tag
                                                    color={status.tagType === "success" ? "green" : status.tagType === "primary" ? "blue" : "grey"}
                                                    size="small"
                                                >
                                                    {status.dot} {status.label}
                                                </Tag>
                                                <span>Last: {formatLastSeen(device.last_connected_at)}</span>
                                            </div>
                                        </div>

                                        <Dropdown
                                            trigger="click"
                                            position="bottomRight"
                                            render={
                                                <Dropdown.Menu>
                                                    <Dropdown.Item
                                                        icon={<IconDelete />}
                                                        type="danger"
                                                        onClick={() => handleRemoveDevice(device.id)}
                                                        disabled={removingDeviceId === device.id}
                                                    >
                                                        {t("remove_device", "Gỡ khỏi Agent")}
                                                    </Dropdown.Item>
                                                </Dropdown.Menu>
                                            }
                                        >
                                            <Button
                                                icon={<IconMore />}
                                                theme="borderless"
                                                size="small"
                                                loading={removingDeviceId === device.id}
                                            />
                                        </Dropdown>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </Card>

            <SelectDeviceDialog
                open={showAddDialog}
                onOpenChange={setShowAddDialog}
                onSelect={handleAddDevice}
                isLoading={addingDevice}
                excludeDeviceIds={devices.map((d) => d.id)}
                agentId={agentId}
            />
        </>
    );
}

export default DeviceListSection;
