import { useState, useRef, useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  Unplug,
  Usb,
  Loader2,
  Trash2,
  Upload,
  Cpu
} from "lucide-react";
import {
  Button,
  Card,
  Select,
  Input,
  Checkbox,
  Banner,
  Typography,
  Tag,
  Modal
} from "@douyinfe/semi-ui";
import {
  IconAlertTriangle,
  IconInfoCircle,
  IconRefresh,
  IconDelete
} from "@douyinfe/semi-icons";
import { PageHead } from "@/components";

// Web Serial types are declared globally in src/types/web-serial.d.ts

// Flash address constants
const FLASH_ADDRESSES = {
  BOOTLOADER: 0x1000,
  PARTITION_TABLE: 0x8000,
  APP: 0x10000,
};

// Baud rate options
const BAUD_RATES = [115200, 230400, 460800, 921600] as const;

// Flash modes
const FLASH_MODES = [
  { value: "keep", label: "Keep" },
  { value: "qio", label: "QIO" },
  { value: "qout", label: "QOUT" },
  { value: "dio", label: "DIO" },
  { value: "dout", label: "DOUT" },
];

interface FirmwareFile {
  file: File;
  address: number;
  data?: Uint8Array;
}

interface FlashProgress {
  fileIndex: number;
  written: number;
  total: number;
  percentage: number;
}

type ConnectionStatus = "disconnected" | "connecting" | "connected" | "flashing" | "erasing";

// ESPLoader types (from esptool-js)
interface ESPLoaderInstance {
  main(): Promise<string>;
  flashId(): Promise<number>;
  eraseFlash(): Promise<void>;
  writeFlash(options: {
    fileArray: Array<{ data: string; address: number }>;
    flashSize: string;
    flashMode: string;
    flashFreq: string;
    eraseAll: boolean;
    compress: boolean;
    reportProgress: (fileIndex: number, written: number, total: number) => void;
    calculateMD5Hash: (image: string) => string;
  }): Promise<void>;
  hardReset(): Promise<void>;
  softReset(): Promise<void>;
  chip: {
    CHIP_NAME: string;
    CHIP_DETECT_MAGIC_VALUE: number[];
  };
}

interface TransportInstance {
  disconnect(): Promise<void>;
  connect(baudRate?: number): Promise<void>;
  setDTR(value: boolean): Promise<void>;
}

const { Title, Text } = Typography;

export function FirmwareFlasherPage() {
  useTranslation(["devices", "common"]);

  // State
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [chipInfo, setChipInfo] = useState<string>("");
  const [logs, setLogs] = useState<string[]>([]);
  const [firmwareFiles, setFirmwareFiles] = useState<FirmwareFile[]>([]);
  const [flashProgress, setFlashProgress] = useState<FlashProgress | null>(null);
  const [baudRate, setBaudRate] = useState<number>(921600);
  const [flashMode, setFlashMode] = useState<string>("keep");
  const [eraseBeforeFlash, setEraseBeforeFlash] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  // Refs
  const espLoaderRef = useRef<ESPLoaderInstance | null>(null);
  const transportRef = useRef<TransportInstance | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check WebSerial support
  const isWebSerialSupported = "serial" in navigator;

  // Log helper
  const addLog = useCallback((message: string, type: "info" | "success" | "error" | "warn" = "info") => {
    const timestamp = new Date().toLocaleTimeString();
    const prefix = type === "error" ? "❌" : type === "success" ? "✅" : type === "warn" ? "⚠️" : "ℹ️";
    setLogs(prev => [...prev, `[${timestamp}] ${prefix} ${message}`]);
  }, []);

  // Scroll logs to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Load esptool-js dynamically
  const loadEsptool = useCallback(async () => {
    try {
      // Dynamic import from CDN - TypeScript doesn't understand URL imports
      // @ts-expect-error Dynamic import from CDN
      const module = await import(/* @vite-ignore */ "https://unpkg.com/esptool-js@0.5.4/bundle.js");
      return module;
    } catch (err) {
      addLog("Không thể tải esptool-js library", "error");
      throw err;
    }
  }, [addLog]);

  // Connect to ESP32
  const handleConnect = useCallback(async () => {
    if (!isWebSerialSupported) {
      setError("Trình duyệt không hỗ trợ WebSerial API. Vui lòng sử dụng Chrome hoặc Edge phiên bản 89+");
      return;
    }

    setError("");
    setConnectionStatus("connecting");
    addLog("Đang kết nối với thiết bị...");

    try {
      // Request serial port
      const port = await navigator.serial!.requestPort();

      // Load esptool-js
      const esptool = await loadEsptool();

      // Create transport
      const transport = new esptool.Transport(port, true);
      transportRef.current = transport;

      // Terminal logger for esptool
      const terminal = {
        clean: () => { },
        writeLine: (data: string) => addLog(data),
        write: (data: string) => {
          if (data.trim()) addLog(data);
        },
      };

      // Create ESPLoader instance
      const loader = new esptool.ESPLoader({
        transport,
        baudrate: baudRate,
        terminal,
        romBaudrate: 115200,
      });

      // Connect and detect chip
      const chipName = await loader.main();
      espLoaderRef.current = loader;

      setChipInfo(chipName);
      setConnectionStatus("connected");
      addLog(`Đã kết nối với ${chipName}`, "success");

    } catch (err) {
      const message = err instanceof Error ? err.message : "Lỗi không xác định";
      addLog(`Lỗi kết nối: ${message}`, "error");
      setError(message);
      setConnectionStatus("disconnected");
      espLoaderRef.current = null;
      transportRef.current = null;
    }
  }, [isWebSerialSupported, baudRate, addLog, loadEsptool]);

  // Disconnect
  const handleDisconnect = useCallback(async () => {
    try {
      if (transportRef.current) {
        await transportRef.current.disconnect();
      }
      addLog("Đã ngắt kết nối", "info");
    } catch (err) {
      addLog("Lỗi khi ngắt kết nối", "warn");
    } finally {
      espLoaderRef.current = null;
      transportRef.current = null;
      setConnectionStatus("disconnected");
      setChipInfo("");
    }
  }, [addLog]);

  // Handle file selection
  const handleFileSelect = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files?.length) return;

    const newFiles: FirmwareFile[] = [];

    for (const file of Array.from(files)) {
      const data = new Uint8Array(await file.arrayBuffer());

      // Auto-detect address based on filename
      let address = FLASH_ADDRESSES.APP;
      const lowerName = file.name.toLowerCase();

      if (lowerName.includes("bootloader")) {
        address = FLASH_ADDRESSES.BOOTLOADER;
      } else if (lowerName.includes("partition")) {
        address = FLASH_ADDRESSES.PARTITION_TABLE;
      }

      newFiles.push({ file, address, data });
      addLog(`Đã thêm file: ${file.name} (${(file.size / 1024).toFixed(2)} KB) @ 0x${address.toString(16)}`);
    }

    setFirmwareFiles(prev => [...prev, ...newFiles]);

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [addLog]);

  // Remove firmware file
  const handleRemoveFile = useCallback((index: number) => {
    setFirmwareFiles(prev => {
      const file = prev[index];
      addLog(`Đã xóa file: ${file.file.name}`);
      return prev.filter((_, i) => i !== index);
    });
  }, [addLog]);

  // Update file address
  const handleAddressChange = useCallback((index: number, addressHex: string) => {
    const address = parseInt(addressHex, 16);
    if (isNaN(address)) return;

    setFirmwareFiles(prev => prev.map((f, i) =>
      i === index ? { ...f, address } : f
    ));
  }, []);

  // Convert Uint8Array to binary string for esptool
  const uint8ArrayToBinaryString = (data: Uint8Array): string => {
    let binary = "";
    for (let i = 0; i < data.length; i++) {
      binary += String.fromCharCode(data[i]);
    }
    return binary;
  };

  // Simple MD5 placeholder (esptool-js handles this internally)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const calculateMD5Hash = (_image: string): string => {
    // Return empty string - esptool-js will calculate internally if needed
    return "";
  };

  // Flash firmware
  const handleFlash = useCallback(async () => {
    if (!espLoaderRef.current) {
      setError("Chưa kết nối với thiết bị");
      return;
    }

    if (firmwareFiles.length === 0) {
      setError("Vui lòng chọn ít nhất một file firmware");
      return;
    }

    setError("");
    setConnectionStatus("flashing");
    addLog("Bắt đầu flash firmware...");

    try {
      const loader = espLoaderRef.current;

      // Erase flash if requested
      if (eraseBeforeFlash) {
        setConnectionStatus("erasing");
        addLog("Đang xóa flash...");
        await loader.eraseFlash();
        addLog("Đã xóa flash", "success");
        setConnectionStatus("flashing");
      }

      // Prepare file array for esptool
      const fileArray = firmwareFiles.map(f => ({
        data: uint8ArrayToBinaryString(f.data!),
        address: f.address,
      }));

      // Flash with progress
      await loader.writeFlash({
        fileArray,
        flashSize: "keep",
        flashMode: flashMode,
        flashFreq: "keep",
        eraseAll: false,
        compress: true,
        reportProgress: (fileIndex: number, written: number, total: number) => {
          const percentage = Math.round((written / total) * 100);
          setFlashProgress({ fileIndex, written, total, percentage });

          if (written === total) {
            const fileName = firmwareFiles[fileIndex]?.file.name || `File ${fileIndex + 1}`;
            addLog(`Hoàn thành flash: ${fileName}`, "success");
          }
        },
        calculateMD5Hash,
      });

      addLog("Flash firmware hoàn tất!", "success");

      // Reset device using transport DTR signals (reference: TienHuyIoT/esp_web_flasher)
      try {
        addLog("Đang reset thiết bị...");
        const transport = transportRef.current;

        if (transport) {
          // Disconnect then reconnect with console baudrate for reset
          await transport.disconnect();
          await transport.connect(115200);

          // Toggle DTR to trigger hardware reset
          await transport.setDTR(false);
          await new Promise(resolve => setTimeout(resolve, 100));
          await transport.setDTR(true);

          addLog("Thiết bị đã được reset", "success");
        } else {
          addLog("Không thể tự động reset - vui lòng reset thiết bị thủ công", "warn");
        }
      } catch (resetErr) {
        // setSignals may fail on some USB-Serial chips (e.g., CH340, CP210x without DTR)
        const resetMessage = resetErr instanceof Error ? resetErr.message : "Lỗi reset";
        addLog(`Reset tự động thất bại: ${resetMessage}. Vui lòng nhấn nút RST/EN trên board`, "warn");
      }

      setConnectionStatus("connected");
      setFlashProgress(null);

    } catch (err) {
      const message = err instanceof Error ? err.message : "Lỗi không xác định";
      addLog(`Lỗi flash: ${message}`, "error");
      setError(message);
      setConnectionStatus("connected");
      setFlashProgress(null);
    }
  }, [espLoaderRef, firmwareFiles, eraseBeforeFlash, flashMode, addLog]);

  // Erase flash
  const handleEraseFlash = useCallback(async () => {
    if (!espLoaderRef.current) {
      setError("Chưa kết nối với thiết bị");
      return;
    }

    Modal.confirm({
      title: "Xác nhận xóa Flash",
      content: "Bạn có chắc chắn muốn xóa toàn bộ flash? Dữ liệu sẽ không thể khôi phục!",
      okType: "danger",
      okText: "Xóa toàn bộ",
      cancelText: "Hủy",
      centered: true,
      onOk: async () => {
        setError("");
        setConnectionStatus("erasing");
        addLog("Đang xóa toàn bộ flash...");

        try {
          await espLoaderRef.current!.eraseFlash();
          addLog("Đã xóa toàn bộ flash", "success");
          setConnectionStatus("connected");
        } catch (err) {
          const message = err instanceof Error ? err.message : "Lỗi không xác định";
          addLog(`Lỗi xóa flash: ${message}`, "error");
          setError(message);
          setConnectionStatus("connected");
        }
      },
    });
  }, [addLog]);

  // Clear logs
  const handleClearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  // Render connection status badge
  const renderStatusBadge = () => {
    const statusConfig = {
      disconnected: { icon: Unplug, color: "grey", label: "Chưa kết nối" },
      connecting: { icon: Loader2, color: "orange", label: "Đang kết nối..." },
      connected: { icon: Usb, color: "green", label: "Đã kết nối" },
      flashing: { icon: Loader2, color: "blue", label: "Đang flash..." },
      erasing: { icon: Loader2, color: "orange", label: "Đang xóa..." },
    };

    const config = statusConfig[connectionStatus];
    const Icon = config.icon;
    const isAnimating = ["connecting", "flashing", "erasing"].includes(connectionStatus);

    return (
      <div className="flex items-center gap-2">
        {/* @ts-ignore */}
        <Icon className={`${isAnimating ? "animate-spin" : ""} w-4 h-4`} />
        {/* @ts-ignore */}
        <Tag color={config.color} type="solid">{config.label}</Tag>
        {chipInfo && connectionStatus === "connected" && (
          <Text type="secondary" size="small">({chipInfo})</Text>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6 p-6">
      <PageHead
        title="ESP32 Web Flasher"
        description="Flash firmware lên ESP32 trực tiếp từ trình duyệt qua WebSerial"
      />

      {/* WebSerial not supported alert */}
      {!isWebSerialSupported && (
        <Banner
          type="danger"
          icon={<IconAlertTriangle />}
          description="Trình duyệt của bạn không hỗ trợ WebSerial API. Vui lòng sử dụng Google Chrome hoặc Microsoft Edge phiên bản 89 trở lên."
        />
      )}

      {/* Error alert */}
      {error && (
        <Banner
          type="danger"
          icon={<IconAlertTriangle />}
          description={error}
        />
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left column - Connection & Settings */}
        <div className="space-y-6">
          {/* Connection Card */}
          <Card
            title={
              <div className="flex items-center gap-2">
                <Cpu className="h-5 w-5" />
                <Title heading={6} style={{ margin: 0 }}>Kết nối thiết bị</Title>
              </div>
            }
          >
            <div className="space-y-4">
              {/* Status */}
              <div className="h-12 w-12 rounded-full bg-purple-100 flex items-center justify-center mx-auto mb-4">
                <Cpu className="h-6 w-6 text-purple-600" />
              </div>
              <div className="flex items-center justify-between">
                <Text type="secondary">Trạng thái:</Text>
                {renderStatusBadge()}
              </div>

              {/* Baud Rate */}
              <div className="space-y-2">
                <Text strong>Baud Rate</Text>
                <Select
                  value={baudRate}
                  onChange={(v) => setBaudRate(v as number)}
                  disabled={connectionStatus !== "disconnected"}
                  style={{ width: '100%' }}
                  optionList={BAUD_RATES.map(rate => ({ value: rate, label: `${rate.toLocaleString()} bps` }))}
                />
              </div>

              {/* Connect/Disconnect buttons */}
              <div className="flex gap-2">
                {connectionStatus === "disconnected" ? (
                  <Button
                    block
                    theme="solid"
                    type="primary"
                    onClick={handleConnect}
                    disabled={!isWebSerialSupported}
                    icon={<Usb className="h-4 w-4" />}
                  >
                    Kết nối
                  </Button>
                ) : (
                  <Button
                    block
                    theme="light"
                    type="warning"
                    onClick={handleDisconnect}
                    disabled={connectionStatus === "flashing" || connectionStatus === "erasing"}
                    icon={<Unplug className="h-4 w-4" />}
                  >
                    Ngắt kết nối
                  </Button>
                )}
              </div>
            </div>
          </Card>

          {/* Flash Settings Card */}
          <Card title={<Title heading={6}>Cài đặt Flash</Title>}>
            <div className="space-y-4">
              {/* Flash Mode */}
              <div className="space-y-2">
                <Text strong>Flash Mode</Text>
                <Select
                  value={flashMode}
                  onChange={(v) => setFlashMode(v as string)}
                  disabled={connectionStatus !== "connected"}
                  style={{ width: '100%' }}
                  optionList={FLASH_MODES}
                />
              </div>

              {/* Erase before flash */}
              <div className="flex items-center space-x-2 pt-2">
                <Checkbox
                  checked={eraseBeforeFlash}
                  onChange={(e) => setEraseBeforeFlash(!!e.target.checked)}
                  disabled={connectionStatus !== "connected"}
                >
                  Xóa flash trước khi ghi
                </Checkbox>
              </div>

              {/* Erase Flash button */}
              <Button
                type="danger"
                theme="light"
                block
                onClick={handleEraseFlash}
                disabled={connectionStatus !== "connected"}
                icon={<Trash2 className="h-4 w-4" />}
              >
                Xóa toàn bộ Flash
              </Button>
            </div>
          </Card>
        </div>

        {/* Middle column - Firmware Files */}
        <div className="space-y-6">
          <Card
            title={
              <div className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                <div>
                  <Title heading={6} style={{ margin: 0 }}>Firmware Files</Title>
                  <Text size="small" type="tertiary">Thêm các file .bin để flash lên thiết bị</Text>
                </div>
              </div>
            }
          >
            <div className="space-y-4">
              {/* File input */}
              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".bin"
                  multiple
                  onChange={(e) => {
                    // @ts-ignore
                    handleFileSelect(e)
                  }}
                  style={{ display: 'none' }}
                />

              </div>

              {/* File list */}
              <div className="space-y-2">
                {firmwareFiles.length === 0 ? (
                  <div className="rounded-lg border border-dashed p-6 text-center text-gray-500 cursor-pointer hover:bg-gray-50 transition-colors" onClick={() => fileInputRef.current?.click()}>
                    <Upload className="mx-auto h-8 w-8 mb-2" />
                    <p className="text-sm">Chưa có file nào được chọn</p>
                    <p className="text-xs">Click để chọn file .bin</p>
                  </div>
                ) : (
                  firmwareFiles.map((fw, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 rounded-lg border p-3 bg-gray-50"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">
                          {fw.file.name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {(fw.file.size / 1024).toFixed(2)} KB
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Input
                          value={`0x${fw.address.toString(16)}`}
                          onChange={(v) => handleAddressChange(index, v.replace("0x", ""))}
                          className="w-24 font-mono"
                          size="small"
                          placeholder="0x10000"
                        />
                        <Button
                          theme="borderless"
                          type="danger"
                          icon={<IconDelete />}
                          onClick={() => handleRemoveFile(index)}
                        />
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Quick address buttons */}
              <div className="flex flex-wrap gap-2">
                <Button
                  theme="light"
                  onClick={() => fileInputRef.current?.click()}
                  icon={<Upload className="h-3 w-3" />}
                >
                  Thêm file
                </Button>
              </div>

              {/* Flash button */}
              <Button
                block
                size="large"
                theme="solid"
                onClick={handleFlash}
                disabled={
                  connectionStatus !== "connected" ||
                  firmwareFiles.length === 0
                }
                loading={connectionStatus === "flashing"}
              >
                {connectionStatus === "flashing" ? "Đang flash..." : (
                  <>
                    <Cpu className="h-4 w-4 text-purple-600" /> Flash Firmware
                  </>
                )}
              </Button>

              {/* Flash progress */}
              {flashProgress && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <Text>Tiến độ:</Text>
                    <Text>{Math.round(flashProgress.percentage)}%</Text>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-purple-600 transition-all duration-300"
                      style={{ width: `${flashProgress.percentage}%` }}
                    />
                  </div>
                </div>
              )}

            </div>
          </Card>

          {/* Info Card */}
          <Banner
            type="info"
            icon={<IconInfoCircle />}
            description={
              <div className="text-xs space-y-1 mt-1">
                <p>• Địa chỉ mặc định: Bootloader (0x000), Partition (0x8000), App (0x10000)</p>
                <p>• Nhấn giữ nút BOOT trên ESP32 khi kết nối nếu cần</p>
                <p>• Đảm bảo không có chương trình nào khác đang sử dụng cổng COM</p>
              </div>
            }
            title="Hướng dẫn"
          />
        </div>

        {/* Right column - Logs */}
        <div>
          <Card
            className="h-full"
            title={<Title heading={6}>Console Log</Title>}
            headerExtraContent={
              <Button
                theme="light"
                size="small"
                onClick={handleClearLogs}
                icon={<IconRefresh />}
              >
                Xóa log
              </Button>
            }
          >
            <div className="h-[500px] overflow-y-auto rounded-lg bg-gray-900 text-green-400 p-3 font-mono text-xs">
              {logs.length === 0 ? (
                <p className="text-gray-500">Chưa có log nào...</p>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className="py-0.5 whitespace-pre-wrap break-all border-b border-gray-800 last:border-0">
                    {log}
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default FirmwareFlasherPage;
