/**
 * Clock Widget Configuration Step - Semi Design implementation
 */

import { useTranslation } from "react-i18next";
import { Clock } from "lucide-react";
import { Input, Select, Switch, Typography } from "@douyinfe/semi-ui";
import type { ClockConfig, DisplayConfig, WidgetPosition, WidgetSize } from "../utils/types";
import { cn } from "@/lib/utils";

const { Text } = Typography;

interface ClockStepProps {
    config: DisplayConfig;
    onUpdate: (updates: Partial<ClockConfig>) => void;
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

const SIZE_OPTIONS: { value: WidgetSize; label: string }[] = [
    { value: "small", label: "Nhỏ" },
    { value: "medium", label: "Vừa" },
    { value: "large", label: "Lớn" },
];

export function ClockStep({ config, onUpdate }: ClockStepProps) {
    const { t } = useTranslation(["devices", "common"]);
    const { clock } = config;

    // Preview time
    const now = new Date();
    let hours = now.getHours();
    let suffix = "";
    if (clock.format === "12h") {
        suffix = hours >= 12 ? " PM" : " AM";
        hours = hours % 12 || 12;
    }
    const previewTime = clock.showSeconds
        ? `${hours.toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}:${now.getSeconds().toString().padStart(2, "0")}${suffix}`
        : `${hours.toString().padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}${suffix}`;

    return (
        <div className="space-y-6">
            {/* Header with preview */}
            <div className="flex items-start justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <Clock className="h-5 w-5 text-blue-500" />
                        <Text strong>
                            {t("display.clock_settings", "Cài đặt đồng hồ")}
                        </Text>
                    </div>
                    <Text type="tertiary" size="small">
                        {t("display.clock_settings_desc", "Tùy chỉnh cách hiển thị thời gian")}
                    </Text>
                </div>

                {/* Live preview */}
                <div
                    className="px-4 py-2 rounded-lg text-center"
                    style={{
                        backgroundColor: config.background.color,
                        color: clock.color,
                    }}
                >
                    <div
                        className={cn(
                            "font-mono font-bold",
                            clock.size === "small" && "text-lg",
                            clock.size === "medium" && "text-2xl",
                            clock.size === "large" && "text-3xl"
                        )}
                    >
                        {previewTime}
                    </div>
                    {clock.showDate && (
                        <div className="text-xs opacity-70 mt-1">
                            {now.toLocaleDateString("vi-VN", {
                                weekday: "short",
                                day: "numeric",
                                month: "short",
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Settings Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {/* Format */}
                <div className="space-y-2">
                    <Text strong size="small" className="block">
                        {t("display.time_format", "Định dạng giờ")}
                    </Text>
                    <Select
                        value={clock.format}
                        onChange={(v) => onUpdate({ format: v as "12h" | "24h" })}
                        style={{ width: "100%" }}
                    >
                        <Select.Option value="24h">24 giờ (14:30)</Select.Option>
                        <Select.Option value="12h">12 giờ (2:30 PM)</Select.Option>
                    </Select>
                </div>

                {/* Position */}
                <div className="space-y-2">
                    <Text strong size="small" className="block">
                        {t("display.position", "Vị trí")}
                    </Text>
                    <Select
                        value={clock.position}
                        onChange={(v) => onUpdate({ position: v as WidgetPosition })}
                        style={{ width: "100%" }}
                    >
                        {POSITION_OPTIONS.map((opt) => (
                            <Select.Option key={opt.value} value={opt.value}>
                                {opt.label}
                            </Select.Option>
                        ))}
                    </Select>
                </div>

                {/* Size */}
                <div className="space-y-2">
                    <Text strong size="small" className="block">
                        {t("display.size", "Kích thước")}
                    </Text>
                    <Select
                        value={clock.size}
                        onChange={(v) => onUpdate({ size: v as WidgetSize })}
                        style={{ width: "100%" }}
                    >
                        {SIZE_OPTIONS.map((opt) => (
                            <Select.Option key={opt.value} value={opt.value}>
                                {opt.label}
                            </Select.Option>
                        ))}
                    </Select>
                </div>

                {/* Color */}
                <div className="space-y-2">
                    <Text strong size="small" className="block">
                        {t("display.text_color", "Màu chữ")}
                    </Text>
                    <div className="flex gap-2">
                        <input
                            type="color"
                            value={clock.color}
                            onChange={(e) => onUpdate({ color: e.target.value })}
                            className="w-12 h-10 p-1 cursor-pointer rounded border"
                        />
                        <Input
                            value={clock.color}
                            onChange={(value) => onUpdate({ color: String(value) })}
                            className="flex-1 font-mono"
                            placeholder="#ffffff"
                        />
                    </div>
                </div>
            </div>

            {/* Toggle options */}
            <div className="space-y-4 pt-4 border-t">
                <div className="flex items-center justify-between">
                    <div>
                        <Text strong size="small" className="block">
                            {t("display.show_seconds", "Hiển thị giây")}
                        </Text>
                        <Text type="tertiary" size="small">
                            {t("display.show_seconds_desc", "Hiển thị số giây trong đồng hồ")}
                        </Text>
                    </div>
                    <Switch
                        checked={clock.showSeconds}
                        onChange={(v) => onUpdate({ showSeconds: v })}
                    />
                </div>

                <div className="flex items-center justify-between">
                    <div>
                        <Text strong size="small" className="block">
                            {t("display.show_date", "Hiển thị ngày")}
                        </Text>
                        <Text type="tertiary" size="small">
                            {t("display.show_date_desc", "Hiển thị ngày tháng bên dưới đồng hồ")}
                        </Text>
                    </div>
                    <Switch
                        checked={clock.showDate}
                        onChange={(v) => onUpdate({ showDate: v })}
                    />
                </div>
            </div>
        </div>
    );
}

export default ClockStep;
