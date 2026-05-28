/**
 * Weather Widget Configuration Step - Semi Design implementation
 * Uses free Open-Meteo API - No API key required!
 */

import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Cloud, MapPin, RefreshCw } from "lucide-react";
import { Input, Select, Switch, Button, Typography } from "@douyinfe/semi-ui";
import { IconRefresh } from "@douyinfe/semi-icons";
import type { WeatherConfig, DisplayConfig, WidgetPosition } from "../utils/types";
import { WEATHER_ICONS } from "../utils/types";

const { Text } = Typography;

interface WeatherStepProps {
    config: DisplayConfig;
    onUpdate: (updates: Partial<WeatherConfig>) => void;
}

const POSITION_OPTIONS: { value: WidgetPosition; label: string }[] = [
    { value: "top-left", label: "Trên - Trái" },
    { value: "top-right", label: "Trên - Phải" },
    { value: "bottom-left", label: "Dưới - Trái" },
    { value: "bottom-right", label: "Dưới - Phải" },
];

const UPDATE_INTERVALS = [
    { value: 15, label: "15 phút" },
    { value: 30, label: "30 phút" },
    { value: 60, label: "1 giờ" },
    { value: 180, label: "3 giờ" },
];

// Popular Vietnam cities
const POPULAR_CITIES = [
    "Hanoi",
    "Ho Chi Minh City",
    "Da Nang",
    "Hai Phong",
    "Can Tho",
    "Nha Trang",
    "Hue",
    "Vung Tau",
];

interface WeatherPreview {
    temp: number;
    humidity: number;
    code: number;
    city: string;
    loading: boolean;
    error?: string;
}

export function WeatherStep({ config, onUpdate }: WeatherStepProps) {
    const { t } = useTranslation(["devices", "common"]);
    const { weather } = config;

    // Weather preview state
    const [preview, setPreview] = useState<WeatherPreview>({
        temp: 28,
        humidity: 75,
        code: 2,
        city: weather.location,
        loading: false,
    });

    // Fetch weather preview
    const fetchWeatherPreview = async () => {
        if (!weather.location) return;

        setPreview((prev) => ({ ...prev, loading: true, error: undefined }));

        try {
            // First, geocode the location
            const geoResponse = await fetch(
                `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(weather.location)}&count=1&language=vi`
            );
            const geoData = await geoResponse.json();

            if (!geoData.results || geoData.results.length === 0) {
                setPreview((prev) => ({
                    ...prev,
                    loading: false,
                    error: "Không tìm thấy địa điểm",
                }));
                return;
            }

            const { latitude, longitude, name } = geoData.results[0];

            // Then fetch weather
            const weatherResponse = await fetch(
                `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=temperature_2m,relative_humidity_2m,weather_code&timezone=auto`
            );
            const weatherData = await weatherResponse.json();

            const current = weatherData.current || {};
            setPreview({
                temp: Math.round(current.temperature_2m || 28),
                humidity: current.relative_humidity_2m || 75,
                code: current.weather_code || 2,
                city: name || weather.location,
                loading: false,
            });
        } catch (error) {
            setPreview((prev) => ({
                ...prev,
                loading: false,
                error: "Lỗi kết nối API",
            }));
        }
    };

    // Fetch on location change (debounced)
    useEffect(() => {
        const timeout = setTimeout(() => {
            if (weather.location) {
                fetchWeatherPreview();
            }
        }, 500);

        return () => clearTimeout(timeout);
    }, [weather.location]);

    const weatherIcon = WEATHER_ICONS[preview.code] || "🌤️";

    return (
        <div className="space-y-6">
            {/* Header with preview */}
            <div className="flex items-start justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2 mb-1">
                        <Cloud className="h-5 w-5 text-cyan-500" />
                        <Text strong>
                            {t("display.weather_settings", "Cài đặt thời tiết")}
                        </Text>
                    </div>
                    <Text type="tertiary" size="small">
                        {t("display.weather_free", "Sử dụng Open-Meteo API miễn phí, không cần đăng ký")}
                    </Text>
                </div>

                {/* Live preview */}
                <div
                    className="px-4 py-3 rounded-lg min-w-[120px]"
                    style={{
                        backgroundColor: config.background.color,
                        color: config.isDarkMode ? "#ffffff" : "#000000",
                    }}
                >
                    {preview.loading ? (
                        <RefreshCw className="h-6 w-6 animate-spin mx-auto" />
                    ) : preview.error ? (
                        <div className="text-xs text-red-400 text-center">{preview.error}</div>
                    ) : (
                        <div className="text-center">
                            {weather.showIcon && (
                                <div className="text-3xl mb-1">{weatherIcon}</div>
                            )}
                            {weather.showTemp && (
                                <div className="text-xl font-bold">{preview.temp}°C</div>
                            )}
                            {weather.showHumidity && (
                                <div className="text-xs opacity-70">💧 {preview.humidity}%</div>
                            )}
                            {weather.showCity && (
                                <div className="text-xs opacity-50 mt-1">{preview.city}</div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Location Input */}
            <div className="space-y-3">
                <Text strong size="small" className="flex items-center gap-2">
                    <MapPin className="h-4 w-4" />
                    {t("display.location", "Địa điểm")}
                </Text>
                <div className="flex gap-2">
                    <Input
                        value={weather.location}
                        onChange={(value) => onUpdate({ location: String(value) })}
                        placeholder="Hanoi, Ho Chi Minh City..."
                        className="flex-1"
                    />
                    <Button
                        icon={<IconRefresh spin={preview.loading} />}
                        onClick={fetchWeatherPreview}
                        disabled={preview.loading}
                    />
                </div>

                {/* Quick city buttons */}
                <div className="flex flex-wrap gap-1">
                    {POPULAR_CITIES.map((city) => (
                        <Button
                            key={city}
                            size="small"
                            theme={weather.location === city ? "solid" : "borderless"}
                            onClick={() => onUpdate({ location: city })}
                        >
                            {city}
                        </Button>
                    ))}
                </div>
            </div>

            {/* Settings Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {/* Position */}
                <div className="space-y-2">
                    <Text strong size="small" className="block">
                        {t("display.position", "Vị trí")}
                    </Text>
                    <Select
                        value={weather.position}
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

                {/* Update Interval */}
                <div className="space-y-2">
                    <Text strong size="small" className="block">
                        {t("display.update_interval", "Tần suất cập nhật")}
                    </Text>
                    <Select
                        value={String(weather.updateInterval)}
                        onChange={(v) => onUpdate({ updateInterval: parseInt(String(v)) })}
                        style={{ width: "100%" }}
                    >
                        {UPDATE_INTERVALS.map((opt) => (
                            <Select.Option key={opt.value} value={String(opt.value)}>
                                {opt.label}
                            </Select.Option>
                        ))}
                    </Select>
                </div>
            </div>

            {/* Toggle options */}
            <div className="space-y-4 pt-4 border-t">
                <div className="flex items-center justify-between">
                    <Text strong size="small">
                        {t("display.show_icon", "Hiển thị icon thời tiết")}
                    </Text>
                    <Switch
                        checked={weather.showIcon}
                        onChange={(v) => onUpdate({ showIcon: v })}
                    />
                </div>

                <div className="flex items-center justify-between">
                    <Text strong size="small">
                        {t("display.show_temp", "Hiển thị nhiệt độ")}
                    </Text>
                    <Switch
                        checked={weather.showTemp}
                        onChange={(v) => onUpdate({ showTemp: v })}
                    />
                </div>

                <div className="flex items-center justify-between">
                    <Text strong size="small">
                        {t("display.show_humidity", "Hiển thị độ ẩm")}
                    </Text>
                    <Switch
                        checked={weather.showHumidity}
                        onChange={(v) => onUpdate({ showHumidity: v })}
                    />
                </div>

                <div className="flex items-center justify-between">
                    <Text strong size="small">
                        {t("display.show_city", "Hiển thị tên thành phố")}
                    </Text>
                    <Switch
                        checked={weather.showCity}
                        onChange={(v) => onUpdate({ showCity: v })}
                    />
                </div>
            </div>

            {/* API info */}
            <div className="text-xs text-gray-500 bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3">
                <Text strong size="small" className="block mb-1">💡 Open-Meteo API</Text>
                <Text type="tertiary" size="small">
                    Dữ liệu thời tiết được cung cấp miễn phí bởi{" "}
                    <a
                        href="https://open-meteo.com"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:underline"
                    >
                        open-meteo.com
                    </a>
                    . Không cần API key, không giới hạn requests.
                </Text>
            </div>
        </div>
    );
}

export default WeatherStep;
