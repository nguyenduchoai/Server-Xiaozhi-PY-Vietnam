/**
 * Display Customizer Dialog - Semi Design implementation
 * Main wizard for customizing ESP32 display appearance
 */

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
    Monitor,
    Settings2,
    Eye,
    ChevronLeft,
    ChevronRight,
    Download,
    Usb,
    Loader2,
    Check,
} from "lucide-react";

import { Modal, Button, Typography } from "@douyinfe/semi-ui";
import { cn } from "@/lib/utils";

// Hooks and Utils
import { useDisplayConfig } from "./hooks/useDisplayConfig";
import { packDisplayAssets, downloadBinary, generateFilename } from "./utils/assetPacker";

// Steps
import { SelectFeaturesStep } from "./steps/SelectFeaturesStep";
import { BackgroundStep } from "./steps/BackgroundStep";
import { ClockStep } from "./steps/ClockStep";
import { WeatherStep } from "./steps/WeatherStep";
import { EmojiStep } from "./steps/EmojiStep";
import { DisplayPreviewCanvas } from "./DisplayPreviewCanvas";
import { FlashDialog } from "./FlashDialog";

const { Title, Text } = Typography;

interface DisplayCustomizerDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    deviceId?: string;
    deviceName?: string;
    deviceBoard?: string;
    screenWidth?: number;
    screenHeight?: number;
    onFlash?: (data: Uint8Array) => void;
}

type WizardStep = "features" | "configure" | "preview";

const STEPS: { id: WizardStep; label: string; icon: React.ElementType }[] = [
    { id: "features", label: "Chọn tính năng", icon: Settings2 },
    { id: "configure", label: "Cấu hình", icon: Monitor },
    { id: "preview", label: "Xem trước", icon: Eye },
];

export function DisplayCustomizerDialog({
    open,
    onOpenChange,
    deviceName,
    deviceBoard,
    screenWidth = 320,
    screenHeight = 240,
    onFlash,
}: DisplayCustomizerDialogProps) {
    const { t } = useTranslation(["devices", "common"]);

    // Wizard state
    const [currentStep, setCurrentStep] = useState<WizardStep>("features");
    const [isGenerating, setIsGenerating] = useState(false);

    // Config state
    const {
        config,
        updateBackground,
        updateClock,
        updateWeather,
        updateEmoji,
        toggleFeature,
    } = useDisplayConfig({
        screenWidth,
        screenHeight,
        boardPreset: deviceBoard,
    });

    // Flash dialog state
    const [showFlashDialog, setShowFlashDialog] = useState(false);
    const [flashBinaryData, setFlashBinaryData] = useState<Uint8Array | null>(null);

    // Get current step index
    const currentStepIndex = STEPS.findIndex((s) => s.id === currentStep);

    // Navigation
    const canGoBack = currentStepIndex > 0;
    const canGoNext = currentStepIndex < STEPS.length - 1;
    const isLastStep = currentStepIndex === STEPS.length - 1;

    const goBack = useCallback(() => {
        if (canGoBack) {
            setCurrentStep(STEPS[currentStepIndex - 1].id);
        }
    }, [canGoBack, currentStepIndex]);

    const goNext = useCallback(() => {
        if (canGoNext) {
            setCurrentStep(STEPS[currentStepIndex + 1].id);
        }
    }, [canGoNext, currentStepIndex]);

    // Check if features step is valid
    const isFeaturesValid =
        config.enableBackground ||
        config.enableSlideshow ||
        config.enableClock ||
        config.enableWeather ||
        config.enableEmoji;

    // Generate and download binary
    const handleDownload = useCallback(async () => {
        setIsGenerating(true);
        try {
            const binary = await packDisplayAssets(config);
            const filename = generateFilename(config);
            downloadBinary(binary, filename);
        } catch (error) {
            console.error("Error generating binary:", error);
            alert(t("display.generate_error", "Có lỗi khi tạo file"));
        } finally {
            setIsGenerating(false);
        }
    }, [config, t]);

    // Flash to device - Open FlashDialog
    const handleFlash = useCallback(async () => {
        setIsGenerating(true);
        try {
            const binary = await packDisplayAssets(config);
            setFlashBinaryData(binary);
            setShowFlashDialog(true);
        } catch (error) {
            console.error("Error generating binary:", error);
            alert(t("display.generate_error", "Có lỗi khi tạo file"));
        } finally {
            setIsGenerating(false);
        }
    }, [config, t]);

    // Render step content
    const renderStepContent = () => {
        switch (currentStep) {
            case "features":
                return (
                    <SelectFeaturesStep
                        config={config}
                        onToggle={toggleFeature}
                    />
                );

            case "configure":
                return (
                    <div className="space-y-8">
                        {config.enableBackground && (
                            <BackgroundStep config={config} onUpdate={updateBackground} />
                        )}
                        {config.enableClock && (
                            <ClockStep config={config} onUpdate={updateClock} />
                        )}
                        {config.enableWeather && (
                            <WeatherStep config={config} onUpdate={updateWeather} />
                        )}
                        {config.enableEmoji && (
                            <EmojiStep config={config} onUpdate={updateEmoji} />
                        )}
                        {!config.enableBackground &&
                            !config.enableClock &&
                            !config.enableWeather &&
                            !config.enableEmoji && (
                                <div className="text-center text-gray-500 py-8">
                                    {t("display.no_configurable", "Không có tính năng nào cần cấu hình")}
                                </div>
                            )}
                    </div>
                );

            case "preview":
                return (
                    <div className="space-y-6">
                        {/* Preview Canvas */}
                        <div className="flex justify-center">
                            <DisplayPreviewCanvas
                                config={config}
                                scale={1.5}
                                className="shadow-xl"
                            />
                        </div>

                        {/* Config Summary */}
                        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
                            <Text strong className="block mb-2">
                                {t("display.config_summary", "Tóm tắt cấu hình")}
                            </Text>
                            <div className="grid grid-cols-2 gap-2 text-sm text-gray-500">
                                <div>Chip: <span className="text-gray-900 dark:text-gray-100">{config.chip.toUpperCase()}</span></div>
                                <div>Màn hình: <span className="text-gray-900 dark:text-gray-100">{config.screenWidth}x{config.screenHeight}</span></div>
                                <div>Nền: <span className="text-gray-900 dark:text-gray-100">{config.enableBackground ? "✓" : "✗"}</span></div>
                                <div>Đồng hồ: <span className="text-gray-900 dark:text-gray-100">{config.enableClock ? "✓" : "✗"}</span></div>
                                <div>Thời tiết: <span className="text-gray-900 dark:text-gray-100">{config.enableWeather ? "✓" : "✗"}</span></div>
                                <div>Emoji: <span className="text-gray-900 dark:text-gray-100">{config.enableEmoji ? "✓" : "✗"}</span></div>
                            </div>
                        </div>

                        {/* Action buttons */}
                        <div className="flex flex-col sm:flex-row gap-3">
                            <Button
                                className="flex-1"
                                onClick={handleDownload}
                                disabled={isGenerating}
                                icon={isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                            >
                                {t("display.download_bin", "Tải file .bin")}
                            </Button>

                            {onFlash && (
                                <Button
                                    theme="solid"
                                    className="flex-1"
                                    onClick={handleFlash}
                                    disabled={isGenerating}
                                    icon={isGenerating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Usb className="h-4 w-4" />}
                                >
                                    {t("display.flash_device", "Flash vào thiết bị")}
                                </Button>
                            )}
                        </div>
                    </div>
                );

            default:
                return null;
        }
    };

    return (
        <>
            <Modal
                title={
                    <div className="flex items-center gap-2">
                        <Monitor className="h-5 w-5" />
                        <Title heading={5} className="!mb-0">
                            {t("display.customize_display", "Tạo Theme")}
                        </Title>
                    </div>
                }
                visible={open}
                onCancel={() => onOpenChange(false)}
                footer={null}
                width={900}
                style={{ top: 40 }}
                bodyStyle={{ maxHeight: "calc(90vh - 120px)", overflowY: "auto" }}
            >
                <Text type="tertiary" className="block mb-4">
                    {deviceName
                        ? t("display.customize_for_device", "Thiết kế giao diện cho {{name}}", { name: deviceName })
                        : t("display.customize_generic", "Thiết kế giao diện hiển thị cho thiết bị ESP32")}
                </Text>

                {/* Step Indicator */}
                <div className="flex items-center justify-between mb-6 px-4">
                    {STEPS.map((step, index) => {
                        const isActive = step.id === currentStep;
                        const isCompleted = index < currentStepIndex;
                        const Icon = step.icon;

                        return (
                            <div key={step.id} className="flex items-center">
                                {/* Step circle */}
                                <button
                                    onClick={() => {
                                        if (index <= currentStepIndex || (index === 1 && isFeaturesValid)) {
                                            setCurrentStep(step.id);
                                        }
                                    }}
                                    disabled={index > currentStepIndex && !isFeaturesValid}
                                    className={cn(
                                        "flex items-center justify-center w-10 h-10 rounded-full transition-all",
                                        isActive
                                            ? "bg-blue-500 text-white"
                                            : isCompleted
                                                ? "bg-blue-100 text-blue-500"
                                                : "bg-gray-100 text-gray-400 dark:bg-gray-800",
                                        index <= currentStepIndex && "cursor-pointer hover:scale-105"
                                    )}
                                >
                                    {isCompleted ? (
                                        <Check className="h-5 w-5" />
                                    ) : (
                                        <Icon className="h-5 w-5" />
                                    )}
                                </button>

                                {/* Step label */}
                                <span
                                    className={cn(
                                        "ml-2 text-sm hidden sm:block",
                                        isActive ? "font-medium" : "text-gray-500"
                                    )}
                                >
                                    {step.label}
                                </span>

                                {/* Connector line */}
                                {index < STEPS.length - 1 && (
                                    <div
                                        className={cn(
                                            "h-0.5 w-8 sm:w-16 mx-2 sm:mx-4",
                                            index < currentStepIndex ? "bg-blue-500" : "bg-gray-200 dark:bg-gray-700"
                                        )}
                                    />
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* Step Content */}
                <div className="min-h-[400px] py-4">{renderStepContent()}</div>

                {/* Navigation */}
                <div className="flex justify-between pt-4 border-t">
                    <Button
                        onClick={goBack}
                        disabled={!canGoBack}
                        icon={<ChevronLeft className="h-4 w-4" />}
                    >
                        {t("common:back", "Quay lại")}
                    </Button>

                    <div className="flex gap-2">
                        <Button onClick={() => onOpenChange(false)}>
                            {t("common:cancel", "Hủy")}
                        </Button>

                        {!isLastStep ? (
                            <Button
                                theme="solid"
                                onClick={goNext}
                                disabled={currentStep === "features" && !isFeaturesValid}
                            >
                                {t("common:next", "Tiếp theo")}
                                <ChevronRight className="h-4 w-4 ml-1" />
                            </Button>
                        ) : null}
                    </div>
                </div>
            </Modal>

            {/* Flash Dialog */}
            <FlashDialog
                open={showFlashDialog}
                onOpenChange={setShowFlashDialog}
                binaryData={flashBinaryData}
                deviceName={deviceName}
            />
        </>
    );
}

export default DisplayCustomizerDialog;
