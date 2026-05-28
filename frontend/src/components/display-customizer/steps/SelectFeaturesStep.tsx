/**
 * Step 1: Select Features
 * Allows user to choose which display features to enable
 */

import { useTranslation } from "react-i18next";
import { Monitor, Image, Clock, Cloud, Smile, Images } from "lucide-react";
import type { DisplayConfig } from "../utils/types";
import { cn } from "@/lib/utils";

interface SelectFeaturesStepProps {
    config: DisplayConfig;
    onToggle: (
        feature:
            | "enableBackground"
            | "enableSlideshow"
            | "enableClock"
            | "enableWeather"
            | "enableEmoji"
            | "enableLunarCalendar"
            | "enableMqtt"
    ) => void;
}

interface FeatureOption {
    id: keyof Pick<
        DisplayConfig,
        | "enableBackground"
        | "enableSlideshow"
        | "enableClock"
        | "enableWeather"
        | "enableEmoji"
        | "enableLunarCalendar"
        | "enableMqtt"
    >;
    icon: React.ReactNode;
    title: string;
    description: string;
    color: string;
}

export function SelectFeaturesStep({
    config,
    onToggle,
}: SelectFeaturesStepProps) {
    const { t } = useTranslation(["devices", "common"]);

    const features: FeatureOption[] = [
        {
            id: "enableBackground",
            icon: <Image className="h-6 w-6" />,
            title: t("display.background", "Hình nền"),
            description: t(
                "display.background_desc",
                "Thêm hình nền tùy chỉnh hoặc màu sắc"
            ),
            color: "bg-purple-500",
        },
        {
            id: "enableSlideshow",
            icon: <Images className="h-6 w-6" />,
            title: t("display.slideshow", "Slideshow"),
            description: t(
                "display.slideshow_desc",
                "Trình chiếu nhiều hình ảnh tự động"
            ),
            color: "bg-pink-500",
        },
        {
            id: "enableClock",
            icon: <Clock className="h-6 w-6" />,
            title: t("display.clock", "Đồng hồ"),
            description: t(
                "display.clock_desc",
                "Hiển thị thời gian và ngày tháng"
            ),
            color: "bg-blue-500",
        },
        {
            id: "enableWeather",
            icon: <Cloud className="h-6 w-6" />,
            title: t("display.weather", "Thời tiết"),
            description: t(
                "display.weather_desc",
                "Hiển thị thời tiết hiện tại (miễn phí)"
            ),
            color: "bg-cyan-500",
        },
        {
            id: "enableEmoji",
            icon: <Smile className="h-6 w-6" />,
            title: t("display.emoji", "Biểu cảm AI"),
            description: t(
                "display.emoji_desc",
                "Mapping 21 emotion, hỗ trợ upload ảnh riêng"
            ),
            color: "bg-yellow-500",
        },
        {
            id: "enableMqtt",
            icon: <Cloud className="h-6 w-6" />,
            title: t("display.mqtt", "MQTT Integration"),
            description: t(
                "display.mqtt_desc",
                "Kết nối IoT Broker (Realtime)"
            ),
            color: "bg-green-500",
        },
    ];

    const enabledCount = features.filter((f) => config[f.id]).length;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mb-3">
                    <Monitor className="h-6 w-6 text-primary" />
                </div>
                <h3 className="text-lg font-semibold">
                    {t("display.select_features", "Chọn tính năng hiển thị")}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">
                    {t(
                        "display.select_features_desc",
                        "Chọn các thành phần bạn muốn hiển thị trên màn hình"
                    )}
                </p>
            </div>

            {/* Feature Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {features.map((feature) => {
                    const isEnabled = config[feature.id];

                    return (
                        <button
                            key={feature.id}
                            onClick={() => onToggle(feature.id)}
                            className={cn(
                                "relative flex flex-col items-start p-4 rounded-xl border-2 transition-all duration-200 text-left",
                                "hover:shadow-md hover:scale-[1.02]",
                                isEnabled
                                    ? "border-primary bg-primary/5 shadow-sm"
                                    : "border-border hover:border-primary/50"
                            )}
                        >
                            {/* Icon */}
                            <div
                                className={cn(
                                    "flex items-center justify-center w-10 h-10 rounded-lg text-white mb-3",
                                    feature.color
                                )}
                            >
                                {feature.icon}
                            </div>

                            {/* Content */}
                            <h4 className="font-medium text-sm">{feature.title}</h4>
                            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                {feature.description}
                            </p>

                            {/* Checkbox indicator */}
                            <div
                                className={cn(
                                    "absolute top-3 right-3 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors",
                                    isEnabled
                                        ? "border-primary bg-primary"
                                        : "border-muted-foreground/30"
                                )}
                            >
                                {isEnabled && (
                                    <svg
                                        className="w-3 h-3 text-white"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                        strokeWidth={3}
                                    >
                                        <path
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            d="M5 13l4 4L19 7"
                                        />
                                    </svg>
                                )}
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Summary */}
            <div className="text-center text-sm text-muted-foreground">
                {enabledCount === 0 ? (
                    <span className="text-orange-500">
                        {t("display.no_features", "Vui lòng chọn ít nhất 1 tính năng")}
                    </span>
                ) : (
                    <span>
                        {t("display.features_selected", "Đã chọn {{count}} tính năng", {
                            count: enabledCount,
                        })}
                    </span>
                )}
            </div>
        </div>
    );
}

export default SelectFeaturesStep;
