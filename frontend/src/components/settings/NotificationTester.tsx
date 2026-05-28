/**
 * NotificationTester - Semi Design implementation
 */

import { useState, useEffect } from "react";
import { Card, Typography, Button, Input, Select, Switch, Toast } from "@douyinfe/semi-ui";
import { IconBell } from "@douyinfe/semi-icons";
import { notificationApi } from "@/services/notificationService";
import { analyticsApi, type DeviceStatus } from "@/services/analyticsService";

const { Title, Text } = Typography;

export function NotificationTester() {
    const [devices, setDevices] = useState<DeviceStatus[]>([]);
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);

    const [selectedDevice, setSelectedDevice] = useState<string>("all");
    const [message, setMessage] = useState("");
    const [type, setType] = useState<"info" | "warning" | "alert" | "reminder">("info");
    const [speak, setSpeak] = useState(true);

    useEffect(() => {
        loadDevices();
    }, []);

    const loadDevices = async () => {
        try {
            setLoading(true);
            const data = await analyticsApi.getDeviceStatus();
            // Include both online (WebSocket) and available (MQTT) devices
            setDevices(data.devices.filter((d) => d.is_online || d.status === "available"));
        } catch (error) {
            console.error("Failed to load devices", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSend = async () => {
        if (!message) return;

        try {
            setSending(true);
            if (selectedDevice === "all") {
                await notificationApi.broadcast(message, type, speak);
            } else {
                await notificationApi.send(selectedDevice, message, type, speak);
            }
            Toast.success("Đã gửi thông báo thành công!");
            setMessage("");
        } catch (error) {
            console.error("Send failed", error);
            Toast.error("Gửi thất bại. Kiểm tra console.");
        } finally {
            setSending(false);
        }
    };

    const typeOptions = [
        { value: "info", label: "Info" },
        { value: "warning", label: "Warning" },
        { value: "alert", label: "Alert" },
        { value: "reminder", label: "Reminder" },
    ];

    const deviceOptions = [
        { value: "all", label: "Tất cả thiết bị online" },
        ...devices.map((device) => ({
            value: device.id,
            label: `${device.name} (${device.mac_address})`,
        })),
    ];

    return (
        <Card
            title={
                <div className="flex items-center gap-2">
                    <IconBell className="text-blue-500" />
                    <Title heading={5} className="!mb-0">Test Thông báo & TTS</Title>
                </div>
            }
        >
            <Text type="tertiary" className="block mb-4">
                Gửi thông báo hoặc phát âm thanh trực tiếp tới thiết bị đang online
            </Text>

            <div className="space-y-4">
                <div>
                    <Text strong className="text-sm block mb-1.5">Chọn thiết bị</Text>
                    <Select
                        style={{ width: "100%" }}
                        value={selectedDevice}
                        onChange={(v) => setSelectedDevice(v as string)}
                        optionList={deviceOptions}
                        disabled={loading}
                    />
                    {devices.length === 0 && !loading && (
                        <Text type="danger" size="small" className="mt-1">
                            Không có thiết bị online nào.
                        </Text>
                    )}
                </div>

                <div>
                    <Text strong className="text-sm block mb-1.5">Nội dung thông báo (TTS)</Text>
                    <Input
                        value={message}
                        onChange={(v) => setMessage(v)}
                        placeholder="Nhập nội dung muốn thiết bị nói..."
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <Text strong className="text-sm block mb-1.5">Loại thông báo</Text>
                        <Select
                            style={{ width: "100%" }}
                            value={type}
                            onChange={(v) => setType(v as typeof type)}
                            optionList={typeOptions}
                        />
                    </div>

                    <Card bodyStyle={{ padding: 12 }}>
                        <div className="flex items-center justify-between">
                            <div>
                                <Text strong size="small">Phát âm thanh (TTS)</Text>
                                <Text type="tertiary" size="small" className="block">
                                    Thiết bị sẽ đọc nội dung
                                </Text>
                            </div>
                            <Switch checked={speak} onChange={setSpeak} />
                        </div>
                    </Card>
                </div>

                <Button
                    theme="solid"
                    type="primary"
                    block
                    onClick={handleSend}
                    loading={sending}
                    disabled={!message || sending || (devices.length === 0 && selectedDevice !== "all")}
                >
                    {sending ? "Đang gửi..." : "Gửi thông báo"}
                </Button>
            </div>
        </Card>
    );
}
