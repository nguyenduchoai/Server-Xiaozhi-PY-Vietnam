/**
 * Types for ESP32 Display Customizer
 * Simplified version for xiaozhi/Xiaozhi devices
 */

import type { ChipModel, ColorFormat } from "../../asset-generator/types";

// Re-export types from asset-generator
export type { ChipModel, ColorFormat };

// ============ Widget Position Types ============
export type WidgetPosition =
    | "top-left"
    | "top-center"
    | "top-right"
    | "center"
    | "bottom-left"
    | "bottom-center"
    | "bottom-right";

export type WidgetSize = "small" | "medium" | "large";

// ============ Background Configuration ============
export interface BackgroundConfig {
    mode: "color" | "image";
    color: string;
    imageData?: string; // Base64 encoded image
    imageFit: "cover" | "contain" | "stretch";
    offsetX?: number; // Image position offset X (-1 to 1), used for cover mode
    offsetY?: number; // Image position offset Y (-1 to 1), used for cover mode
}

// ============ Slideshow Configuration ============
export interface SlideshowImage {
    id: string;
    data: string; // Base64
    name?: string;
}

export interface SlideshowConfig {
    images: SlideshowImage[];
    interval: number; // seconds between slides
    transition: "none" | "fade";
    shuffle: boolean;
}

// ============ Clock Widget Configuration ============
export interface ClockConfig {
    enabled: boolean;
    format: "12h" | "24h";
    showSeconds: boolean;
    showDate: boolean;
    position: WidgetPosition;
    size: WidgetSize;
    color: string;
}

// ============ Weather Widget Configuration ============
export interface WeatherConfig {
    enabled: boolean;
    showIcon: boolean;
    showTemp: boolean;
    showHumidity: boolean;
    showCity: boolean;
    position: WidgetPosition;
    updateInterval: number; // minutes
    location: string; // City name for weather lookup
    lunarFormat?: "short" | "full";
}

// ============ Emoji Widget Configuration ============
export interface EmojiConfig {
    enabled: boolean;
    preset: string; // e.g., "twemoji64"
    size: number;
    position: WidgetPosition;
    currentEmotion: string;
    customEmojis: Record<
        string,
        {
            data: string;
            name?: string;
            fileType?: string;
        }
    >;
}

// ============ MQTT Configuration ============
export interface MqttConfig {
    enabled: boolean;
    broker: string;
    port: number;
    username: string;
    password: string;
    topicPrefix: string;
}

// ============ Main Display Configuration ============
export interface DisplayConfig {
    // Device Info
    name: string;
    boardPreset: string;
    chip: ChipModel;
    screenWidth: number;
    screenHeight: number;
    colorFormat: ColorFormat;

    // Feature Toggles
    enableBackground: boolean;
    enableSlideshow: boolean;
    enableClock: boolean;
    enableWeather: boolean;
    enableEmoji: boolean;
    enableLunarCalendar: boolean;
    enableMqtt: boolean;

    // Widget Configurations
    background: BackgroundConfig;
    slideshow: SlideshowConfig;
    clock: ClockConfig;
    weather: WeatherConfig;
    emoji: EmojiConfig;
    mqtt: MqttConfig;

    // Theme
    isDarkMode: boolean;
}

// ============ Default Configuration ============
export const DEFAULT_DISPLAY_CONFIG: DisplayConfig = {
    name: "My Display Theme",
    boardPreset: "ESP-BOX-3",
    chip: "esp32s3",
    screenWidth: 320,
    screenHeight: 240,
    colorFormat: "RGB565",

    enableBackground: true,
    enableSlideshow: false,
    enableClock: true,
    enableWeather: false,
    enableEmoji: true,
    enableLunarCalendar: false,
    enableMqtt: true,

    background: {
        mode: "color",
        color: "#1a1a2e",
        imageFit: "cover",
    },

    slideshow: {
        images: [],
        interval: 10,
        transition: "fade",
        shuffle: false,
    },

    clock: {
        enabled: true,
        format: "24h",
        showSeconds: false,
        showDate: true,
        position: "top-center",
        size: "large",
        color: "#ffffff",
    },

    weather: {
        enabled: false,
        showIcon: true,
        showTemp: true,
        showHumidity: false,
        showCity: true,
        position: "top-right",
        updateInterval: 30,
        location: "Hanoi",
    },

    emoji: {
        enabled: true,
        preset: "twemoji64",
        size: 64,
        position: "center",
        currentEmotion: "happy",
        customEmojis: {},
    },

    mqtt: {
        enabled: true,
        broker: "",          // Set via device config or system settings
        port: 1883,
        username: "",        // Set via device config
        password: "",        // Set via device config
        topicPrefix: "xiaozhi/device",
    },

    isDarkMode: true,
};

// ============ Wizard Step Types ============
export type WizardStep = "features" | "configure" | "preview";

export interface WizardState {
    currentStep: WizardStep;
    config: DisplayConfig;
    isGenerating: boolean;
    previewImage?: string;
}

// ============ Asset Binary Section Types ============
export const SECTION_TYPES = {
    BACKGROUND: 0x01,
    CLOCK: 0x02,
    WEATHER: 0x03,
    SLIDESHOW: 0x04,
    EMOJI: 0x05,
    MQTT: 0x06,
} as const;

export interface SectionData {
    type: number;
    data: Uint8Array;
}

// ============ Weather Data Types (for widget display) ============
export interface WeatherData {
    temperature: number;
    humidity: number;
    weatherCode: number;
    description: string;
    icon: string;
    city: string;
    updatedAt: string;
}

// Weather code to icon mapping
export const WEATHER_ICONS: Record<number, string> = {
    0: "☀️", // Clear sky
    1: "🌤️", // Mainly clear
    2: "⛅", // Partly cloudy
    3: "☁️", // Overcast
    45: "🌫️", // Fog
    48: "🌫️", // Depositing rime fog
    51: "🌦️", // Light drizzle
    53: "🌦️", // Moderate drizzle
    55: "🌧️", // Dense drizzle
    61: "🌧️", // Slight rain
    63: "🌧️", // Moderate rain
    65: "🌧️", // Heavy rain
    71: "❄️", // Slight snow
    73: "❄️", // Moderate snow
    75: "❄️", // Heavy snow
    80: "🌦️", // Slight rain showers
    81: "🌧️", // Moderate rain showers
    82: "⛈️", // Violent rain showers
    95: "⛈️", // Thunderstorm
    96: "⛈️", // Thunderstorm with hail
    99: "⛈️", // Thunderstorm with heavy hail
};
