/**
 * Background Configuration Step - Semi Design implementation
 * Allows user to set background color or upload an image
 */

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Upload, Palette, Image as ImageIcon, X } from "lucide-react";
import { Button, Input, Radio, Typography } from "@douyinfe/semi-ui";
import type { BackgroundConfig, DisplayConfig } from "../utils/types";
import { resizeImage } from "../utils/imageConverter";
import { cn } from "@/lib/utils";

const { Text } = Typography;

interface BackgroundStepProps {
    config: DisplayConfig;
    onUpdate: (updates: Partial<BackgroundConfig>) => void;
}

// Preset colors
const COLOR_PRESETS = [
    { name: "Midnight", color: "#1a1a2e" },
    { name: "Ocean", color: "#0f3460" },
    { name: "Forest", color: "#1a4314" },
    { name: "Wine", color: "#4a1942" },
    { name: "Slate", color: "#334155" },
    { name: "Pure Black", color: "#000000" },
    { name: "Pure White", color: "#ffffff" },
    { name: "Warm Gray", color: "#44403c" },
];

export function BackgroundStep({ config, onUpdate }: BackgroundStepProps) {
    const { t } = useTranslation(["devices", "common"]);
    const [isUploading, setIsUploading] = useState(false);

    const { background, screenWidth, screenHeight } = config;

    // Handle image upload
    const handleImageUpload = useCallback(
        async (e: React.ChangeEvent<HTMLInputElement>) => {
            const file = e.target.files?.[0];
            if (!file) return;

            if (!file.type.startsWith("image/")) {
                alert(t("display.invalid_image", "Vui lòng chọn file hình ảnh"));
                return;
            }

            if (file.size > 5 * 1024 * 1024) {
                alert(t("display.image_too_large", "Hình ảnh quá lớn (tối đa 5MB)"));
                return;
            }

            setIsUploading(true);

            try {
                const resized = await resizeImage(file, screenWidth, screenHeight, "jpeg", 0.9);
                onUpdate({
                    mode: "image",
                    imageData: resized,
                });
            } catch (error) {
                console.error("Image upload error:", error);
                alert(t("display.upload_error", "Có lỗi khi tải hình ảnh"));
            } finally {
                setIsUploading(false);
            }
        },
        [screenWidth, screenHeight, onUpdate, t]
    );

    // Remove image
    const handleRemoveImage = useCallback(() => {
        onUpdate({
            mode: "color",
            imageData: undefined,
        });
    }, [onUpdate]);

    return (
        <div className="space-y-6">
            {/* Mode Selection */}
            <div>
                <Text strong size="small" className="block mb-3">
                    {t("display.bg_mode", "Loại nền")}
                </Text>
                <Radio.Group
                    value={background.mode}
                    onChange={(e) => onUpdate({ mode: e.target.value as "color" | "image" })}
                    direction="horizontal"
                >
                    <Radio value="color">
                        <span className="flex items-center gap-2">
                            <Palette className="h-4 w-4" />
                            {t("display.solid_color", "Màu đơn")}
                        </span>
                    </Radio>
                    <Radio value="image">
                        <span className="flex items-center gap-2">
                            <ImageIcon className="h-4 w-4" />
                            {t("display.custom_image", "Hình ảnh")}
                        </span>
                    </Radio>
                </Radio.Group>
            </div>

            {/* Color Selection */}
            {background.mode === "color" && (
                <div className="space-y-4">
                    <Text strong size="small" className="block">
                        {t("display.select_color", "Chọn màu nền")}
                    </Text>

                    {/* Color presets */}
                    <div className="grid grid-cols-4 sm:grid-cols-8 gap-2">
                        {COLOR_PRESETS.map((preset) => (
                            <button
                                key={preset.name}
                                onClick={() => onUpdate({ color: preset.color })}
                                className={cn(
                                    "w-full aspect-square rounded-lg border-2 transition-all",
                                    "hover:scale-105 hover:shadow-md",
                                    background.color === preset.color
                                        ? "border-blue-500 ring-2 ring-blue-500/30"
                                        : "border-transparent"
                                )}
                                style={{ backgroundColor: preset.color }}
                                title={preset.name}
                            />
                        ))}
                    </div>

                    {/* Custom color picker */}
                    <div className="flex items-center gap-3">
                        <input
                            type="color"
                            value={background.color}
                            onChange={(e) => onUpdate({ color: e.target.value })}
                            className="w-12 h-10 p-1 cursor-pointer rounded border"
                        />
                        <Input
                            value={background.color}
                            onChange={(value) => onUpdate({ color: String(value) })}
                            placeholder="#1a1a2e"
                            className="flex-1 font-mono"
                        />
                    </div>
                </div>
            )}

            {/* Image Upload */}
            {background.mode === "image" && (
                <div className="space-y-4">
                    {!background.imageData ? (
                        <label
                            className={cn(
                                "flex flex-col items-center justify-center",
                                "w-full h-48 rounded-xl border-2 border-dashed",
                                "cursor-pointer transition-colors",
                                "hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20",
                                isUploading ? "opacity-50 pointer-events-none" : ""
                            )}
                        >
                            <Upload className="h-10 w-10 text-gray-400 mb-3" />
                            <Text strong size="small">
                                {isUploading
                                    ? t("display.uploading", "Đang tải...")
                                    : t("display.click_to_upload", "Click để tải hình ảnh")}
                            </Text>
                            <Text type="tertiary" size="small" className="mt-1">
                                PNG, JPG, WEBP (tối đa 5MB)
                            </Text>
                            <Text type="tertiary" size="small">
                                {t("display.recommended_size", "Khuyến nghị: {{width}}x{{height}}px", {
                                    width: screenWidth,
                                    height: screenHeight,
                                })}
                            </Text>
                            <input
                                type="file"
                                accept="image/*"
                                onChange={handleImageUpload}
                                className="hidden"
                                disabled={isUploading}
                            />
                        </label>
                    ) : (
                        <div className="relative">
                            {/* Preview */}
                            <div
                                className="rounded-xl overflow-hidden border"
                                style={{
                                    aspectRatio: `${screenWidth}/${screenHeight}`,
                                    maxWidth: 400,
                                }}
                            >
                                <img
                                    src={background.imageData}
                                    alt="Background preview"
                                    className="w-full h-full object-cover"
                                />
                            </div>

                            {/* Remove button */}
                            <Button
                                type="danger"
                                theme="solid"
                                icon={<X className="h-4 w-4" />}
                                className="absolute top-2 right-2"
                                onClick={handleRemoveImage}
                            />

                            {/* Change button */}
                            <label className="absolute bottom-2 right-2">
                                <Button
                                    size="small"
                                    icon={<Upload className="h-3 w-3" />}
                                >
                                    {t("display.change_image", "Đổi ảnh")}
                                </Button>
                                <input
                                    type="file"
                                    accept="image/*"
                                    onChange={handleImageUpload}
                                    className="hidden"
                                />
                            </label>
                        </div>
                    )}

                    {/* Image fit options */}
                    {background.imageData && (
                        <div className="space-y-4">
                            <div>
                                <Text strong size="small" className="block mb-2">
                                    {t("display.image_fit", "Cách hiển thị")}
                                </Text>
                                <Radio.Group
                                    value={background.imageFit}
                                    onChange={(e) =>
                                        onUpdate({ imageFit: e.target.value as "cover" | "contain" | "stretch" })
                                    }
                                    direction="horizontal"
                                >
                                    <Radio value="cover">Lấp đầy</Radio>
                                    <Radio value="contain">Vừa khung</Radio>
                                    <Radio value="stretch">Kéo giãn</Radio>
                                </Radio.Group>
                            </div>

                            {/* Position controls for cover mode */}
                            {background.imageFit === "cover" && (
                                <div className="space-y-3 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                                    <Text strong size="small" className="block">
                                        {t("display.image_position", "Điều chỉnh vị trí hình")}
                                    </Text>
                                    <div className="space-y-2">
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs w-16 text-gray-500">Ngang</span>
                                            <input
                                                type="range"
                                                min="-1"
                                                max="1"
                                                step="0.1"
                                                value={background.offsetX || 0}
                                                onChange={(e) => onUpdate({ offsetX: parseFloat(e.target.value) })}
                                                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
                                            />
                                            <button
                                                onClick={() => onUpdate({ offsetX: 0 })}
                                                className="text-xs text-gray-500 hover:text-blue-500"
                                            >
                                                Reset
                                            </button>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs w-16 text-gray-500">Dọc</span>
                                            <input
                                                type="range"
                                                min="-1"
                                                max="1"
                                                step="0.1"
                                                value={background.offsetY || 0}
                                                onChange={(e) => onUpdate({ offsetY: parseFloat(e.target.value) })}
                                                className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-500"
                                            />
                                            <button
                                                onClick={() => onUpdate({ offsetY: 0 })}
                                                className="text-xs text-gray-500 hover:text-blue-500"
                                            >
                                                Reset
                                            </button>
                                        </div>
                                    </div>
                                    <Text type="tertiary" size="small">
                                        Kéo thanh trượt để điều chỉnh phần hình ảnh được hiển thị
                                    </Text>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default BackgroundStep;
