/**
 * Custom hook for managing Display Configuration state
 */

import { useState, useCallback, useMemo } from "react";
import type {
    DisplayConfig,
    BackgroundConfig,
    ClockConfig,
    WeatherConfig,
    EmojiConfig,
    SlideshowConfig,
    SlideshowImage,
} from "../utils/types";
import { DEFAULT_DISPLAY_CONFIG } from "../utils/types";
import { BOARD_PRESETS } from "../../asset-generator/types";

interface UseDisplayConfigOptions {
    screenWidth?: number;
    screenHeight?: number;
    boardPreset?: string;
}

interface UseDisplayConfigReturn {
    config: DisplayConfig;
    updateConfig: <K extends keyof DisplayConfig>(
        key: K,
        value: DisplayConfig[K]
    ) => void;
    updateBackground: (updates: Partial<BackgroundConfig>) => void;
    updateClock: (updates: Partial<ClockConfig>) => void;
    updateWeather: (updates: Partial<WeatherConfig>) => void;
    updateEmoji: (updates: Partial<EmojiConfig>) => void;
    updateSlideshow: (updates: Partial<SlideshowConfig>) => void;
    addSlideshowImage: (image: SlideshowImage) => void;
    removeSlideshowImage: (id: string) => void;
    setPreset: (presetName: string) => void;
    updateMqtt: (updates: Partial<DisplayConfig["mqtt"]>) => void;
    toggleFeature: (
        feature:
            | "enableBackground"
            | "enableSlideshow"
            | "enableClock"
            | "enableWeather"
            | "enableEmoji"
            | "enableLunarCalendar"
            | "enableMqtt"
    ) => void;
    resetConfig: () => void;
    isValid: boolean;
}


export function useDisplayConfig(
    options: UseDisplayConfigOptions = {}
): UseDisplayConfigReturn {
    // Initialize config with options
    const initialConfig = useMemo(() => {
        const config = { ...DEFAULT_DISPLAY_CONFIG };

        if (options.screenWidth) config.screenWidth = options.screenWidth;
        if (options.screenHeight) config.screenHeight = options.screenHeight;

        if (options.boardPreset) {
            const preset = BOARD_PRESETS.find((p) => p.name === options.boardPreset);
            if (preset) {
                config.boardPreset = preset.name;
                config.chip = preset.chip;
                config.screenWidth = preset.width;
                config.screenHeight = preset.height;
                config.colorFormat = preset.colorFormat;
            }
        }

        return config;
    }, [options.screenWidth, options.screenHeight, options.boardPreset]);

    const [config, setConfig] = useState<DisplayConfig>(initialConfig);

    // Generic update function
    const updateConfig = useCallback(
        <K extends keyof DisplayConfig>(key: K, value: DisplayConfig[K]) => {
            setConfig((prev) => ({ ...prev, [key]: value }));
        },
        []
    );

    // Background updates
    const updateBackground = useCallback((updates: Partial<BackgroundConfig>) => {
        setConfig((prev) => ({
            ...prev,
            background: { ...prev.background, ...updates },
        }));
    }, []);

    // Clock updates
    const updateClock = useCallback((updates: Partial<ClockConfig>) => {
        setConfig((prev) => ({
            ...prev,
            clock: { ...prev.clock, ...updates },
        }));
    }, []);

    // Weather updates
    const updateWeather = useCallback((updates: Partial<WeatherConfig>) => {
        setConfig((prev) => ({
            ...prev,
            weather: { ...prev.weather, ...updates },
        }));
    }, []);

    // Emoji updates
    const updateEmoji = useCallback((updates: Partial<EmojiConfig>) => {
        setConfig((prev) => ({
            ...prev,
            emoji: { ...prev.emoji, ...updates },
        }));
    }, []);

    // Slideshow updates
    const updateSlideshow = useCallback((updates: Partial<SlideshowConfig>) => {
        setConfig((prev) => ({
            ...prev,
            slideshow: { ...prev.slideshow, ...updates },
        }));
    }, []);

    // Add slideshow image
    const addSlideshowImage = useCallback((image: SlideshowImage) => {
        setConfig((prev) => ({
            ...prev,
            slideshow: {
                ...prev.slideshow,
                images: [...prev.slideshow.images, image],
            },
        }));
    }, []);

    // Remove slideshow image
    const removeSlideshowImage = useCallback((id: string) => {
        setConfig((prev) => ({
            ...prev,
            slideshow: {
                ...prev.slideshow,
                images: prev.slideshow.images.filter((img) => img.id !== id),
            },
        }));
    }, []);

    // Set board preset
    const setPreset = useCallback((presetName: string) => {
        const preset = BOARD_PRESETS.find((p) => p.name === presetName);
        if (preset) {
            setConfig((prev) => ({
                ...prev,
                boardPreset: preset.name,
                chip: preset.chip,
                screenWidth: preset.width,
                screenHeight: preset.height,
                colorFormat: preset.colorFormat,
            }));
        }
    }, []);

    // MQTT updates
    const updateMqtt = useCallback((updates: Partial<DisplayConfig["mqtt"]>) => {
        setConfig((prev) => ({
            ...prev,
            mqtt: { ...prev.mqtt, ...updates },
        }));
    }, []);

    // Toggle feature
    const toggleFeature = useCallback(
        (
            feature:
                | "enableBackground"
                | "enableSlideshow"
                | "enableClock"
                | "enableWeather"
                | "enableEmoji"
                | "enableLunarCalendar"
                | "enableMqtt"
        ) => {
            setConfig((prev) => ({
                ...prev,
                [feature]: !prev[feature],
            }));
        },
        []
    );

    // Reset to default
    const resetConfig = useCallback(() => {
        setConfig(initialConfig);
    }, [initialConfig]);

    // Validation
    const isValid = useMemo(() => {
        // Must have at least one feature enabled
        const hasFeature =
            config.enableBackground ||
            config.enableSlideshow ||
            config.enableClock ||
            config.enableWeather ||
            config.enableEmoji;

        // Name must not be empty
        const hasName = config.name.trim().length > 0;

        return hasFeature && hasName;
    }, [config]);

    return {
        config,
        updateConfig,
        updateBackground,
        updateClock,
        updateWeather,
        updateEmoji,
        updateSlideshow,
        addSlideshowImage,
        removeSlideshowImage,
        setPreset,
        updateMqtt,
        toggleFeature,
        resetConfig,
        isValid,
    };
}
