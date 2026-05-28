/**
 * Flash Dialog Component - Semi Design implementation
 * Shows WebSerial flash progress with logs
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
    Usb,
    Loader2,
    Check,
    AlertCircle,
    RefreshCw,
    ChevronDown,
    ChevronUp,
} from "lucide-react";

import { Modal, Button, Progress, Typography } from "@douyinfe/semi-ui";
import { cn } from "@/lib/utils";

import { useWebSerialFlash } from "./hooks/useWebSerialFlash";

const { Title, Text } = Typography;

interface FlashDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    binaryData: Uint8Array | null;
    flashAddress?: number;
    deviceName?: string;
}

// Stage icons and colors
const stageConfig: Record<string, { icon: React.ElementType; color: string; bgColor: string }> = {
    idle: { icon: Usb, color: "text-gray-500", bgColor: "bg-gray-100" },
    connecting: { icon: Loader2, color: "text-blue-500", bgColor: "bg-blue-100" },
    erasing: { icon: Loader2, color: "text-orange-500", bgColor: "bg-orange-100" },
    writing: { icon: Loader2, color: "text-yellow-500", bgColor: "bg-yellow-100" },
    verifying: { icon: Loader2, color: "text-purple-500", bgColor: "bg-purple-100" },
    done: { icon: Check, color: "text-green-500", bgColor: "bg-green-100" },
    error: { icon: AlertCircle, color: "text-red-500", bgColor: "bg-red-100" },
};

export function FlashDialog({
    open,
    onOpenChange,
    binaryData,
    flashAddress = 0x0,
    deviceName,
}: FlashDialogProps) {
    const { t } = useTranslation(["devices", "common"]);
    const [showLogs, setShowLogs] = useState(false);

    const {
        isSupported,
        isConnected,
        chipInfo,
        flashProgress,
        connect,
        disconnect,
        flash,
        reset,
        logs,
    } = useWebSerialFlash({ flashAddress });

    // Auto-flash when connected and have binary data
    useEffect(() => {
        if (isConnected && binaryData && flashProgress.stage === "idle") {
            const timeout = setTimeout(() => {
                flash(binaryData, flashAddress);
            }, 500);
            return () => clearTimeout(timeout);
        }
    }, [isConnected, binaryData, flashProgress.stage, flash, flashAddress]);

    // Reset on close
    useEffect(() => {
        if (!open) {
            reset();
        }
    }, [open, reset]);

    const handleConnect = async () => {
        await connect();
    };

    const handleClose = async () => {
        if (isConnected) {
            await disconnect();
        }
        onOpenChange(false);
    };

    const config = stageConfig[flashProgress.stage] || stageConfig.idle;
    const Icon = config.icon;
    const isAnimating = ["connecting", "erasing", "writing", "verifying"].includes(flashProgress.stage);
    const canClose = flashProgress.stage === "idle" || flashProgress.stage === "done" || flashProgress.stage === "error";

    return (
        <Modal
            title={
                <div className="flex items-center gap-2">
                    <Usb className="h-5 w-5" />
                    <Title heading={5} className="!mb-0">
                        {t("display.flash_title", "Flash to Device")}
                    </Title>
                </div>
            }
            visible={open}
            onCancel={canClose ? handleClose : undefined}
            closable={canClose}
            maskClosable={canClose}
            footer={null}
            width={420}
        >
            <Text type="tertiary" className="block mb-4">
                {deviceName
                    ? t("display.flash_desc_device", "Flash display config to {{name}}", { name: deviceName })
                    : t("display.flash_desc", "Flash display configuration via WebSerial")}
            </Text>

            {/* Browser Support Check */}
            {!isSupported && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                    <div className="flex items-start gap-2">
                        <AlertCircle className="h-5 w-5 mt-0.5" />
                        <div>
                            <Text strong className="block">
                                {t("display.webserial_not_supported", "WebSerial không được hỗ trợ")}
                            </Text>
                            <Text size="small" className="mt-1 block">
                                {t("display.use_chrome", "Vui lòng sử dụng Chrome, Edge hoặc Opera trên desktop.")}
                            </Text>
                        </div>
                    </div>
                </div>
            )}

            {/* Main Content */}
            {isSupported && (
                <div className="space-y-4">
                    {/* Status Icon */}
                    <div className="flex flex-col items-center py-4">
                        <div
                            className={cn(
                                "w-16 h-16 rounded-full flex items-center justify-center",
                                config.bgColor
                            )}
                        >
                            <Icon
                                className={cn(
                                    "h-8 w-8",
                                    config.color,
                                    isAnimating && "animate-spin"
                                )}
                            />
                        </div>
                        <Text strong className="mt-3 block">{flashProgress.message}</Text>
                        {chipInfo && (
                            <Text type="tertiary" size="small">
                                {t("display.chip_detected", "Chip: {{chip}}", { chip: chipInfo })}
                            </Text>
                        )}
                    </div>

                    {/* Progress Bar */}
                    <Progress percent={flashProgress.progress} showInfo />

                    {/* Logs Toggle */}
                    <button
                        onClick={() => setShowLogs(!showLogs)}
                        className="w-full flex items-center justify-between text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors py-2"
                    >
                        <span>{t("display.show_logs", "Hiển thị logs")}</span>
                        {showLogs ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>

                    {/* Logs */}
                    {showLogs && (
                        <div className="bg-gray-900 text-gray-100 rounded-lg p-3 h-40 overflow-y-auto font-mono text-xs">
                            {logs.length === 0 ? (
                                <p className="text-gray-500">No logs yet...</p>
                            ) : (
                                logs.map((log, i) => (
                                    <div key={i} className="whitespace-pre-wrap">
                                        {log}
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    {/* Binary Info */}
                    {binaryData && (
                        <Text type="tertiary" size="small" className="block text-center">
                            {t("display.binary_size", "Size: {{size}} bytes", {
                                size: binaryData.length.toLocaleString(),
                            })}
                            {" | "}
                            {t("display.flash_address", "Address: 0x{{address}}", {
                                address: flashAddress.toString(16).toUpperCase(),
                            })}
                        </Text>
                    )}
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 mt-4">
                {flashProgress.stage === "idle" && !isConnected && (
                    <>
                        <Button onClick={handleClose} className="flex-1">
                            {t("common:cancel", "Hủy")}
                        </Button>
                        <Button
                            theme="solid"
                            onClick={handleConnect}
                            className="flex-1"
                            disabled={!isSupported}
                            icon={<Usb className="h-4 w-4" />}
                        >
                            {t("display.connect", "Kết nối")}
                        </Button>
                    </>
                )}

                {flashProgress.stage === "done" && (
                    <div className="w-full space-y-3">
                        <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                            <Text strong className="block mb-1">✅ Flash thành công!</Text>
                            <Text size="small">
                                Nhấn nút <strong>Reset</strong> trên thiết bị hoặc rút/cắm lại USB để áp dụng cấu hình mới.
                            </Text>
                        </div>
                        <Button theme="solid" onClick={handleClose} className="w-full" icon={<Check className="h-4 w-4" />}>
                            {t("common:done", "Hoàn tất")}
                        </Button>
                    </div>
                )}

                {flashProgress.stage === "error" && (
                    <>
                        <Button onClick={handleClose} className="flex-1">
                            {t("common:close", "Đóng")}
                        </Button>
                        <Button theme="solid" onClick={handleConnect} className="flex-1" icon={<RefreshCw className="h-4 w-4" />}>
                            {t("display.retry", "Thử lại")}
                        </Button>
                    </>
                )}

                {isAnimating && (
                    <Text type="tertiary" size="small" className="w-full text-center">
                        {t("display.do_not_disconnect", "Không ngắt kết nối thiết bị...")}
                    </Text>
                )}
            </div>
        </Modal>
    );
}

export default FlashDialog;
