import { toast } from "sonner";
"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  IconArrowLeft,
  IconDelete,
  IconCopy,
  IconSetting,
  IconTerminal,
  IconEdit,
} from "@douyinfe/semi-icons";
import {
  Button,
  Card,
  Tabs,
  TabPane,
  Tag,
  Typography,

  Select,
  Banner,
  Skeleton
} from "@douyinfe/semi-ui";
import {
  Check,
  Cpu,
  Usb,
  Unplug,
  Download,
  Play,
  Pause,
  Bot,
} from "lucide-react"; // Keeping specialized icons not in Semi

import { PageHead, DeviceControlPanel } from "@/components";
import { cn } from "@/lib/utils";
import { useDevice } from "@/hooks";
import { EditDeviceDialog } from "@/components";
import { useUpdateDevice } from "@/queries/device-queries";
import { useTemplateList } from "@/queries/template-queries";
import AgentDeviceManager from "@/components/AgentDeviceManager";

const { Title, Text } = Typography;

// Common baud rates for ESP32 monitor
const BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600] as const;

// Local Web Serial port type
interface LocalSerialPort {
  open(options: { baudRate: number }): Promise<void>;
  close(): Promise<void>;
  readable: ReadableStream<Uint8Array> | null;
  writable: WritableStream<Uint8Array> | null;
}

type ConnectionState = "disconnected" | "connecting" | "connected";

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

export function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const { t } = useTranslation(["devices", "agents", "common"]);

  // Fetch device data
  const { data: device, isLoading, error, refetch } = useDevice(deviceId!);

  // Edit dialog state
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const { mutateAsync: updateDevice, isPending: isUpdating } = useUpdateDevice();

  // Fetch templates for control panel
  const { data: templatesData } = useTemplateList();

  // Serial Monitor state
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [baudRate, setBaudRate] = useState<number>(115200);
  const [logs, setLogs] = useState<string[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [copyState, setCopyState] = useState<{ copied: boolean; field: string | null }>({
    copied: false,
    field: null,
  });

  // Refs
  const portRef = useRef<LocalSerialPort | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const isReadingRef = useRef(false);

  // Check WebSerial support
  const isWebSerialSupported = "serial" in navigator;

  // Copy handler
  const handleCopy = useCallback((text: string, field: string) => {
    navigator.clipboard.writeText(text);
    setCopyState({ copied: true, field });
    toast.success(t("common:copied", "Copied to clipboard"));
    setTimeout(() => {
      setCopyState({ copied: false, field: null });
    }, 2000);
  }, [t]);

  // Add log entry
  const addLog = useCallback((message: string, type: "data" | "info" | "error" = "data") => {
    const timestamp = new Date().toLocaleTimeString("vi-VN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      fractionalSecondDigits: 3,
    });

    const prefix = type === "error" ? "❌" : type === "info" ? "ℹ️" : "";
    const formattedMessage = prefix ? `[${timestamp}] ${prefix} ${message}` : `[${timestamp}] ${message}`;

    setLogs(prev => {
      const newLogs = [...prev, formattedMessage];
      if (newLogs.length > 1000) {
        return newLogs.slice(-1000);
      }
      return newLogs;
    });
  }, []);

  // Scroll to bottom
  useEffect(() => {
    if (!isPaused) {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, isPaused]);

  // Read from serial port
  const readSerialData = useCallback(async () => {
    const port = portRef.current;
    if (!port?.readable || isReadingRef.current) return;

    isReadingRef.current = true;
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      const reader = port.readable.getReader();
      readerRef.current = reader;

      while (true) {
        const { value, done } = await reader.read();

        if (done) {
          break;
        }

        if (value) {
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            const trimmedLine = line.replace(/\r/g, "").trim();
            if (trimmedLine) {
              addLog(trimmedLine);
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "TypeError") {
        const message = err instanceof Error ? err.message : "Lỗi đọc dữ liệu";
        addLog(message, "error");
      }
    } finally {
      isReadingRef.current = false;
      readerRef.current = null;
    }
  }, [addLog]);

  // Connect to serial port
  const handleConnect = useCallback(async () => {
    if (!isWebSerialSupported) {
      addLog("Trình duyệt không hỗ trợ WebSerial API", "error");
      return;
    }

    try {
      setConnectionState("connecting");
      addLog(`Đang kết nối với baudrate ${baudRate}...`, "info");

      const port = await navigator.serial!.requestPort() as unknown as LocalSerialPort;
      await port.open({ baudRate });
      portRef.current = port;

      setConnectionState("connected");
      addLog(`Đã kết nối thành công! Baudrate: ${baudRate}`, "info");
      addLog("Đang chờ dữ liệu từ thiết bị...", "info");

      readSerialData();

    } catch (err) {
      const message = err instanceof Error ? err.message : "Lỗi kết nối";

      if (message.includes("No port selected")) {
        addLog("Đã hủy chọn cổng COM", "info");
      } else {
        addLog(`Lỗi kết nối: ${message}`, "error");
      }

      setConnectionState("disconnected");
      portRef.current = null;
    }
  }, [isWebSerialSupported, baudRate, addLog, readSerialData]);

  // Disconnect from serial port
  const handleDisconnect = useCallback(async () => {
    try {
      if (readerRef.current) {
        await readerRef.current.cancel();
        readerRef.current = null;
      }

      if (portRef.current) {
        await portRef.current.close();
        portRef.current = null;
      }

      setConnectionState("disconnected");
      addLog("Đã ngắt kết nối", "info");

    } catch (err) {
      const message = err instanceof Error ? err.message : "Lỗi ngắt kết nối";
      addLog(`Lỗi: ${message}`, "error");

      portRef.current = null;
      readerRef.current = null;
      setConnectionState("disconnected");
    }
  }, [addLog]);

  // Clear logs
  const handleClearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  // Download logs
  const handleDownloadLogs = useCallback(() => {
    const content = logs.join("\n");
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `serial-monitor-${device?.device_name || "device"}-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [logs, device?.device_name]);

  // Handle edit device submit
  const handleEditDeviceSubmit = async (data: { device_name?: string; board?: string; status?: string }) => {
    if (!device) return;

    try {
      await updateDevice({ deviceId: device.id, payload: data });
      refetch();
      toast.success(t("device_updated", { ns: "devices" }));
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : t("update_error", { ns: "devices" });
      toast.error(errorMsg);
      throw error;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (readerRef.current) {
        readerRef.current.cancel().catch(() => { });
      }
      if (portRef.current) {
        portRef.current.close().catch(() => { });
      }
    };
  }, []);

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center gap-4">
          <Skeleton.Avatar />
          <div>
            <Skeleton.Title className="w-48 mb-2" />
            <Skeleton.Paragraph className="w-32" />
          </div>
        </div>
        <Skeleton.Image className="h-96" />
      </div>
    );
  }

  // Error state
  if (error || !device) {
    return (
      <div className="space-y-6 p-6">
        <Button theme="borderless" icon={<IconArrowLeft />} onClick={() => navigate("/devices")}>
          {t("back_to_devices", "Quay lại danh sách")}
        </Button>
        <Banner
          type="danger"
          description={error instanceof Error ? error.message : t("device_not_found", "Không tìm thấy thiết bị")}
        />
      </div>
    );
  }

  return (
    <>
      <PageHead
        title={device.device_name || t("device_detail", "Chi tiết thiết bị")}
        description={t("device_detail_desc", "Xem thông tin và monitor thiết bị")}
      />

      <div className="space-y-6 p-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button theme="borderless" icon={<IconArrowLeft />} onClick={() => navigate("/devices")} />
            <div>
              <Title heading={3} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Cpu className="h-6 w-6" />
                {device.device_name || t("unnamed_device", "Thiết bị chưa đặt tên")}
              </Title>
              <Text type="tertiary">
                {device.mac_address}
              </Text>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button onClick={() => setIsEditDialogOpen(true)} icon={<IconEdit />}>
              {t("edit", { ns: "common" })}
            </Button>
            <Button theme="light" onClick={() => navigate(`/devices/${deviceId}/customize`)} icon={<IconSetting />}>
              {t("customize_ui", "Tùy chỉnh")}
            </Button>
          </div>
        </div>

        {/* Main content with tabs */}
        {/* Quick Action Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Custom UI Card */}
          <div
            className="cursor-pointer"
            onClick={() => navigate(`/devices/${deviceId}/customize`)}
          >
            <Card
              shadows="hover"
              className="transition-all hover:shadow-lg border-l-4 border-l-blue-500 h-full"
              bodyStyle={{ padding: 16 }}
            >
              <div className="flex items-center gap-4">
                <div className="p-3 bg-blue-100 rounded-lg">
                  <IconSetting style={{ fontSize: 24, color: 'var(--semi-color-primary)' }} />
                </div>
                <div>
                  <Title heading={6} style={{ marginBottom: 4 }}>
                    {t("customize_ui", "Tùy chỉnh giao diện")}
                  </Title>
                  <Text type="tertiary" size="small">
                    {t("customize_ui_desc", "Hình nền, đồng hồ, thời tiết...")}
                  </Text>
                </div>
              </div>
            </Card>
          </div>

          {/* Firmware Flasher Card */}
          <div
            className="cursor-pointer"
            onClick={() => navigate('/tools/flasher')}
          >
            <Card
              shadows="hover"
              className="transition-all hover:shadow-lg border-l-4 border-l-green-500 h-full"
              bodyStyle={{ padding: 16 }}
            >
              <div className="flex items-center gap-4">
                <div className="p-3 bg-green-100 rounded-lg">
                  <Usb className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <Title heading={6} style={{ marginBottom: 4 }}>
                    {t("firmware_flasher", "Nạp Firmware")}
                  </Title>
                  <Text type="tertiary" size="small">
                    {t("firmware_flasher_desc", "Nạp firmware OTA hoặc qua USB")}
                  </Text>
                </div>
              </div>
            </Card>
          </div>

          {/* Serial Monitor Card */}
          <div
            className="cursor-pointer"
            onClick={() => {
              // Scroll to monitor tab
              const monitorTab = document.querySelector('[data-itemkey="monitor"]');
              monitorTab?.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            <Card
              shadows="hover"
              className="transition-all hover:shadow-lg border-l-4 border-l-purple-500 h-full"
              bodyStyle={{ padding: 16 }}
            >
              <div className="flex items-center gap-4">
                <div className="p-3 bg-purple-100 rounded-lg">
                  <IconTerminal style={{ fontSize: 24, color: '#8b5cf6' }} />
                </div>
                <div>
                  <Title heading={6} style={{ marginBottom: 4 }}>
                    {t("serial_monitor", "Serial Monitor")}
                  </Title>
                  <Text type="tertiary" size="small">
                    {t("serial_monitor_desc", "Xem log từ thiết bị qua USB")}
                  </Text>
                </div>
              </div>
            </Card>
          </div>
        </div>

        <Tabs type="line" defaultActiveKey="control">
          <TabPane tab={
            <span>
              <IconTerminal style={{ marginRight: 8 }} />
              {t("serial_monitor", "Serial Monitor")}
            </span>
          } itemKey="monitor"
          >
            <div className="space-y-4 pt-4">
              {/* Toolbar */}
              <Card bodyStyle={{ padding: 12 }}>
                <div className="flex items-center gap-2 flex-wrap">
                  {/* Connection button */}
                  {connectionState === "disconnected" ? (
                    <Button onClick={handleConnect} theme="solid" icon={<Usb className="h-4 w-4 mr-2" />}>
                      {t("connect", "Kết nối")}
                    </Button>
                  ) : connectionState === "connecting" ? (
                    <Button disabled icon={<Usb className="h-4 w-4 animate-pulse mr-2" />}>
                      {t("connecting", "Đang kết nối...")}
                    </Button>
                  ) : (
                    <Button onClick={handleDisconnect} type="danger" icon={<Unplug className="h-4 w-4 mr-2" />}>
                      {t("disconnect", "Ngắt kết nối")}
                    </Button>
                  )}

                  {/* Pause/Resume */}
                  <Button
                    onClick={() => setIsPaused(!isPaused)}
                    theme="light"
                    icon={isPaused ? <Play className="h-4 w-4 mr-2" /> : <Pause className="h-4 w-4 mr-2" />}
                  >
                    {isPaused ? t("resume", "Tiếp tục") : t("pause", "Tạm dừng")}
                  </Button>

                  {/* Clear logs */}
                  <Button
                    onClick={handleClearLogs}
                    theme="light"
                    icon={<IconDelete />}
                  >
                    {t("clear", "Xóa")}
                  </Button>

                  {/* Download logs */}
                  <Button
                    onClick={handleDownloadLogs}
                    theme="light"
                    disabled={logs.length === 0}
                    icon={<Download className="h-4 w-4 mr-2" />}
                  >
                    {t("download", "Tải về")}
                  </Button>

                  {/* Settings toggle */}
                  <Button
                    onClick={() => setShowSettings(!showSettings)}
                    theme={showSettings ? "solid" : "borderless"}
                    type={showSettings ? "secondary" : "tertiary"}
                    icon={<IconSetting />}
                  />

                  <div className="flex-1" />

                  {/* Connection status */}
                  <div className="flex items-center gap-2 text-sm">
                    <div
                      className={cn(
                        "h-2 w-2 rounded-full",
                        connectionState === "connected" && "bg-green-500",
                        connectionState === "connecting" && "bg-yellow-500 animate-pulse",
                        connectionState === "disconnected" && "bg-gray-400"
                      )}
                    />
                    <Text type="tertiary">
                      {connectionState === "connected"
                        ? t("status_connected", "Đã kết nối")
                        : connectionState === "connecting"
                          ? t("status_connecting", "Đang kết nối")
                          : t("status_disconnected", "Chưa kết nối")}
                    </Text>
                  </div>
                </div>

                {/* Settings panel */}
                {showSettings && (
                  <div className="flex items-center gap-4 mt-3 pt-3 border-t">
                    <div className="flex items-center gap-2">
                      <Text strong className="whitespace-nowrap">Baud Rate:</Text>
                      <Select
                        value={String(baudRate)}
                        onChange={(v: any) => setBaudRate(Number(v))}
                        disabled={connectionState === "connected"}
                        style={{ width: 120 }}
                        optionList={BAUD_RATES.map(rate => ({ value: String(rate), label: rate.toLocaleString() }))}
                      />
                    </div>

                    {connectionState === "connected" && (
                      <Text type="tertiary" size="small">
                        * {t("disconnect_to_change", "Ngắt kết nối để thay đổi cài đặt")}
                      </Text>
                    )}
                  </div>
                )}
              </Card>

              {/* WebSerial not supported warning */}
              {!isWebSerialSupported && (
                <Banner
                  type="danger"
                  title="Trình duyệt không hỗ trợ WebSerial API"
                  description="Vui lòng sử dụng Chrome, Edge hoặc Opera phiên bản mới nhất."
                />
              )}

              {/* Terminal output */}
              <Card
                bodyStyle={{ padding: 0 }}
                headerStyle={{ padding: '8px 16px', borderBottom: '1px solid var(--semi-color-border)' }}
                title={
                  <div className="flex items-center justify-between w-full">
                    <span className="flex items-center gap-2 text-sm font-medium">
                      <IconTerminal /> Output
                    </span>
                  </div>
                }
                headerExtraContent={
                  <span className="text-xs text-muted-foreground mr-4">
                    {logs.length} {t("lines", "dòng")}
                    {isPaused && (
                      <span className="text-yellow-500 ml-2">⏸ {t("paused", "Đã tạm dừng")}</span>
                    )}
                  </span>
                }
              >
                <div className="bg-black h-[500px] overflow-y-auto p-4 font-mono text-xs leading-relaxed">
                  {logs.length === 0 ? (
                    <div className="text-gray-500 text-center py-8">
                      {connectionState === "connected"
                        ? t("waiting_for_data", "Đang chờ dữ liệu từ thiết bị...")
                        : t("click_connect", "Nhấn 'Kết nối' để bắt đầu monitor")}
                    </div>
                  ) : (
                    logs.map((log, index) => (
                      <div
                        key={index}
                        className={cn(
                          "whitespace-pre-wrap break-all",
                          log.includes("❌") && "text-red-400",
                          log.includes("ℹ️") && "text-blue-400",
                          !log.includes("❌") && !log.includes("ℹ️") && "text-green-400"
                        )}
                      >
                        {log}
                      </div>
                    ))
                  )}
                  <div ref={logsEndRef} />
                </div>
              </Card>
            </div>
          </TabPane>

          {/* Remote Control Tab */}
          <TabPane tab={
            <span>
              <IconSetting style={{ marginRight: 8 }} />
              {t("remote_control", "Điều khiển")}
            </span>
          } itemKey="control"
          >
            <div className="pt-4">
              <DeviceControlPanel
                deviceId={deviceId!}
                deviceStatus={(device.status === 'active' || device.status === 'online') ? 'online' : 'offline'}
                templates={templatesData?.data?.map((t: any) => ({
                  id: t.id,
                  name: t.template_name || t.name,
                })) || []}
                onTemplateChange={() => refetch()}
              />
            </div>
          </TabPane>

          <TabPane tab={
            <span>
              <Cpu className="h-4 w-4 mr-2 inline-block" />
              {t("device_info", "Thông tin")}
            </span>
          } itemKey="info"
          >
            <Card className="mt-4" title={
              <div className="flex items-center gap-2">
                <Cpu className="h-5 w-5" />
                {t("device_details", { ns: "agents" })}
              </div>
            }>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Device Name */}
                <div className="space-y-1">
                  <Text type="tertiary" strong>{t("device_name", { ns: "agents" })}</Text>
                  <Title heading={5}>{device.device_name || "—"}</Title>
                </div>

                {/* MAC Address */}
                <div className="space-y-1">
                  <Text type="tertiary" strong>{t("mac_address", { ns: "agents" })}</Text>
                  <div className="flex items-center gap-2">
                    <Tag size="large" type="solid" color="grey" style={{ fontFamily: 'monospace' }}>
                      {device.mac_address || "—"}
                    </Tag>
                    {device.mac_address && (
                      <Button
                        theme="borderless"
                        icon={copyState.copied && copyState.field === "mac" ? <Check className="h-4 w-4 text-green-600" /> : <IconCopy />}
                        onClick={() => handleCopy(device.mac_address, "mac")}
                      />
                    )}
                  </div>
                </div>

                {/* Board */}
                <div className="space-y-1">
                  <Text type="tertiary" strong>{t("board", { ns: "agents" })}</Text>
                  <Text size="normal" style={{ display: 'block' }}>{device.board || "—"}</Text>
                </div>

                {/* Firmware Version */}
                <div className="space-y-1">
                  <Text type="tertiary" strong>{t("firmware_version", { ns: "agents" })}</Text>
                  <Text size="normal" style={{ fontFamily: 'monospace', display: 'block' }}>{device.firmware_version || "—"}</Text>
                </div>

                {/* Status */}
                <div className="space-y-1">
                  <Text type="tertiary" strong>{t("device_status", { ns: "agents" })}</Text>
                  <div className="mt-1">
                    <Tag color={(device.status === "active" || device.status === "online") ? "green" : "grey"}>
                      {device.status || "—"}
                    </Tag>
                  </div>
                </div>

                {/* Last Connected */}
                <div className="space-y-1">
                  <Text type="tertiary" strong>{t("last_connected", { ns: "agents" })}</Text>
                  <Text size="normal" style={{ display: 'block' }}>
                    {device.last_connected_at
                      ? formatTimestamp(device.last_connected_at)
                      : "—"}
                  </Text>
                </div>

                {/* Created At */}
                <div className="space-y-1">
                  <Text type="tertiary" strong>{t("binding_date", { ns: "agents" })}</Text>
                  <Text size="normal" style={{ display: 'block' }}>{formatTimestamp(device.created_at)}</Text>
                </div>

                {/* Updated At */}
                <div className="space-y-1">
                  <Text type="tertiary" strong>{t("last_updated", { ns: "agents" })}</Text>
                  <Text size="normal" style={{ display: 'block' }}>{formatTimestamp(device.updated_at)}</Text>
                </div>
              </div>
            </Card>
          </TabPane>

          {/* Agents Tab */}
          <TabPane tab={
            <span>
              <Bot className="h-4 w-4 mr-2 inline-block" />
              Agents
            </span>
          } itemKey="agents"
          >
            <div className="pt-4">
              <AgentDeviceManager
                deviceId={deviceId!}
                deviceName={device.device_name ?? undefined}
              />
            </div>
          </TabPane>
        </Tabs>
      </div>

      {/* Edit Device Dialog */}
      <EditDeviceDialog
        open={isEditDialogOpen}
        onOpenChange={setIsEditDialogOpen}
        device={device}
        onSubmit={handleEditDeviceSubmit}
        isLoading={isUpdating}
      />
    </>
  );
}
