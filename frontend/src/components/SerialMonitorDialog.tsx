/**
 * SerialMonitorDialog - Semi Design implementation
 */

import { useState, useRef, useCallback, useEffect, memo } from "react";
import { useTranslation } from "react-i18next";
import {
  Terminal,
  Usb,
  Unplug,
  Trash2,
  Download,
  Play,
  Pause,
  Settings,
} from "lucide-react";

import { Modal, Button, Select, Typography } from "@douyinfe/semi-ui";
import { cn } from "@/lib/utils";

const { Title, Text } = Typography;

// Common baud rates for ESP32 monitor
const BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600] as const;

// Local Web Serial port type (simplified)
interface LocalSerialPort {
  open(options: { baudRate: number }): Promise<void>;
  close(): Promise<void>;
  readable: ReadableStream<Uint8Array> | null;
  writable: WritableStream<Uint8Array> | null;
}

interface SerialMonitorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deviceName?: string;
}

type ConnectionState = "disconnected" | "connecting" | "connected";

const SerialMonitorDialogComponent = ({
  open,
  onOpenChange,
  deviceName,
}: SerialMonitorDialogProps) => {
  const { t } = useTranslation(["devices", "common"]);

  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [baudRate, setBaudRate] = useState<number>(115200);
  const [logs, setLogs] = useState<string[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const portRef = useRef<LocalSerialPort | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const isReadingRef = useRef(false);

  const isWebSerialSupported = "serial" in navigator;

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

  useEffect(() => {
    if (!isPaused) {
      logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, isPaused]);

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

  const handleConnect = useCallback(async () => {
    if (!isWebSerialSupported) {
      addLog("Trình duyệt không hỗ trợ WebSerial API", "error");
      return;
    }

    try {
      setConnectionState("connecting");
      addLog(`Đang kết nối với baudrate ${baudRate}...`, "info");

      const port = await navigator.serial!.requestPort();

      await port.open({ baudRate: baudRate });
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

  const handleClearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  const handleDownloadLogs = useCallback(() => {
    const content = logs.join("\n");
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `serial-monitor-${deviceName || "device"}-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [logs, deviceName]);

  useEffect(() => {
    if (!open && connectionState === "connected") {
      handleDisconnect();
    }
  }, [open, connectionState, handleDisconnect]);

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

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <Terminal className="h-5 w-5" />
          <Title heading={5} className="!mb-0">
            Serial Monitor {deviceName && `- ${deviceName}`}
          </Title>
        </div>
      }
      visible={open}
      onCancel={() => onOpenChange(false)}
      width={900}
      style={{ top: 40 }}
      bodyStyle={{ height: "calc(80vh - 100px)", display: "flex", flexDirection: "column" }}
      footer={null}
    >
      <Text type="tertiary" className="block mb-3">
        {t("serial_monitor_desc", "Xem log từ thiết bị ESP32 qua cổng Serial (tương tự lệnh idf.py monitor)")}
      </Text>

      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap mb-3">
        {connectionState === "disconnected" ? (
          <Button onClick={handleConnect} icon={<Usb className="h-4 w-4" />}>
            {t("connect", "Kết nối")}
          </Button>
        ) : connectionState === "connecting" ? (
          <Button disabled icon={<Usb className="h-4 w-4 animate-pulse" />}>
            {t("connecting", "Đang kết nối...")}
          </Button>
        ) : (
          <Button type="danger" onClick={handleDisconnect} icon={<Unplug className="h-4 w-4" />}>
            {t("disconnect", "Ngắt kết nối")}
          </Button>
        )}

        <Button
          onClick={() => setIsPaused(!isPaused)}
          icon={isPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
        >
          {isPaused ? t("resume", "Tiếp tục") : t("pause", "Tạm dừng")}
        </Button>

        <Button onClick={handleClearLogs} icon={<Trash2 className="h-4 w-4" />}>
          {t("clear", "Xóa")}
        </Button>

        <Button
          onClick={handleDownloadLogs}
          icon={<Download className="h-4 w-4" />}
          disabled={logs.length === 0}
        >
          {t("download", "Tải về")}
        </Button>

        <Button
          onClick={() => setShowSettings(!showSettings)}
          theme="borderless"
          icon={<Settings className="h-4 w-4" />}
          style={{ marginLeft: "auto" }}
        />

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
        <div className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg mb-3">
          <div className="flex items-center gap-2">
            <Text size="small">Baud Rate:</Text>
            <Select
              value={String(baudRate)}
              onChange={(v) => setBaudRate(Number(v))}
              disabled={connectionState === "connected"}
              style={{ width: 120 }}
            >
              {BAUD_RATES.map((rate) => (
                <Select.Option key={rate} value={String(rate)}>
                  {rate.toLocaleString()}
                </Select.Option>
              ))}
            </Select>
          </div>

          {connectionState === "connected" && (
            <Text type="tertiary" size="small">
              * {t("disconnect_to_change", "Ngắt kết nối để thay đổi cài đặt")}
            </Text>
          )}
        </div>
      )}

      {/* WebSerial not supported warning */}
      {!isWebSerialSupported && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400 mb-3">
          <Text strong>Trình duyệt không hỗ trợ WebSerial API</Text>
          <Text type="tertiary" size="small" className="block mt-1">
            Vui lòng sử dụng Chrome, Edge hoặc Opera phiên bản mới nhất.
          </Text>
        </div>
      )}

      {/* Log output */}
      <div className="flex-1 min-h-0 bg-black rounded-lg overflow-hidden">
        <div className="h-full overflow-y-auto p-4 font-mono text-xs leading-relaxed">
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
      </div>

      {/* Footer info */}
      <div className="flex items-center justify-between mt-2">
        <Text type="tertiary" size="small">{logs.length} {t("lines", "dòng")}</Text>
        {isPaused && (
          <Text type="warning" size="small" strong>
            ⏸ {t("paused", "Đã tạm dừng")}
          </Text>
        )}
      </div>
    </Modal>
  );
};

export const SerialMonitorDialog = memo(SerialMonitorDialogComponent);
