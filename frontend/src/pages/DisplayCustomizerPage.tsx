import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Card, Typography, Empty, Row, Col, Skeleton, Select, Button } from "@douyinfe/semi-ui";
import { Monitor, Cpu, ArrowRight } from "lucide-react";
import { IconServer } from "@douyinfe/semi-icons";

import { PageHead } from "@/components";
import apiClient from "@/config/axios-instance";

const { Title, Text } = Typography;

interface Device {
    id: string;
    device_name: string;
    mac_address: string;
    board?: string;
    is_online?: boolean;
}

export function DisplayCustomizerPage() {
    const { t } = useTranslation(["devices", "common"]);
    const navigate = useNavigate();
    const [devices, setDevices] = useState<Device[]>([]);
    const [selectedDevice, setSelectedDevice] = useState<string>("");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDevices();
    }, []);

    const fetchDevices = async () => {
        try {
            setLoading(true);
            const response = await apiClient.get("/user/devices/", {
                params: { page: 1, page_size: 100 }
            });
            const deviceList = response.data.data || [];
            setDevices(deviceList);
            if (deviceList.length > 0) {
                setSelectedDevice(deviceList[0].id);
            }
        } catch (error) {
            console.error("Failed to fetch devices:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleCustomize = () => {
        if (selectedDevice) {
            navigate(`/devices/${selectedDevice}/customize`);
        }
    };

    const selectedDeviceData = devices.find(d => d.id === selectedDevice);

    if (loading) {
        return (
            <div className="space-y-6 p-6">
                <div>
                    <Title heading={2}>{t("display_customizer", "Tạo Theme")}</Title>
                    <Text type="secondary">{t("display_customizer_desc", "Chọn thiết bị để tùy chỉnh giao diện")}</Text>
                </div>
                <Row gutter={[16, 16]}>
                    {[1, 2, 3].map(i => (
                        <Col xs={24} sm={12} lg={8} key={i}>
                            <Skeleton placeholder={<Skeleton.Image style={{ height: 150 }} />} active />
                        </Col>
                    ))}
                </Row>
            </div>
        );
    }

    if (devices.length === 0) {
        return (
            <div className="space-y-6 p-6">
                <PageHead
                    title="Tạo Theme"
                    description="Thiết kế giao diện cho thiết bị ESP32"
                />
                <div>
                    <Title heading={2}>{t("display_customizer", "Tạo Theme")}</Title>
                    <Text type="secondary">{t("display_customizer_desc", "Chọn thiết bị để tùy chỉnh giao diện")}</Text>
                </div>
                <Empty
                    image={<IconServer style={{ fontSize: 48, color: 'var(--semi-color-text-2)' }} />}
                    title={t("no_devices", "Chưa có thiết bị")}
                    description={t("add_device_first", "Vui lòng thêm thiết bị trước khi tùy chỉnh giao diện")}
                >
                    <Button theme="solid" onClick={() => navigate("/devices")}>
                        {t("go_to_devices", "Đi đến trang Thiết bị")}
                    </Button>
                </Empty>
            </div>
        );
    }

    return (
        <>
            <PageHead
                title="Tạo Theme"
                description="Thiết kế giao diện cho thiết bị ESP32"
            />
            <div className="space-y-6 p-6">
                {/* Header */}
                <div>
                    <Title heading={2} className="flex items-center gap-3">
                        <Monitor className="h-8 w-8 text-primary" />
                        {t("display_customizer", "Tạo Theme")}
                    </Title>
                    <Text type="secondary" className="mt-1">
                        {t("display_customizer_desc", "Thiết kế hình nền, đồng hồ, thời tiết và biểu cảm AI cho thiết bị")}
                    </Text>
                </div>

                {/* Device Selection Card */}
                <Card
                    title={
                        <div className="flex items-center gap-2">
                            <Cpu className="h-5 w-5" />
                            <span>{t("select_device", "Chọn thiết bị")}</span>
                        </div>
                    }
                    className="max-w-2xl"
                >
                    <div className="space-y-6">
                        <div>
                            <Text type="secondary" className="block mb-2">
                                {t("select_device_to_customize", "Chọn thiết bị bạn muốn tùy chỉnh giao diện:")}
                            </Text>
                            <Select
                                value={selectedDevice}
                                onChange={(v) => setSelectedDevice(v as string)}
                                style={{ width: '100%' }}
                                size="large"
                                optionList={devices.map(d => ({
                                    value: d.id,
                                    label: (
                                        <div className="flex items-center gap-3 py-1">
                                            <div className={`w-2 h-2 rounded-full ${d.is_online ? "bg-green-500" : "bg-gray-400"}`} />
                                            <div>
                                                <div className="font-medium">{d.device_name || d.mac_address}</div>
                                                {d.board && <div className="text-xs text-gray-500">{d.board}</div>}
                                            </div>
                                        </div>
                                    )
                                }))}
                            />
                        </div>

                        {/* Selected Device Info */}
                        {selectedDeviceData && (
                            <div className="p-4 bg-gray-50 rounded-lg">
                                <div className="grid grid-cols-2 gap-4 text-sm">
                                    <div>
                                        <Text type="tertiary">Tên thiết bị</Text>
                                        <div className="font-medium">{selectedDeviceData.device_name || "—"}</div>
                                    </div>
                                    <div>
                                        <Text type="tertiary">MAC Address</Text>
                                        <div className="font-mono">{selectedDeviceData.mac_address}</div>
                                    </div>
                                    <div>
                                        <Text type="tertiary">Board</Text>
                                        <div>{selectedDeviceData.board || "ESP-BOX-3"}</div>
                                    </div>
                                    <div>
                                        <Text type="tertiary">Trạng thái</Text>
                                        <div className="flex items-center gap-1">
                                            <div className={`w-2 h-2 rounded-full ${selectedDeviceData.is_online ? "bg-green-500" : "bg-gray-400"}`} />
                                            <span>{selectedDeviceData.is_online ? "Online" : "Offline"}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        <Button
                            theme="solid"
                            type="primary"
                            size="large"
                            block
                            onClick={handleCustomize}
                            disabled={!selectedDevice}
                            icon={<ArrowRight className="h-4 w-4" />}
                            iconPosition="right"
                        >
                            {t("start_customizing", "Bắt đầu tùy chỉnh")}
                        </Button>
                    </div>
                </Card>

                {/* Quick Select Cards */}
                <div>
                    <Title heading={5} className="mb-4">{t("quick_select", "Chọn nhanh")}</Title>
                    <Row gutter={[16, 16]}>
                        {devices.slice(0, 6).map(device => (
                            <Col xs={24} sm={12} md={8} lg={6} key={device.id}>
                                <div
                                    className={`cursor-pointer transition-all bg-white rounded-lg border p-4 hover:shadow-md ${selectedDevice === device.id ? 'ring-2 ring-primary border-primary' : 'border-gray-200'}`}
                                    onClick={() => setSelectedDevice(device.id)}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`w-3 h-3 rounded-full ${device.is_online ? "bg-green-500" : "bg-gray-400"}`} />
                                        <div className="flex-1 min-w-0">
                                            <div className="font-medium truncate">{device.device_name || device.mac_address}</div>
                                            <div className="text-xs text-gray-500">{device.board || "ESP32"}</div>
                                        </div>
                                        {selectedDevice === device.id && (
                                            <div className="text-primary">✓</div>
                                        )}
                                    </div>
                                </div>
                            </Col>
                        ))}
                    </Row>
                </div>
            </div>
        </>
    );
}
