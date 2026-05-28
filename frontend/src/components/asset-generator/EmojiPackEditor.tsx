/**
 * EmojiPackEditor - Semi Design implementation
 * Component cho phép tùy chỉnh từng biểu cảm
 */

import { useState, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
    Upload,
    X,
    RotateCcw,
    Check,
    Image as ImageIcon,
} from "lucide-react";

import { Button, Tag, Select, Tooltip, Typography, Banner } from "@douyinfe/semi-ui";
import { cn } from "@/lib/utils";

import { EMOJI_EMOTIONS, EMOJI_PRESETS } from "./types";

const { Text } = Typography;

// Custom emoji data
export interface CustomEmojiData {
    file?: File;
    preview?: string; // ObjectURL for preview
    isCustom: boolean;
}

export type CustomEmojis = Record<string, CustomEmojiData>;

interface EmojiPackEditorProps {
    selectedPreset: string;
    onPresetChange: (preset: string) => void;
    customEmojis: CustomEmojis;
    onCustomEmojisChange: (emojis: CustomEmojis) => void;
    emojiSize: number;
    onEmojiSizeChange: (size: number) => void;
    screenWidth: number;
    screenHeight: number;
}

export function EmojiPackEditor({
    selectedPreset,
    onPresetChange,
    customEmojis,
    onCustomEmojisChange,
    emojiSize,
    onEmojiSizeChange,
    screenWidth,
    screenHeight,
}: EmojiPackEditorProps) {
    const { t } = useTranslation(["devices", "common"]);
    const [isCustomMode, setIsCustomMode] = useState(false);
    const fileInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

    // Count custom emojis
    const customCount = Object.values(customEmojis).filter(e => e.isCustom).length;

    // Handle preset selection
    const handlePresetSelect = (presetName: string) => {
        onPresetChange(presetName);
        const preset = EMOJI_PRESETS.find(p => p.name === presetName);
        if (preset) {
            onEmojiSizeChange(preset.size);
        }
        setIsCustomMode(false);
    };

    // Handle switching to custom mode
    const handleCustomMode = () => {
        setIsCustomMode(true);
    };

    // Handle individual emoji upload
    const handleEmojiUpload = useCallback((emotionName: string, file: File) => {
        // Validate file type
        if (!file.type.startsWith("image/")) {
            alert("Vui lòng chọn file hình ảnh (PNG, GIF, JPG)");
            return;
        }

        // Create preview URL
        const preview = URL.createObjectURL(file);

        onCustomEmojisChange({
            ...customEmojis,
            [emotionName]: {
                file,
                preview,
                isCustom: true,
            },
        });
    }, [customEmojis, onCustomEmojisChange]);

    // Handle emoji click to upload
    const handleEmojiClick = (emotionName: string) => {
        const input = fileInputRefs.current[emotionName];
        if (input) {
            input.click();
        }
    };

    // Handle file input change
    const handleFileChange = (emotionName: string, e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleEmojiUpload(emotionName, file);
        }
        // Reset input
        e.target.value = "";
    };

    // Remove custom emoji
    const handleRemoveEmoji = (emotionName: string) => {
        const current = customEmojis[emotionName];
        if (current?.preview) {
            URL.revokeObjectURL(current.preview);
        }

        const newEmojis = { ...customEmojis };
        delete newEmojis[emotionName];
        onCustomEmojisChange(newEmojis);
    };

    // Reset all custom emojis
    const handleResetAll = () => {
        // Cleanup all preview URLs
        Object.values(customEmojis).forEach(e => {
            if (e.preview) {
                URL.revokeObjectURL(e.preview);
            }
        });
        onCustomEmojisChange({});
        setIsCustomMode(false);
        onPresetChange("twemoji64");
        onEmojiSizeChange(64);
    };

    // Get preview URL or default for an emotion
    const getEmojiPreview = (emotionName: string): string | null => {
        const custom = customEmojis[emotionName];
        if (custom?.preview) {
            return custom.preview;
        }
        // Return null if no custom, will show default emoji
        return null;
    };

    return (
        <div className="space-y-6">
            {/* Preset Selection */}
            <div className="space-y-4">
                <Text strong className="flex items-center gap-2">
                    <ImageIcon className="h-4 w-4" />
                    {t("select_emoji_pack", "Chọn bộ biểu cảm")}
                </Text>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {/* Preset options */}
                    {EMOJI_PRESETS.map((preset) => (
                        <button
                            key={preset.name}
                            onClick={() => handlePresetSelect(preset.name)}
                            className={cn(
                                "flex items-center justify-between p-4 rounded-xl border text-left transition-all hover:shadow-md",
                                selectedPreset === preset.name && !isCustomMode
                                    ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-500"
                                    : "border-gray-200 dark:border-gray-700 hover:border-blue-300"
                            )}
                        >
                            <div className="flex items-center gap-3">
                                <span className="text-3xl">😊</span>
                                <div>
                                    <Text strong>{preset.displayName}</Text>
                                    <Text type="tertiary" size="small" className="block">
                                        {preset.size}x{preset.size} px
                                    </Text>
                                </div>
                            </div>
                            {selectedPreset === preset.name && !isCustomMode && (
                                <div className="bg-blue-500 text-white rounded-full p-1">
                                    <Check className="h-3 w-3" />
                                </div>
                            )}
                        </button>
                    ))}

                    {/* Custom option */}
                    <button
                        onClick={handleCustomMode}
                        className={cn(
                            "flex items-center justify-between p-4 rounded-xl border text-left transition-all hover:shadow-md",
                            isCustomMode
                                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-500"
                                : "border-dashed border-gray-300 dark:border-gray-600 hover:border-blue-300"
                        )}
                    >
                        <div className="flex items-center gap-3">
                            <div className="text-3xl flex items-center justify-center w-8 h-8 bg-gray-100 dark:bg-gray-800 rounded-lg">
                                <Upload className="h-5 w-5" />
                            </div>
                            <div>
                                <Text strong>Tùy chỉnh</Text>
                                <Text type="tertiary" size="small" className="block">
                                    Upload hình riêng
                                </Text>
                            </div>
                        </div>
                        {isCustomMode && (
                            <div className="bg-blue-500 text-white rounded-full p-1">
                                <Check className="h-3 w-3" />
                            </div>
                        )}
                    </button>
                </div>
            </div>

            {/* Preview Emoji Grid (dạng rút gọn khi không custom) */}
            {!isCustomMode && (
                <div className="border-t pt-4">
                    <Text type="tertiary" size="small" className="block mb-3">
                        Preview bộ biểu cảm:
                    </Text>
                    <div className="flex flex-wrap gap-2">
                        {EMOJI_EMOTIONS.map((emotion) => (
                            <span
                                key={emotion.name}
                                className="text-2xl opacity-80 hover:opacity-100 transition-opacity"
                                title={emotion.displayName}
                            >
                                {emotion.emoji}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Custom Emoji Editor Grid */}
            {isCustomMode && (
                <div className="space-y-4 rounded-xl border bg-gray-50 dark:bg-gray-800/50 p-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <Text strong>Tùy chỉnh từng biểu cảm</Text>
                            <Text type="tertiary" size="small" className="block">
                                Click vào biểu cảm để upload hình thay thế. Hỗ trợ PNG (trong suốt) và GIF (động).
                            </Text>
                        </div>
                        <div className="flex items-center gap-2">
                            {customCount > 0 && (
                                <Tag>{customCount}/21 đã tùy chỉnh</Tag>
                            )}
                            <Button
                                theme="borderless"
                                size="small"
                                onClick={handleResetAll}
                                icon={<RotateCcw className="h-4 w-4" />}
                            >
                                Reset tất cả
                            </Button>
                        </div>
                    </div>

                    {/* Size config */}
                    <div className="flex items-center gap-4 p-3 bg-white dark:bg-gray-900 rounded-lg">
                        <Text size="small">Kích thước:</Text>
                        <Select
                            value={String(emojiSize)}
                            onChange={(v) => onEmojiSizeChange(Number(v))}
                            style={{ width: 120 }}
                        >
                            <Select.Option value="32">32x32 px</Select.Option>
                            <Select.Option value="48">48x48 px</Select.Option>
                            <Select.Option value="64">64x64 px</Select.Option>
                            <Select.Option value="96">96x96 px</Select.Option>
                            <Select.Option value="128">128x128 px</Select.Option>
                        </Select>
                        <Text type="tertiary" size="small">
                            (Phải nhỏ hơn {screenWidth}x{screenHeight})
                        </Text>
                    </div>

                    {/* Neutral (required) notice */}
                    <Banner
                        type="warning"
                        description={<>
                            Emotion nào chưa upload sẽ dùng lại bộ biểu cảm nền đang chọn để giữ đủ mapping cho thiết bị.
                        </>}
                        closeIcon={null}
                    />

                    {/* Emoji Grid */}
                    <div className="grid grid-cols-3 sm:grid-cols-5 md:grid-cols-7 gap-3">
                        {EMOJI_EMOTIONS.map((emotion) => {
                            const customData = customEmojis[emotion.name];
                            const isNeutral = emotion.name === "neutral";
                            const preview = getEmojiPreview(emotion.name);

                            return (
                                <Tooltip key={emotion.name} content={
                                    <div>
                                        <Text strong size="small" className="block">{emotion.displayName}</Text>
                                        <Text type="tertiary" size="small">
                                            {customData?.isCustom ? "Click để thay đổi" : "Click để upload"}
                                        </Text>
                                    </div>
                                }>
                                    <div
                                        onClick={() => handleEmojiClick(emotion.name)}
                                        className={cn(
                                            "relative aspect-square rounded-xl border-2 flex flex-col items-center justify-center cursor-pointer transition-all hover:scale-105 hover:shadow-lg group",
                                            customData?.isCustom
                                                ? "border-green-500 bg-green-500/10"
                                                : isNeutral
                                                    ? "border-amber-500 border-dashed bg-amber-500/5"
                                                    : "border-dashed border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 hover:border-blue-300"
                                        )}
                                    >
                                        {/* Preview or Default Emoji */}
                                        {preview ? (
                                            <img
                                                src={preview}
                                                alt={emotion.displayName}
                                                className="w-10 h-10 object-contain"
                                            />
                                        ) : (
                                            <span className="text-3xl">{emotion.emoji}</span>
                                        )}

                                        {/* Label */}
                                        <span className="text-[10px] text-gray-500 mt-1 truncate max-w-full px-1">
                                            {emotion.name}
                                        </span>

                                        {/* Custom indicator */}
                                        {customData?.isCustom && (
                                            <div className="absolute -top-1 -right-1 bg-green-500 text-white rounded-full p-0.5">
                                                <Check className="h-3 w-3" />
                                            </div>
                                        )}

                                        {/* Required badge for neutral */}
                                        {isNeutral && !customData?.isCustom && (
                                            <div className="absolute -top-1 -left-1 bg-amber-500 text-white text-[8px] px-1 rounded">
                                                BẮT BUỘC
                                            </div>
                                        )}

                                        {/* Hover overlay */}
                                        <div className="absolute inset-0 rounded-xl bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                            <Upload className="h-6 w-6 text-white" />
                                        </div>

                                        {/* Remove button */}
                                        {customData?.isCustom && (
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    handleRemoveEmoji(emotion.name);
                                                }}
                                                className="absolute top-1 right-1 bg-red-500 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                                            >
                                                <X className="h-3 w-3" />
                                            </button>
                                        )}

                                        {/* Hidden file input */}
                                        <input
                                            ref={(el) => { fileInputRefs.current[emotion.name] = el; }}
                                            type="file"
                                            accept="image/png,image/gif,image/jpeg,image/webp"
                                            className="hidden"
                                            onChange={(e) => handleFileChange(emotion.name, e)}
                                        />
                                    </div>
                                </Tooltip>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}

export default EmojiPackEditor;
