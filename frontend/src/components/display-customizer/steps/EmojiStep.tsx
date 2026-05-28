/**
 * Emoji emotion mapping configuration for Display Customizer.
 */

import { useCallback, useRef } from "react";
import { Smile, Upload, X } from "lucide-react";
import { Button, Select, Typography, Banner } from "@douyinfe/semi-ui";
import type { DisplayConfig, EmojiConfig, WidgetPosition } from "../utils/types";
import { EMOJI_EMOTIONS, EMOJI_PRESETS } from "@/components/asset-generator/types";
import { cn } from "@/lib/utils";

const { Text } = Typography;

interface EmojiStepProps {
    config: DisplayConfig;
    onUpdate: (updates: Partial<EmojiConfig>) => void;
}

const POSITION_OPTIONS: { value: WidgetPosition; label: string }[] = [
    { value: "top-left", label: "Trên - Trái" },
    { value: "top-center", label: "Trên - Giữa" },
    { value: "top-right", label: "Trên - Phải" },
    { value: "center", label: "Giữa" },
    { value: "bottom-left", label: "Dưới - Trái" },
    { value: "bottom-center", label: "Dưới - Giữa" },
    { value: "bottom-right", label: "Dưới - Phải" },
];

const SIZE_OPTIONS = [32, 48, 64, 96, 128];

function readFileAsDataUrl(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = () => reject(new Error("Failed to read emoji file"));
        reader.readAsDataURL(file);
    });
}

export function EmojiStep({ config, onUpdate }: EmojiStepProps) {
    const { emoji } = config;
    const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});
    const customCount = Object.keys(emoji.customEmojis || {}).length;

    const updateCustomEmotion = useCallback(
        async (emotionName: string, file: File) => {
            if (!file.type.startsWith("image/")) {
                alert("Vui lòng chọn file hình ảnh");
                return;
            }

            const data = await readFileAsDataUrl(file);
            onUpdate({
                currentEmotion: emotionName,
                customEmojis: {
                    ...(emoji.customEmojis || {}),
                    [emotionName]: {
                        data,
                        name: file.name,
                        fileType: file.type,
                    },
                },
            });
        },
        [emoji.customEmojis, onUpdate],
    );

    const removeCustomEmotion = useCallback(
        (emotionName: string) => {
            const next = { ...(emoji.customEmojis || {}) };
            delete next[emotionName];
            onUpdate({ customEmojis: next });
        },
        [emoji.customEmojis, onUpdate],
    );

    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <div className="mb-1 flex items-center gap-2">
                        <Smile className="h-5 w-5 text-yellow-500" />
                        <Text strong>Cấu hình biểu cảm AI</Text>
                    </div>
                    <Text type="tertiary" size="small">
                        Mapping đủ 21 emotion. Emotion nào không upload sẽ dùng bộ preset nền.
                    </Text>
                </div>

                <div className="rounded-lg border bg-gray-50 px-4 py-2 text-center">
                    <Text strong>{customCount}/21</Text>
                    <Text type="tertiary" size="small" className="block">
                        đã tùy chỉnh
                    </Text>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="space-y-2">
                    <Text strong size="small" className="block">
                        Bộ preset nền
                    </Text>
                    <Select
                        value={emoji.preset}
                        onChange={(v) => {
                            const preset = EMOJI_PRESETS.find((p) => p.name === v);
                            onUpdate({
                                preset: String(v),
                                ...(preset ? { size: preset.size } : {}),
                            });
                        }}
                        style={{ width: "100%" }}
                    >
                        {EMOJI_PRESETS.map((preset) => (
                            <Select.Option key={preset.name} value={preset.name}>
                                {preset.displayName}
                            </Select.Option>
                        ))}
                    </Select>
                </div>

                <div className="space-y-2">
                    <Text strong size="small" className="block">
                        Emotion xem trước
                    </Text>
                    <Select
                        value={emoji.currentEmotion}
                        onChange={(v) => onUpdate({ currentEmotion: String(v) })}
                        style={{ width: "100%" }}
                    >
                        {EMOJI_EMOTIONS.map((emotion) => (
                            <Select.Option key={emotion.name} value={emotion.name}>
                                {emotion.displayName}
                            </Select.Option>
                        ))}
                    </Select>
                </div>

                <div className="space-y-2">
                    <Text strong size="small" className="block">
                        Vị trí
                    </Text>
                    <Select
                        value={emoji.position}
                        onChange={(v) => onUpdate({ position: v as WidgetPosition })}
                        style={{ width: "100%" }}
                    >
                        {POSITION_OPTIONS.map((option) => (
                            <Select.Option key={option.value} value={option.value}>
                                {option.label}
                            </Select.Option>
                        ))}
                    </Select>
                </div>

                <div className="space-y-2">
                    <Text strong size="small" className="block">
                        Kích thước
                    </Text>
                    <Select
                        value={String(emoji.size)}
                        onChange={(v) => onUpdate({ size: Number(v) })}
                        style={{ width: "100%" }}
                    >
                        {SIZE_OPTIONS.map((size) => (
                            <Select.Option key={size} value={String(size)}>
                                {size}x{size}px
                            </Select.Option>
                        ))}
                    </Select>
                </div>
            </div>

            <Banner
                type="info"
                description="Click từng emotion để upload ảnh riêng. Nếu để trống, thiết bị sẽ dùng ảnh từ preset nền nên không mất mapping."
                closeIcon={null}
            />

            <div className="grid grid-cols-3 gap-3 sm:grid-cols-5 md:grid-cols-7">
                {EMOJI_EMOTIONS.map((emotion) => {
                    const custom = emoji.customEmojis?.[emotion.name];
                    const isSelected = emoji.currentEmotion === emotion.name;

                    return (
                        <div
                            key={emotion.name}
                            role="button"
                            tabIndex={0}
                            onClick={() => {
                                onUpdate({ currentEmotion: emotion.name });
                                inputRefs.current[emotion.name]?.click();
                            }}
                            onKeyDown={(event) => {
                                if (event.key === "Enter" || event.key === " ") {
                                    event.preventDefault();
                                    onUpdate({ currentEmotion: emotion.name });
                                    inputRefs.current[emotion.name]?.click();
                                }
                            }}
                            className={cn(
                                "group relative aspect-square rounded-xl border-2 bg-white p-2 text-center transition-all hover:scale-[1.03] hover:shadow-md",
                                custom ? "border-green-500 bg-green-50" : "border-dashed border-gray-300",
                                isSelected && "ring-2 ring-blue-500",
                            )}
                        >
                            <div className="flex h-full flex-col items-center justify-center gap-1">
                                {custom ? (
                                    <img
                                        src={custom.data}
                                        alt={emotion.displayName}
                                        className="h-10 w-10 object-contain"
                                    />
                                ) : (
                                    <span className="text-3xl">{emotion.emoji}</span>
                                )}
                                <span className="max-w-full truncate text-[10px] text-gray-500">
                                    {emotion.name}
                                </span>
                            </div>

                            {custom ? (
                                <span className="absolute right-1 top-1 rounded-full bg-green-500 px-1 text-[9px] text-white">
                                    custom
                                </span>
                            ) : null}

                            <span className="absolute inset-0 hidden items-center justify-center rounded-xl bg-black/45 text-white group-hover:flex">
                                <Upload className="h-5 w-5" />
                            </span>

                            {custom ? (
                                <Button
                                    size="small"
                                    type="danger"
                                    theme="solid"
                                    icon={<X className="h-3 w-3" />}
                                    className="absolute -right-2 -top-2 opacity-0 group-hover:opacity-100"
                                    onClick={(event) => {
                                        event.stopPropagation();
                                        removeCustomEmotion(emotion.name);
                                    }}
                                />
                            ) : null}

                            <input
                                ref={(element) => {
                                    inputRefs.current[emotion.name] = element;
                                }}
                                type="file"
                                accept="image/png,image/gif,image/jpeg,image/webp"
                                className="hidden"
                                onClick={(event) => {
                                    event.stopPropagation();
                                }}
                                onChange={(event) => {
                                    const file = event.target.files?.[0];
                                    if (file) {
                                        updateCustomEmotion(emotion.name, file);
                                    }
                                    event.target.value = "";
                                }}
                            />
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default EmojiStep;
