/**
 * Asset Packer for ESP32 Display
 * Packs display configuration into binary format for flashing
 *
 * Binary Format:
 * ┌─────────────────────────────────────────────────────────┐
 * │ Header (32 bytes)                                       │
 * │   Magic: "DCFG" (4 bytes)                               │
 * │   Version: uint16 (2 bytes)                             │
 * │   Flags: uint16 (2 bytes)                               │
 * │   Screen Width: uint16 (2 bytes)                        │
 * │   Screen Height: uint16 (2 bytes)                       │
 * │   Color Format: uint8 (1 byte) - 0=RGB565, 1=MONO       │
 * │   Section Count: uint8 (1 byte)                         │
 * │   Reserved: (18 bytes)                                  │
 * ├─────────────────────────────────────────────────────────┤
 * │ Section 1                                               │
 * │   Type: uint8 (1 byte)                                  │
 * │   Size: uint32 (4 bytes) - size of data                 │
 * │   Data: (size bytes)                                    │
 * ├─────────────────────────────────────────────────────────┤
 * │ Section 2 ...                                           │
 * └─────────────────────────────────────────────────────────┘
 */

import type { DisplayConfig, SectionData } from "./types";
import { SECTION_TYPES } from "./types";
import {
    convertImageToRGB565,
    createSolidColorRGB565,
    hexToRGB565,
} from "./imageConverter";

// Magic bytes: "DCFG" (Display Config)
const MAGIC = new Uint8Array([0x44, 0x43, 0x46, 0x47]);
const VERSION = 1;
const HEADER_SIZE = 32;

/**
 * Safely convert ArrayBufferLike to ArrayBuffer
 * Always creates a copy to handle SharedArrayBuffer compatibility
 */
function toArrayBuffer(buffer: ArrayBufferLike): ArrayBuffer {
    // Always create a copy to ensure we have a plain ArrayBuffer
    const copy = new ArrayBuffer(buffer.byteLength);
    new Uint8Array(copy).set(new Uint8Array(buffer as unknown as ArrayBuffer));
    return copy;
}

/**
 * Pack DisplayConfig into binary format
 */
export async function packDisplayAssets(
    config: DisplayConfig
): Promise<Uint8Array> {
    const sections: SectionData[] = [];

    // Pack background section
    if (config.enableBackground) {
        const bgSection = await packBackgroundSection(config);
        if (bgSection) {
            sections.push(bgSection);
        }
    }

    // Pack clock section
    if (config.enableClock && config.clock.enabled) {
        const clockSection = packClockSection(config);
        sections.push(clockSection);
    }

    // Pack weather section
    if (config.enableWeather && config.weather.enabled) {
        const weatherSection = packWeatherSection(config);
        sections.push(weatherSection);
    }

    if (config.enableEmoji && config.emoji.enabled) {
        const emojiSection = packEmojiSection(config);
        sections.push(emojiSection);
    }

    // Pack MQTT section
    if (config.enableMqtt && config.mqtt.enabled) {
        const mqttSection = packMqttSection(config);
        sections.push(mqttSection);
    }

    // Calculate total size
    let totalSize = HEADER_SIZE;
    for (const section of sections) {
        totalSize += 1 + 4 + section.data.length; // type + size + data
    }

    // Create buffer
    const buffer = new ArrayBuffer(totalSize);
    const view = new DataView(buffer);
    const uint8 = new Uint8Array(buffer);

    let offset = 0;

    // Write header
    // Magic
    uint8.set(MAGIC, offset);
    offset += 4;

    // Version
    view.setUint16(offset, VERSION, true); // little-endian
    offset += 2;

    // Flags (reserved for future use)
    const flags = config.isDarkMode ? 0x01 : 0x00;
    view.setUint16(offset, flags, true);
    offset += 2;

    // Screen dimensions
    view.setUint16(offset, config.screenWidth, true);
    offset += 2;
    view.setUint16(offset, config.screenHeight, true);
    offset += 2;

    // Color format: 0 = RGB565, 1 = MONO
    view.setUint8(offset, config.colorFormat === "RGB565" ? 0 : 1);
    offset += 1;

    // Section count
    view.setUint8(offset, sections.length);
    offset += 1;

    // Reserved (skip to end of header)
    offset = HEADER_SIZE;

    // Write sections
    for (const section of sections) {
        // Type
        view.setUint8(offset, section.type);
        offset += 1;

        // Size
        view.setUint32(offset, section.data.length, true);
        offset += 4;

        // Data
        uint8.set(section.data, offset);
        offset += section.data.length;
    }

    return uint8;
}

/**
 * Pack background section
 */
async function packBackgroundSection(
    config: DisplayConfig
): Promise<SectionData | null> {
    const { background, screenWidth, screenHeight, colorFormat } = config;

    let imageData: Uint16Array | Uint8Array;

    if (background.mode === "image" && background.imageData) {
        // Convert image to appropriate format
        if (colorFormat === "RGB565") {
            imageData = await convertImageToRGB565(
                background.imageData,
                screenWidth,
                screenHeight
            );
        } else {
            // For mono, we'd use convertImageToMono
            // For now, fall back to solid color
            imageData = createSolidColorRGB565(background.color, screenWidth, screenHeight);
        }
    } else {
        // Solid color background
        imageData = createSolidColorRGB565(
            background.color,
            screenWidth,
            screenHeight
        );
    }

    // Convert to Uint8Array (2 bytes per pixel for RGB565)
    const data = new Uint8Array(toArrayBuffer(imageData.buffer));

    return {
        type: SECTION_TYPES.BACKGROUND,
        data,
    };
}

/**
 * Pack clock widget section
 * Format: [format:1][showSec:1][showDate:1][pos:1][size:1][colorR5G6B5:2][reserved:2] = 9 bytes
 */
function packClockSection(config: DisplayConfig): SectionData {
    const { clock } = config;
    const data = new Uint8Array(9);
    const view = new DataView(toArrayBuffer(data.buffer));

    let offset = 0;

    // Format: 0 = 24h, 1 = 12h
    data[offset++] = clock.format === "12h" ? 1 : 0;

    // Show seconds
    data[offset++] = clock.showSeconds ? 1 : 0;

    // Show date
    data[offset++] = clock.showDate ? 1 : 0;

    // Position (encoded as index)
    const posMap: Record<string, number> = {
        "top-left": 0,
        "top-center": 1,
        "top-right": 2,
        center: 3,
        "bottom-left": 4,
        "bottom-center": 5,
        "bottom-right": 6,
    };
    data[offset++] = posMap[clock.position] ?? 1;

    // Size: 0 = small, 1 = medium, 2 = large
    const sizeMap: Record<string, number> = {
        small: 0,
        medium: 1,
        large: 2,
    };
    data[offset++] = sizeMap[clock.size] ?? 2;

    // Color (RGB565)
    const color565 = hexToRGB565(clock.color);
    view.setUint16(offset, color565, true);
    offset += 2;

    // Reserved
    view.setUint16(offset, 0, true);

    return {
        type: SECTION_TYPES.CLOCK,
        data,
    };
}

/**
 * Pack weather widget section
 * Format: [showIcon:1][showTemp:1][showHum:1][showCity:1][pos:1][interval:2][locationLen:1][location:n]
 */
function packWeatherSection(config: DisplayConfig): SectionData {
    const { weather } = config;

    // Encode location as UTF-8
    const encoder = new TextEncoder();
    const locationBytes = encoder.encode(weather.location);
    const locationLen = Math.min(locationBytes.length, 50); // Max 50 chars

    const headerSize = 8;
    const data = new Uint8Array(headerSize + locationLen);
    const view = new DataView(toArrayBuffer(data.buffer));

    let offset = 0;

    // Flags
    data[offset++] = weather.showIcon ? 1 : 0;
    data[offset++] = weather.showTemp ? 1 : 0;
    data[offset++] = weather.showHumidity ? 1 : 0;
    data[offset++] = weather.showCity ? 1 : 0;

    // Position
    const posMap: Record<string, number> = {
        "top-left": 0,
        "top-center": 1,
        "top-right": 2,
        center: 3,
        "bottom-left": 4,
        "bottom-center": 5,
        "bottom-right": 6,
    };
    data[offset++] = posMap[weather.position] ?? 2;

    // Update interval (minutes)
    view.setUint16(offset, weather.updateInterval, true);
    offset += 2;

    // Location length
    data[offset++] = locationLen;

    // Location string
    data.set(locationBytes.slice(0, locationLen), offset);

    return {
        type: SECTION_TYPES.WEATHER,
        data,
    };
}

/**
 * Pack emoji widget mapping as JSON.
 */
function packEmojiSection(config: DisplayConfig): SectionData {
    const encoder = new TextEncoder();
    const data = encoder.encode(
        JSON.stringify({
            preset: config.emoji.preset,
            size: config.emoji.size,
            position: config.emoji.position,
            currentEmotion: config.emoji.currentEmotion,
            customEmojis: config.emoji.customEmojis || {},
        })
    );

    return {
        type: SECTION_TYPES.EMOJI,
        data,
    };
}

/**
 * Pack MQTT section
 * Format: [brokerLen:1][broker:n][port:2][userLen:1][user:n][passLen:1][pass:n][topicPrefixLen:1][topicPrefix:n]
 */
function packMqttSection(config: DisplayConfig): SectionData {
    const { mqtt } = config;
    const encoder = new TextEncoder();

    const brokerBytes = encoder.encode(mqtt.broker);
    const userBytes = encoder.encode(mqtt.username);
    const passBytes = encoder.encode(mqtt.password);
    const topicPrefixBytes = encoder.encode(mqtt.topicPrefix);

    const brokerLen = Math.min(brokerBytes.length, 100);
    const userLen = Math.min(userBytes.length, 50);
    const passLen = Math.min(passBytes.length, 50);
    const topicPrefixLen = Math.min(topicPrefixBytes.length, 50);

    const dataSize = 1 + brokerLen + 2 + 1 + userLen + 1 + passLen + 1 + topicPrefixLen;
    const data = new Uint8Array(dataSize);
    const view = new DataView(toArrayBuffer(data.buffer));

    let offset = 0;

    // Broker
    data[offset++] = brokerLen;
    data.set(brokerBytes.slice(0, brokerLen), offset);
    offset += brokerLen;

    // Port
    view.setUint16(offset, mqtt.port, true);
    offset += 2;

    // Username
    data[offset++] = userLen;
    data.set(userBytes.slice(0, userLen), offset);
    offset += userLen;

    // Password
    data[offset++] = passLen;
    data.set(passBytes.slice(0, passLen), offset);
    offset += passLen;

    // Topic Prefix
    data[offset++] = topicPrefixLen;
    data.set(topicPrefixBytes.slice(0, topicPrefixLen), offset);
    offset += topicPrefixLen;

    return {
        type: SECTION_TYPES.MQTT,
        data,
    };
}

/**
 * Download binary data as file
 */
export function downloadBinary(data: Uint8Array, filename: string): void {
    // Create a copy to ensure we have a plain ArrayBuffer
    const buffer = toArrayBuffer(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength));
    const blob = new Blob([buffer], { type: "application/octet-stream" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    URL.revokeObjectURL(url);
}

/**
 * Generate default filename based on config
 */
export function generateFilename(config: DisplayConfig, extension: "bin" | "packl" = "bin"): string {
    const timestamp = new Date().toISOString().slice(0, 10);
    return `display_${config.chip}_${config.screenWidth}x${config.screenHeight}_${timestamp}.${extension}`;
}

/**
 * PACKL File Format for XiaoZhi Theme Packs
 * 
 * The .packl format is a themed asset pack that can be:
 * 1. Copied to SD card at /presets/theme/filename.packl
 * 2. Flashed directly to the ESP32's data partition
 * 
 * Format:
 * ┌─────────────────────────────────────────────────────────┐
 * │ PACKL Header (64 bytes)                                 │
 * │   Magic: "PKL1" (4 bytes)                               │
 * │   Version: uint16 (2 bytes) = 1                         │
 * │   Flags: uint16 (2 bytes)                               │
 * │   Theme Name: (32 bytes, null-padded UTF-8)             │
 * │   Data Offset: uint32 (4 bytes)                         │
 * │   Data Size: uint32 (4 bytes)                           │
 * │   Checksum CRC32: uint32 (4 bytes)                      │
 * │   Reserved: (12 bytes)                                  │
 * ├─────────────────────────────────────────────────────────┤
 * │ Display Config Binary (from packDisplayAssets)         │
 * └─────────────────────────────────────────────────────────┘
 */

const PACKL_MAGIC = new Uint8Array([0x50, 0x4B, 0x4C, 0x31]); // "PKL1"
const PACKL_VERSION = 1;
const PACKL_HEADER_SIZE = 64;

/**
 * CRC32 lookup table - generated once at module load
 */
const CRC32_TABLE = (function generateCRC32Table(): Uint32Array {
    const table = new Uint32Array(256);
    for (let i = 0; i < 256; i++) {
        let c = i;
        for (let j = 0; j < 8; j++) {
            c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
        }
        table[i] = c;
    }
    return table;
})();

/**
 * Calculate CRC32 checksum using cached lookup table
 */
function crc32(data: Uint8Array): number {
    let crc = 0xFFFFFFFF;
    for (let i = 0; i < data.length; i++) {
        crc = CRC32_TABLE[(crc ^ data[i]) & 0xFF] ^ (crc >>> 8);
    }
    return (crc ^ 0xFFFFFFFF) >>> 0;
}

/**
 * Pack DisplayConfig into .packl format for SD card
 */
export async function packDisplayAsPackl(
    config: DisplayConfig,
    themeName: string = "custom_theme"
): Promise<Uint8Array> {
    // First, get the binary display config
    const displayData = await packDisplayAssets(config);

    // Create PACKL buffer
    const totalSize = PACKL_HEADER_SIZE + displayData.length;
    const buffer = new ArrayBuffer(totalSize);
    const view = new DataView(buffer);
    const uint8 = new Uint8Array(buffer);

    let offset = 0;

    // Magic: "PKL1"
    uint8.set(PACKL_MAGIC, offset);
    offset += 4;

    // Version
    view.setUint16(offset, PACKL_VERSION, true);
    offset += 2;

    // Flags (reserved)
    view.setUint16(offset, 0, true);
    offset += 2;

    // Theme Name (32 bytes, null-padded)
    const encoder = new TextEncoder();
    const nameBytes = encoder.encode(themeName.slice(0, 31));
    uint8.set(nameBytes, offset);
    offset = 8 + 32; // Skip to after theme name

    // Data Offset
    view.setUint32(offset, PACKL_HEADER_SIZE, true);
    offset += 4;

    // Data Size
    view.setUint32(offset, displayData.length, true);
    offset += 4;

    // Calculate checksum of display data
    const checksum = crc32(displayData);
    view.setUint32(offset, checksum, true);
    offset += 4;

    // Reserved (skip to end of header)
    offset = PACKL_HEADER_SIZE;

    // Write display data
    uint8.set(displayData, offset);

    return uint8;
}

/**
 * Download as .packl file for SD card
 */
export async function downloadAsPackl(config: DisplayConfig, themeName?: string): Promise<void> {
    const name = themeName || config.name || "custom_theme";
    const packlData = await packDisplayAsPackl(config, name);
    const filename = `${name.replace(/[^a-zA-Z0-9_]/g, "_")}.packl`;
    downloadBinary(packlData, filename);
}

/**
 * Get suggested SD card path for the theme
 */
export function getSdCardPath(themeName: string): string {
    const safeName = themeName.replace(/[^a-zA-Z0-9_]/g, "_");
    return `/presets/theme/${safeName}.packl`;
}
