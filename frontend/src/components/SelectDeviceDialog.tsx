/**
 * SelectDeviceDialog - Semi Design implementation
 * Dialog for selecting a device to add to an agent
 */

import { useState, useMemo } from "react";
import { Cpu } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";

import type { Device } from "@/types";
import {
    Modal,
    Input,
    Button,
    Tag,
    Skeleton,
    Empty,
    Typography,
    Card,
} from "@douyinfe/semi-ui";
import { IconSearch, IconTick } from "@douyinfe/semi-icons";
import { apiClient } from "@/config/axios-instance";

const { Text, Title } = Typography;

export interface SelectDeviceDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSelect: (deviceId: string) => Promise<void>;
    isLoading?: boolean;
    excludeDeviceIds?: string[];
    agentId: string;
}

export function SelectDeviceDialog({
    open,
    onOpenChange,
    onSelect,
    isLoading = false,
    excludeDeviceIds = [],
}: SelectDeviceDialogProps) {
    const { t } = useTranslation("agents");
    const [searchQuery, setSearchQuery] = useState("");
    const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);

    const { data, isLoading: isLoadingDevices } = useQuery({
        queryKey: ["all-devices-for-selection"],
        queryFn: async () => {
            const { data } = await apiClient.get<{ data: Device[]; total: number }>(
                "/user/devices/",
                { params: { page: 1, page_size: 100 } }
            );
            return data;
        },
        enabled: open,
    });

    const devices = data?.data ?? [];

    const filteredDevices = useMemo(() => {
        return devices.filter((device) => {
            if (excludeDeviceIds.includes(device.id)) return false;
            if (!searchQuery) return true;
            const query = searchQuery.toLowerCase();
            return (
                device.device_name?.toLowerCase().includes(query) ||
                device.mac_address.toLowerCase().includes(query) ||
                device.board?.toLowerCase().includes(query)
            );
        });
    }, [devices, excludeDeviceIds, searchQuery]);

    const handleSelect = async () => {
        if (!selectedDeviceId) return;
        try {
            await onSelect(selectedDeviceId);
            handleClose();
        } catch (error) {
            console.error("Select device error:", error);
        }
    };

    const handleClose = () => {
        setSearchQuery("");
        setSelectedDeviceId(null);
        onOpenChange(false);
    };

    const getDeviceStatus = (device: Device) => {
        const isStatusOnline = device.status === 'active' || device.status === 'online';
        const lastConnected = device.last_connected_at
            ? new Date(device.last_connected_at).getTime()
            : 0;
        const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
        return isStatusOnline || lastConnected > fiveMinutesAgo;
    };

    return (
        <Modal
            title={
                <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600">
                        <Cpu className="h-5 w-5 text-white" />
                    </div>
                    <div>
                        <Title heading={5} className="!mb-0">{t("select_device", "Chọn Thiết bị")}</Title>
                        <Text type="tertiary" size="small">
                            {t("select_device_desc", "Chọn thiết bị để thêm vào agent này")}
                        </Text>
                    </div>
                </div>
            }
            visible={open}
            onCancel={handleClose}
            width={520}
            footer={
                <div className="flex justify-end gap-3">
                    <Button onClick={handleClose} disabled={isLoading}>
                        {t("common:cancel", "Hủy")}
                    </Button>
                    <Button
                        theme="solid"
                        type="primary"
                        onClick={handleSelect}
                        disabled={!selectedDeviceId || isLoading}
                        loading={isLoading}
                    >
                        {t("add_device", "Thêm Thiết bị")}
                    </Button>
                </div>
            }
            bodyStyle={{ padding: "16px 24px" }}
        >
            <div className="space-y-4">
                <Input
                    prefix={<IconSearch />}
                    placeholder={t("search_devices", "Tìm kiếm thiết bị...")}
                    value={searchQuery}
                    onChange={(v) => setSearchQuery(v)}
                    size="large"
                    showClear
                />

                <div className="max-h-[320px] overflow-y-auto pr-1 space-y-2">
                    {isLoadingDevices ? (
                        <div className="space-y-2">
                            {Array.from({ length: 4 }).map((_, i) => (
                                <Skeleton.Paragraph key={i} rows={2} style={{ marginBottom: 12 }} />
                            ))}
                        </div>
                    ) : filteredDevices.length === 0 ? (
                        <div className="py-8">
                            <Empty
                                image={<Cpu className="h-12 w-12 text-gray-300" />}
                                title={searchQuery
                                    ? t("no_devices_found", "Không tìm thấy thiết bị")
                                    : t("no_available_devices", "Không có thiết bị khả dụng")}
                                description={t("device_hint", "Thiết bị cần được kích hoạt trước khi thêm vào agent")}
                            />
                        </div>
                    ) : (
                        filteredDevices.map((device) => {
                            const isSelected = selectedDeviceId === device.id;
                            const isOnline = getDeviceStatus(device);

                            return (
                                <div
                                    key={device.id}
                                    onClick={() => setSelectedDeviceId(device.id)}
                                    className="cursor-pointer"
                                >
                                    <Card
                                        className={`transition-all duration-200 ${isSelected
                                                ? "!border-blue-500 !bg-blue-50 dark:!bg-blue-900/20 shadow-md"
                                                : "hover:!border-blue-300 hover:shadow-sm"
                                            }`}
                                        bodyStyle={{ padding: 12 }}
                                    >
                                        <div className="flex items-center justify-between gap-3">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-lg">📱</span>
                                                    <Text strong ellipsis={{ showTooltip: true }} className="text-sm">
                                                        {device.device_name || device.mac_address}
                                                    </Text>
                                                    {device.board && (
                                                        <Tag size="small" color="blue">{device.board}</Tag>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-3">
                                                    <Text type="tertiary" size="small">MAC: {device.mac_address}</Text>
                                                    <Tag size="small" color={isOnline ? "green" : "grey"}>
                                                        {isOnline ? "🟢 Online" : "⚫ Offline"}
                                                    </Tag>
                                                </div>
                                            </div>
                                            {isSelected && (
                                                <div className="flex-shrink-0 p-1.5 rounded-full bg-blue-500">
                                                    <IconTick className="text-white" />
                                                </div>
                                            )}
                                        </div>
                                    </Card>
                                </div>
                            );
                        })
                    )}
                </div>
            </div>
        </Modal>
    );
}

export default SelectDeviceDialog;
