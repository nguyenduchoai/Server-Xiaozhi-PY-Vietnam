/**
 * AssetsBuilder — Orchestrator for generating assets.bin
 * Ported from 78/xiaozhi-assets-generator (MIT License)
 *
 * Coordinates SpiffsGenerator + WakenetModelPacker + font/emoji/background
 * processing to produce a complete assets.bin binary file in the browser.
 *
 * Simplified adaptation for the Xiaozhi AI IoT Vietnam platform:
 * - No WASM font converter (uses preset fonts only for now)
 * - No WASM GIF scaler (pass-through for GIFs)
 * - Supports preset + custom emoji images
 * - Supports preset wake word models
 * - Generates index.json + packs into SPIFFS binary
 */

import { SpiffsGenerator, type ProgressCallback } from "./SpiffsGenerator";
import { WakenetModelPacker } from "./WakenetModelPacker";
import {
  type AssetConfig,
  WAKE_WORD_MODELS,
  FONT_PRESETS,
  EMOJI_EMOTIONS,
  EMOJI_PRESETS,
} from "./types";

export interface BuildResult {
  blob: Blob;
  filename: string;
  stats: {
    totalFiles: number;
    totalSize: number;
    fileTypes: Record<string, number>;
  };
}

type CustomEmojiFile = File | Blob;
type CustomEmojiValue =
  | CustomEmojiFile
  | {
      file?: CustomEmojiFile;
      isCustom?: boolean;
    };

export type CustomEmojiSources = Record<string, CustomEmojiValue | undefined>;

function getCustomEmojiFile(value: CustomEmojiValue | undefined): CustomEmojiFile | undefined {
  if (!value) {
    return undefined;
  }

  if (value instanceof Blob) {
    return value;
  }

  if ("file" in value && value.file instanceof Blob) {
    return value.file;
  }

  return undefined;
}

function getImageAssetExtension(file: CustomEmojiFile): string {
  const name = file instanceof File ? file.name.toLowerCase() : "";
  const extension = name.split(".").pop();

  if (extension && ["png", "gif", "jpg", "jpeg", "webp"].includes(extension)) {
    return extension === "jpeg" ? "jpg" : extension;
  }

  if (file.type === "image/gif") {
    return "gif";
  }
  if (file.type === "image/jpeg") {
    return "jpg";
  }
  if (file.type === "image/webp") {
    return "webp";
  }

  return "png";
}

/**
 * Convert an image File/Blob to RGB565 raw format with lv_image_dsc_t header
 * Used for background images on the ESP32 display
 */
async function convertImageToRgb565(
  imageFile: File | Blob,
  targetWidth: number,
  targetHeight: number,
): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const blob = imageFile instanceof File ? imageFile : imageFile;
    const url = URL.createObjectURL(blob);
    const img = new Image();

    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = targetWidth;
        canvas.height = targetHeight;
        const ctx = canvas.getContext("2d")!;

        // Draw scaled image to fill the canvas
        ctx.drawImage(img, 0, 0, targetWidth, targetHeight);

        const imageData = ctx.getImageData(0, 0, targetWidth, targetHeight);
        const pixels = imageData.data;

        // 64-byte header (lv_image_dsc_t compatible) + RGB565 pixel data
        const headerSize = 64;
        const pixelDataSize = targetWidth * targetHeight * 2; // 2 bytes per pixel (RGB565)
        const rawData = new ArrayBuffer(headerSize + pixelDataSize);
        const view = new DataView(rawData);

        // Write simple lv_image_dsc_t header
        // Offset 0-3: magic/flags
        view.setUint32(0, 0x19, true); // CF_TRUE_COLOR = 0x19
        // Offset 4-7: width
        view.setUint16(4, targetWidth, true);
        // Offset 6-7: height
        view.setUint16(6, targetHeight, true);
        // Offset 8-11: data size
        view.setUint32(8, pixelDataSize, true);
        // Rest of header is zeros

        // Convert RGBA to RGB565
        let pixelOffset = headerSize;
        for (let i = 0; i < pixels.length; i += 4) {
          const r = pixels[i];
          const g = pixels[i + 1];
          const b = pixels[i + 2];

          // RGB565: RRRRR GGGGGG BBBBB
          const rgb565 = ((r & 0xf8) << 8) | ((g & 0xfc) << 3) | (b >> 3);
          view.setUint16(pixelOffset, rgb565, true); // Little-endian
          pixelOffset += 2;
        }

        URL.revokeObjectURL(url);
        resolve(rawData);
      } catch (error) {
        URL.revokeObjectURL(url);
        reject(error);
      }
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Failed to load image for RGB565 conversion"));
    };

    img.src = url;
  });
}

/**
 * Read a File object as ArrayBuffer
 */
function fileToArrayBuffer(file: File | Blob): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsArrayBuffer(file);
  });
}

/**
 * Build and generate assets.bin from an AssetConfig
 */
export async function buildAssetsBin(
  config: AssetConfig,
  customEmojis: CustomEmojiSources = {},
  progressCallback?: ProgressCallback,
): Promise<BuildResult> {
  const spiffs = new SpiffsGenerator();
  const wakenetPacker = new WakenetModelPacker();

  progressCallback?.(0, "Initializing...");

  // ============================================================
  // 1. Generate index.json
  // ============================================================
  progressCallback?.(5, "Generating index.json...");

  const wakeWordModel = WAKE_WORD_MODELS.find((m) => m.name === config.wakeWord);
  const isC3OrC6 = config.chip === "esp32c3" || config.chip === "esp32c6";
  const wakeWordFileName = isC3OrC6 ? wakeWordModel?.wn9s : wakeWordModel?.wn9;

  const fontPreset = FONT_PRESETS.find((f) => f.name === config.fontPreset);
  const requestedEmojiPreset = EMOJI_PRESETS.find((p) => p.name === config.emojiPreset);
  const fallbackEmojiPreset =
    requestedEmojiPreset ??
    EMOJI_PRESETS.find((p) => p.size === config.emojiSize) ??
    EMOJI_PRESETS.find((p) => p.name === "twemoji64") ??
    EMOJI_PRESETS[0];

  const indexJson: Record<string, unknown> = {
    version: 1,
    chip_model: config.chip,
    display_config: {
      width: config.screenWidth,
      height: config.screenHeight,
      monochrome: config.colorFormat === "MONO",
      color: config.colorFormat,
    },
  };

  // Wake word model reference
  if (wakeWordFileName) {
    indexJson.srmodels = "srmodels.bin";
  }

  // Font reference
  if (fontPreset) {
    indexJson.text_font = fontPreset.file;
  }

  // Skin/theme
  indexJson.skin = {
    light: {
      text_color: config.lightTextColor,
      background_color: config.lightBackgroundColor,
      ...(config.lightBackgroundImage ? { background_image: "background_light.raw" } : {}),
    },
    dark: {
      text_color: config.darkTextColor,
      background_color: config.darkBackgroundColor,
      ...(config.darkBackgroundImage ? { background_image: "background_dark.raw" } : {}),
    },
  };

  const emojiEntries: Array<{ name: string; file: string }> = [];
  const missingEmotions: string[] = [];

  // ============================================================
  // 2. Pack wake word model → srmodels.bin
  // ============================================================
  if (wakeWordFileName) {
    progressCallback?.(10, `Loading wake word model: ${wakeWordFileName}...`);

    const loaded = await wakenetPacker.loadModelFromShare(wakeWordFileName);
    if (loaded) {
      progressCallback?.(25, "Packing srmodels.bin...");
      const srmodelsData = wakenetPacker.packModels();
      spiffs.addFile("srmodels.bin", srmodelsData);
    } else {
      console.warn(`Failed to load wake word model: ${wakeWordFileName}, skipping`);
    }
  }

  // ============================================================
  // 3. Load preset font .bin
  // ============================================================
  if (fontPreset) {
    progressCallback?.(30, `Loading font: ${fontPreset.displayName}...`);
    try {
      const fontResp = await fetch(`./static/fonts/${fontPreset.file}`);
      if (fontResp.ok) {
        const fontData = await fontResp.arrayBuffer();
        spiffs.addFile(fontPreset.file, fontData);
      } else {
        console.warn(`Font file not available on server: ${fontPreset.file}`);
      }
    } catch (error) {
      console.warn(`Failed to load font: ${fontPreset.file}`, error);
    }
  }

  // ============================================================
  // 4. Load emoji images (preset or custom)
  // ============================================================
  progressCallback?.(40, "Processing emoji images...");
  const totalEmojis = EMOJI_EMOTIONS.length;

  for (let i = 0; i < EMOJI_EMOTIONS.length; i++) {
    const emotion = EMOJI_EMOTIONS[i];
    progressCallback?.(
      40 + (i / totalEmojis) * 30,
      `Processing emoji: ${emotion.displayName}...`,
    );

    const customFile = getCustomEmojiFile(customEmojis[emotion.name]);
    let packed = false;

    // Check if user has a custom emoji for this emotion.
    if (customFile) {
      const extension = getImageAssetExtension(customFile);
      const filename = `${emotion.name}.${extension}`;
      const imageData = await fileToArrayBuffer(customFile);
      spiffs.addFile(filename, imageData, {
        width: config.emojiSize,
        height: config.emojiSize,
      });
      emojiEntries.push({ name: emotion.name, file: filename });
      packed = true;
    } else if (fallbackEmojiPreset) {
      // Load from preset so custom packs still keep a full emotion mapping.
      try {
        const emojiResp = await fetch(
          `./static/emojis/${fallbackEmojiPreset.path}/${emotion.name}.png`,
        );
        if (emojiResp.ok) {
          const filename = `${emotion.name}.png`;
          const emojiData = await emojiResp.arrayBuffer();
          spiffs.addFile(filename, emojiData, {
            width: fallbackEmojiPreset.size,
            height: fallbackEmojiPreset.size,
          });
          emojiEntries.push({ name: emotion.name, file: filename });
          packed = true;
        } else {
          console.warn(`Emoji not found: ${fallbackEmojiPreset.path}/${emotion.name}.png`);
        }
      } catch {
        console.warn(`Failed to load emoji: ${emotion.name}`);
      }
    }

    if (!packed) {
      missingEmotions.push(emotion.name);
    }
  }

  if (missingEmotions.length > 0) {
    throw new Error(`Missing emoji assets for: ${missingEmotions.join(", ")}`);
  }

  indexJson.emoji_collection = emojiEntries;

  // ============================================================
  // 5. Process background images
  // ============================================================
  if (config.lightBackgroundImage) {
    progressCallback?.(75, "Converting light background to RGB565...");
    const rawLight = await convertImageToRgb565(
      config.lightBackgroundImage,
      config.screenWidth,
      config.screenHeight,
    );
    spiffs.addFile("background_light.raw", rawLight);
  }

  if (config.darkBackgroundImage) {
    progressCallback?.(80, "Converting dark background to RGB565...");
    const rawDark = await convertImageToRgb565(
      config.darkBackgroundImage,
      config.screenWidth,
      config.screenHeight,
    );
    spiffs.addFile("background_dark.raw", rawDark);
  }

  // ============================================================
  // 6. Generate final SPIFFS binary
  // ============================================================
  progressCallback?.(85, "Writing emotion mapping...");
  const indexJsonStr = JSON.stringify(indexJson, null, 2);
  const indexJsonData = new TextEncoder().encode(indexJsonStr);
  spiffs.addFile("index.json", indexJsonData.buffer);

  progressCallback?.(88, "Generating assets.bin...");

  const assetsBinData = await spiffs.generate((progress, message) => {
    progressCallback?.(88 + progress * 0.12, message);
  });

  const stats = spiffs.getStats();
  const blob = new Blob([assetsBinData], { type: "application/octet-stream" });
  const filename = `assets_${config.chip}_${config.screenWidth}x${config.screenHeight}.bin`;

  progressCallback?.(100, "Completed!");

  return {
    blob,
    filename,
    stats: {
      totalFiles: stats.fileCount,
      totalSize: assetsBinData.byteLength,
      fileTypes: stats.fileTypes,
    },
  };
}
