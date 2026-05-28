/**
 * Display Preview Canvas Component
 * Renders a live preview of the display configuration
 */

import { useEffect, useRef, useMemo, useState } from "react";
import type { DisplayConfig } from "./utils/types";
import { WEATHER_ICONS } from "./utils/types";

interface DisplayPreviewCanvasProps {
    config: DisplayConfig;
    className?: string;
    scale?: number;
}

export function DisplayPreviewCanvas({
    config,
    className = "",
    scale = 1,
}: DisplayPreviewCanvasProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const imageRef = useRef<HTMLImageElement | null>(null);
    const emojiImageRef = useRef<HTMLImageElement | null>(null);
    const [imageLoaded, setImageLoaded] = useState(false);
    const [emojiImageLoaded, setEmojiImageLoaded] = useState(false);

    // Calculate display dimensions
    const displayWidth = config.screenWidth * scale;
    const displayHeight = config.screenHeight * scale;

    // Current time for clock preview - update every second for live preview
    const [currentTime, setCurrentTime] = useState(() => {
        const now = new Date();
        return {
            hours: now.getHours(),
            minutes: now.getMinutes(),
            seconds: now.getSeconds(),
            date: now.toLocaleDateString("vi-VN", {
                weekday: "short",
                day: "numeric",
                month: "short",
            }),
        };
    });

    // Update time every second for live preview
    useEffect(() => {
        const interval = setInterval(() => {
            const now = new Date();
            setCurrentTime({
                hours: now.getHours(),
                minutes: now.getMinutes(),
                seconds: now.getSeconds(),
                date: now.toLocaleDateString("vi-VN", {
                    weekday: "short",
                    day: "numeric",
                    month: "short",
                }),
            });
        }, 1000);
        return () => clearInterval(interval);
    }, []);

    // Mock weather data for preview
    const mockWeather = useMemo(
        () => ({
            temp: 28,
            humidity: 75,
            code: 2, // Partly cloudy
            city: config.weather.location || "Hanoi",
        }),
        [config.weather.location]
    );

    // Preload background image when it changes
    useEffect(() => {
        if (config.background.mode === "image" && config.background.imageData) {
            const img = new Image();
            img.onload = () => {
                imageRef.current = img;
                setImageLoaded(true);
            };
            img.onerror = () => {
                imageRef.current = null;
                setImageLoaded(false);
            };
            img.src = config.background.imageData;
            setImageLoaded(false); // Reset while loading
        } else {
            imageRef.current = null;
            setImageLoaded(false);
        }
    }, [config.background.mode, config.background.imageData]);

    const currentEmotion = config.emoji.currentEmotion || "happy";
    const currentCustomEmoji = config.emoji.customEmojis?.[currentEmotion];

    useEffect(() => {
        if (currentCustomEmoji?.data) {
            const img = new Image();
            img.onload = () => {
                emojiImageRef.current = img;
                setEmojiImageLoaded(true);
            };
            img.onerror = () => {
                emojiImageRef.current = null;
                setEmojiImageLoaded(false);
            };
            img.src = currentCustomEmoji.data;
            setEmojiImageLoaded(false);
        } else {
            emojiImageRef.current = null;
            setEmojiImageLoaded(false);
        }
    }, [currentCustomEmoji?.data]);

    // Serialize config for deep comparison in useEffect
    const configKey = JSON.stringify({
        enableClock: config.enableClock,
        enableWeather: config.enableWeather,
        enableEmoji: config.enableEmoji,
        enableBackground: config.enableBackground,
        clock: config.clock,
        weather: config.weather,
        emoji: config.emoji,
        background: config.background,
        isDarkMode: config.isDarkMode,
    });

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Clear canvas
        ctx.clearRect(0, 0, displayWidth, displayHeight);

        // Draw background
        drawBackground(ctx, config, displayWidth, displayHeight, imageRef.current);

        // Draw widgets
        if (config.enableClock && config.clock.enabled) {
            drawClock(ctx, config, displayWidth, displayHeight, currentTime);
        }

        if (config.enableWeather && config.weather.enabled) {
            drawWeather(ctx, config, displayWidth, displayHeight, mockWeather);
        }

        if (config.enableEmoji && config.emoji.enabled) {
            drawEmoji(ctx, config, displayWidth, displayHeight, emojiImageRef.current);
        }
    }, [configKey, displayWidth, displayHeight, currentTime, mockWeather, imageLoaded, emojiImageLoaded]);

    return (
        <div
            className={`relative inline-block rounded-lg overflow-hidden shadow-lg ${className}`}
            style={{
                width: displayWidth,
                height: displayHeight,
            }}
        >
            <canvas
                ref={canvasRef}
                width={displayWidth}
                height={displayHeight}
                className="block"
                style={{
                    imageRendering: "pixelated",
                }}
            />
            {/* Device frame overlay */}
            <div className="absolute inset-0 pointer-events-none border-4 border-gray-800 rounded-lg" />
        </div>
    );
}
// ============ Drawing Functions ============

function drawBackground(
    ctx: CanvasRenderingContext2D,
    config: DisplayConfig,
    width: number,
    height: number,
    cachedImage: HTMLImageElement | null
) {
    const { background } = config;

    // Fill background color first (for contain mode or as fallback)
    ctx.fillStyle = background.color;
    ctx.fillRect(0, 0, width, height);

    if (background.mode === "image" && cachedImage) {
        const imgWidth = cachedImage.naturalWidth;
        const imgHeight = cachedImage.naturalHeight;

        let sx = 0, sy = 0, sw = imgWidth, sh = imgHeight;
        let dx = 0, dy = 0, dw = width, dh = height;

        const imageFit = background.imageFit || "cover";

        switch (imageFit) {
            case "cover": {
                // Fill entire canvas, crop image if needed
                const canvasRatio = width / height;
                const imgRatio = imgWidth / imgHeight;

                if (imgRatio > canvasRatio) {
                    // Image is wider - crop sides
                    sh = imgHeight;
                    sw = imgHeight * canvasRatio;
                    sx = (imgWidth - sw) / 2;
                    // Apply offset if set
                    if (background.offsetX) {
                        sx += background.offsetX * (imgWidth - sw);
                    }
                } else {
                    // Image is taller - crop top/bottom
                    sw = imgWidth;
                    sh = imgWidth / canvasRatio;
                    sy = (imgHeight - sh) / 2;
                    // Apply offset if set
                    if (background.offsetY) {
                        sy += background.offsetY * (imgHeight - sh);
                    }
                }
                break;
            }
            case "contain": {
                // Fit entire image inside canvas with letterboxing
                const canvasRatio = width / height;
                const imgRatio = imgWidth / imgHeight;

                if (imgRatio > canvasRatio) {
                    // Image is wider - letterbox top/bottom
                    dw = width;
                    dh = width / imgRatio;
                    dx = 0;
                    dy = (height - dh) / 2;
                } else {
                    // Image is taller - letterbox sides
                    dh = height;
                    dw = height * imgRatio;
                    dx = (width - dw) / 2;
                    dy = 0;
                }
                break;
            }
            case "stretch":
            default: {
                // Stretch to fill (default behavior)
                // dx, dy, dw, dh already set to fill canvas
                break;
            }
        }

        ctx.drawImage(cachedImage, sx, sy, sw, sh, dx, dy, dw, dh);
    }

    // Add subtle gradient overlay for depth
    if (config.isDarkMode) {
        const gradient = ctx.createLinearGradient(0, 0, 0, height);
        gradient.addColorStop(0, "rgba(255,255,255,0.02)");
        gradient.addColorStop(1, "rgba(0,0,0,0.1)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, width, height);
    }
}

function drawClock(
    ctx: CanvasRenderingContext2D,
    config: DisplayConfig,
    width: number,
    height: number,
    time: { hours: number; minutes: number; seconds: number; date: string }
) {
    const { clock } = config;

    // Calculate font size based on size setting
    const fontSizes = {
        small: Math.floor(height * 0.08),
        medium: Math.floor(height * 0.12),
        large: Math.floor(height * 0.18),
    };
    const fontSize = fontSizes[clock.size];
    const dateFontSize = Math.floor(fontSize * 0.4);

    // Format time
    let hours = time.hours;
    let suffix = "";
    if (clock.format === "12h") {
        suffix = hours >= 12 ? " PM" : " AM";
        hours = hours % 12 || 12;
    }

    const timeStr = clock.showSeconds
        ? `${hours.toString().padStart(2, "0")}:${time.minutes.toString().padStart(2, "0")}:${time.seconds.toString().padStart(2, "0")}${suffix}`
        : `${hours.toString().padStart(2, "0")}:${time.minutes.toString().padStart(2, "0")}${suffix}`;

    // Calculate position
    const pos = getWidgetPosition(clock.position, width, height, 0.8, 0.2);

    // Draw time
    ctx.font = `bold ${fontSize}px "SF Mono", "Fira Code", monospace`;
    ctx.fillStyle = clock.color;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(timeStr, pos.x, pos.y);

    // Draw date below time
    if (clock.showDate) {
        ctx.font = `${dateFontSize}px system-ui, sans-serif`;
        ctx.fillStyle = clock.color;
        ctx.globalAlpha = 0.7;
        ctx.fillText(time.date, pos.x, pos.y + fontSize * 0.7);
        ctx.globalAlpha = 1;
    }
}

function drawWeather(
    ctx: CanvasRenderingContext2D,
    config: DisplayConfig,
    width: number,
    height: number,
    weather: { temp: number; humidity: number; code: number; city: string }
) {
    const { weather: weatherConfig } = config;
    const fontSize = Math.floor(height * 0.06);
    const iconSize = Math.floor(height * 0.12);

    // Get position
    const pos = getWidgetPosition(weatherConfig.position, width, height, 0.25, 0.15);

    let xOffset = pos.x;

    // Draw icon
    if (weatherConfig.showIcon) {
        const icon = WEATHER_ICONS[weather.code] || "🌤️";
        ctx.font = `${iconSize}px system-ui, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(icon, xOffset, pos.y);
        xOffset += iconSize * 0.8;
    }

    // Draw temperature
    if (weatherConfig.showTemp) {
        ctx.font = `bold ${fontSize}px system-ui, sans-serif`;
        ctx.fillStyle = config.isDarkMode ? "#ffffff" : "#000000";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        const tempStr = `${weather.temp}°C`;
        ctx.fillText(tempStr, xOffset, pos.y - (weatherConfig.showHumidity ? fontSize * 0.5 : 0));

        // Draw humidity below
        if (weatherConfig.showHumidity) {
            ctx.font = `${fontSize * 0.7}px system-ui, sans-serif`;
            ctx.globalAlpha = 0.7;
            ctx.fillText(`💧 ${weather.humidity}%`, xOffset, pos.y + fontSize * 0.5);
            ctx.globalAlpha = 1;
        }
    }

    // Draw city name
    if (weatherConfig.showCity) {
        ctx.font = `${fontSize * 0.6}px system-ui, sans-serif`;
        ctx.fillStyle = config.isDarkMode ? "#ffffff" : "#000000";
        ctx.globalAlpha = 0.5;
        ctx.textAlign = "center";
        ctx.fillText(weather.city, pos.x + iconSize / 2, pos.y + fontSize * 1.2);
        ctx.globalAlpha = 1;
    }
}

function drawEmoji(
    ctx: CanvasRenderingContext2D,
    config: DisplayConfig,
    width: number,
    height: number,
    customImage: HTMLImageElement | null
) {
    const { emoji } = config;

    // Get position
    const pos = getWidgetPosition(emoji.position, width, height, 0.3, 0.3);

    const fontSize = Math.min(emoji.size, height * 0.4);
    const imageSize = fontSize;

    if (customImage) {
        ctx.save();
        ctx.shadowColor = "rgba(255, 255, 255, 0.3)";
        ctx.shadowBlur = 10;
        ctx.drawImage(
            customImage,
            pos.x - imageSize / 2,
            pos.y - imageSize / 2,
            imageSize,
            imageSize
        );
        ctx.restore();
        return;
    }

    const emojiChar = getFallbackEmoji(emoji.currentEmotion);

    ctx.font = `${fontSize}px system-ui, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(emojiChar, pos.x, pos.y);

    // Add subtle glow effect
    ctx.shadowColor = "rgba(255, 255, 255, 0.3)";
    ctx.shadowBlur = 10;
    ctx.fillText(emojiChar, pos.x, pos.y);
    ctx.shadowBlur = 0;
}

function getFallbackEmoji(emotionName: string): string {
    const fallbackMap: Record<string, string> = {
        neutral: "😶",
        happy: "🙂",
        laughing: "😆",
        funny: "😂",
        sad: "😔",
        angry: "😠",
        crying: "😭",
        loving: "😍",
        embarrassed: "😳",
        surprised: "😯",
        shocked: "😱",
        thinking: "🤔",
        winking: "😉",
        cool: "😎",
        relaxed: "😌",
        delicious: "🤤",
        kissy: "😘",
        confident: "😏",
        sleepy: "😴",
        silly: "😜",
        confused: "🙄",
    };
    return fallbackMap[emotionName] || "🙂";
}

// ============ Utility Functions ============

function getWidgetPosition(
    position: string,
    width: number,
    height: number,
    widthRatio: number = 0.5,
    heightRatio: number = 0.5
): { x: number; y: number } {
    const padding = Math.min(width, height) * 0.05;
    const widgetWidth = width * widthRatio;
    const widgetHeight = height * heightRatio;

    switch (position) {
        case "top-left":
            return { x: padding + widgetWidth / 2, y: padding + widgetHeight / 2 };
        case "top-center":
            return { x: width / 2, y: padding + widgetHeight / 2 };
        case "top-right":
            return {
                x: width - padding - widgetWidth / 2,
                y: padding + widgetHeight / 2,
            };
        case "center":
            return { x: width / 2, y: height / 2 };
        case "bottom-left":
            return {
                x: padding + widgetWidth / 2,
                y: height - padding - widgetHeight / 2,
            };
        case "bottom-center":
            return { x: width / 2, y: height - padding - widgetHeight / 2 };
        case "bottom-right":
            return {
                x: width - padding - widgetWidth / 2,
                y: height - padding - widgetHeight / 2,
            };
        default:
            return { x: width / 2, y: height / 2 };
    }
}

export default DisplayPreviewCanvas;
