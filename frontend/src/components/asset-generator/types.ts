/**
 * Types cho Asset Generator
 * Dựa trên xiaozhi-assets-generator
 * BOARD_PRESETS được tự động extract từ firmware/main/boards
 */

// Chip types
export type ChipModel = "esp32" | "esp32s3" | "esp32c3" | "esp32c6" | "esp32p4";

// Screen types
export type ScreenType = "LCD" | "OLED";
export type ColorFormat = "RGB565" | "MONO";

// Preset boards
export interface BoardPreset {
  name: string;
  chip: ChipModel;
  screenType: ScreenType;
  width: number;
  height: number;
  colorFormat: ColorFormat;
  /** Data partition address for safe theme flashing (e.g. SPIFFS/LittleFS) */
  dataPartitionAddress: number;
}

/**
 * Board presets extracted from firmware/main/boards
 * Data partition addresses:
 * - ESP32-S3 16MB: 0x310000
 * - ESP32-S3 8MB: 0x290000
 * - ESP32-C3 4MB: 0x290000
 * - ESP32-C6: 0x290000
 * - ESP32-P4: 0x310000
 */
export const BOARD_PRESETS: BoardPreset[] = [
  // === Vietnam Boards (Priority) ===
  { name: "xiaozhi-ai-iot-vietnam-es3n28p-lcd-2.8", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "xiaozhi-ai-iot-vietnam-1st", chip: "esp32s3", screenType: "LCD", width: 284, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "xiaozhi-ai-iot-vietnam-dtd", chip: "esp32s3", screenType: "LCD", width: 240, height: 320, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },

  // === ESP32-S3 Boards (most common) ===
  { name: "esp-box-3", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "esp-box", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "esp-box-lite", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "lichuang-dev", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "m5stack-core-s3", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "yunliao-s3", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "zhengchen-cam", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "zhengchen-cam-ml307", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "atk-dnesp32s3-box", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "atk-dnesp32s3", chip: "esp32s3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },

  // === ESP32-S3 240x240 TFT ===
  { name: "genjutech-s3-1.54tft", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "esp-sparkbot", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "electron-bot", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "otto-robot", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "minsi-k08-dual", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "movecall-cuican-esp32s3", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "movecall-moji-esp32s3", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "sp-esp32-s3-1.28-box", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "sp-esp32-s3-1.54-muma", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "atk-dnesp32s3-box0", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "xingzhi-cube-1.54tft-ml307", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "xingzhi-cube-1.54tft-wifi", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "zhengchen-1.54tft-ml307", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "zhengchen-1.54tft-wifi", chip: "esp32s3", screenType: "LCD", width: 240, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },

  // === ESP32-S3 240x320 (Portrait) ===
  { name: "df-k10", chip: "esp32s3", screenType: "LCD", width: 240, height: 320, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "jiuchuan-s3", chip: "esp32s3", screenType: "LCD", width: 240, height: 320, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "atk-dnesp32s3-box2-4g", chip: "esp32s3", screenType: "LCD", width: 240, height: 320, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "atk-dnesp32s3-box2-wifi", chip: "esp32s3", screenType: "LCD", width: 240, height: 320, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },

  // === ESP32-S3 Small OLED/TFT ===
  { name: "aipi-lite", chip: "esp32s3", screenType: "LCD", width: 128, height: 128, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "atoms3-echo-base", chip: "esp32s3", screenType: "LCD", width: 128, height: 128, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "atoms3r-echo-base", chip: "esp32s3", screenType: "LCD", width: 128, height: 128, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "magiclick-2p4", chip: "esp32s3", screenType: "LCD", width: 128, height: 128, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "magiclick-2p5", chip: "esp32s3", screenType: "LCD", width: 128, height: 128, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "xingzhi-cube-0.85tft-ml307", chip: "esp32s3", screenType: "LCD", width: 128, height: 128, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "xingzhi-cube-0.85tft-wifi", chip: "esp32s3", screenType: "LCD", width: 128, height: 128, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "du-chatx", chip: "esp32s3", screenType: "LCD", width: 128, height: 160, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "mixgo-nova", chip: "esp32s3", screenType: "LCD", width: 128, height: 160, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "kevin-box-2", chip: "esp32s3", screenType: "OLED", width: 128, height: 64, colorFormat: "MONO", dataPartitionAddress: 0x290000 },
  { name: "tudouzi", chip: "esp32s3", screenType: "OLED", width: 128, height: 64, colorFormat: "MONO", dataPartitionAddress: 0x290000 },
  { name: "xingzhi-cube-0.96oled-ml307", chip: "esp32s3", screenType: "OLED", width: 128, height: 64, colorFormat: "MONO", dataPartitionAddress: 0x290000 },
  { name: "xingzhi-cube-0.96oled-wifi", chip: "esp32s3", screenType: "OLED", width: 128, height: 64, colorFormat: "MONO", dataPartitionAddress: 0x290000 },
  { name: "bread-compact-ml307", chip: "esp32s3", screenType: "OLED", width: 128, height: 32, colorFormat: "MONO", dataPartitionAddress: 0x290000 },
  { name: "bread-compact-wifi", chip: "esp32s3", screenType: "OLED", width: 128, height: 32, colorFormat: "MONO", dataPartitionAddress: 0x290000 },

  // === ESP32-S3 Round/Large Displays ===
  { name: "echoear", chip: "esp32s3", screenType: "LCD", width: 360, height: 360, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "esp32-s3-touch-lcd-1.85", chip: "esp32s3", screenType: "LCD", width: 360, height: 360, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "esp32-s3-touch-lcd-1.85c", chip: "esp32s3", screenType: "LCD", width: 360, height: 360, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "taiji-pi-s3", chip: "esp32s3", screenType: "LCD", width: 360, height: 360, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "esp32-s3-touch-amoled-1.8", chip: "esp32s3", screenType: "LCD", width: 368, height: 448, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "esp32-s3-touch-lcd-1.46", chip: "esp32s3", screenType: "LCD", width: 412, height: 412, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "sensecap-watcher", chip: "esp32s3", screenType: "LCD", width: 412, height: 412, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "waveshare-s3-touch-amoled-1.75", chip: "esp32s3", screenType: "LCD", width: 466, height: 466, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "waveshare-s3-touch-amoled-2.06", chip: "esp32s3", screenType: "LCD", width: 410, height: 502, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "esp32-s3-touch-lcd-3.5", chip: "esp32s3", screenType: "LCD", width: 480, height: 320, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "waveshare-s3-touch-lcd-3.5b", chip: "esp32s3", screenType: "LCD", width: 480, height: 320, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "esp-s3-lcd-ev-board", chip: "esp32s3", screenType: "LCD", width: 480, height: 480, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "waveshare-s3-touch-lcd-4b", chip: "esp32s3", screenType: "LCD", width: 480, height: 480, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "esp-s3-lcd-ev-board-2", chip: "esp32s3", screenType: "LCD", width: 800, height: 480, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "kevin-yuying-313lcd", chip: "esp32s3", screenType: "LCD", width: 376, height: 960, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "waveshare-s3-touch-lcd-3.49", chip: "esp32s3", screenType: "LCD", width: 172, height: 640, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },

  // === ESP32-S3 Other Sizes ===
  { name: "labplus-ledong-v2", chip: "esp32s3", screenType: "LCD", width: 320, height: 172, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "labplus-mpython-v3", chip: "esp32s3", screenType: "LCD", width: 320, height: 172, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "kevin-sp-v4-dev", chip: "esp32s3", screenType: "LCD", width: 240, height: 280, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "waveshare-s3-touch-lcd-1.83", chip: "esp32s3", screenType: "LCD", width: 240, height: 284, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "xiaozhi-ai-iot-vietnam-1st", chip: "esp32s3", screenType: "LCD", width: 284, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "xingzhi-cube-1.83tft-wifi", chip: "esp32s3", screenType: "LCD", width: 284, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },

  // === ESP32-C3 Boards ===
  { name: "surfer-c3-1.14tft", chip: "esp32c3", screenType: "LCD", width: 240, height: 135, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "lichuang-c3-dev", chip: "esp32c3", screenType: "LCD", width: 320, height: 240, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "esp-hi", chip: "esp32c3", screenType: "LCD", width: 160, height: 80, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "magiclick-c3", chip: "esp32c3", screenType: "LCD", width: 128, height: 128, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "magiclick-c3-v2", chip: "esp32c3", screenType: "LCD", width: 128, height: 128, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },
  { name: "xmini-c3", chip: "esp32c3", screenType: "OLED", width: 128, height: 64, colorFormat: "MONO", dataPartitionAddress: 0x290000 },
  { name: "xmini-c3-4g", chip: "esp32c3", screenType: "OLED", width: 128, height: 64, colorFormat: "MONO", dataPartitionAddress: 0x290000 },
  { name: "xmini-c3-v3", chip: "esp32c3", screenType: "OLED", width: 128, height: 64, colorFormat: "MONO", dataPartitionAddress: 0x290000 },

  // === ESP32-C6 Boards ===
  { name: "waveshare-c6-lcd-1.69", chip: "esp32c6", screenType: "LCD", width: 240, height: 280, colorFormat: "RGB565", dataPartitionAddress: 0x290000 },

  // === ESP32-P4 Boards (high-end) ===
  { name: "waveshare-p4-nano", chip: "esp32p4", screenType: "LCD", width: 800, height: 1280, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "waveshare-p4-wifi6-touch-lcd-4b", chip: "esp32p4", screenType: "LCD", width: 720, height: 720, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "waveshare-p4-wifi6-touch-lcd-7b", chip: "esp32p4", screenType: "LCD", width: 1024, height: 600, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },
  { name: "wireless-tag-wtp4c5mp07s", chip: "esp32p4", screenType: "LCD", width: 1024, height: 600, colorFormat: "RGB565", dataPartitionAddress: 0x310000 },

  // === ESP32 (Classic) ===
  { name: "bread-compact-esp32", chip: "esp32", screenType: "OLED", width: 128, height: 32, colorFormat: "MONO", dataPartitionAddress: 0x290000 },
];

// Wake word models
export interface WakeWordModel {
  name: string;
  displayName: string;
  wn9s?: string; // For C3/C6
  wn9?: string; // For S3/P4
}

export const WAKE_WORD_MODELS: WakeWordModel[] = [
  { name: "hilexin", displayName: "Hi, Espressif", wn9s: "wn9s_hilexin", wn9: "wn9_hilexin" },
  { name: "hiesp", displayName: "Hi, ESP", wn9s: "wn9s_hiesp", wn9: "wn9_hiesp" },
  { name: "nihaoxiaozhi", displayName: "Xin chào XiaoZhi", wn9s: "wn9s_nihaoxiaozhi", wn9: "wn9_nihaoxiaozhi_tts" },
  { name: "xiaomeitongxue", displayName: "XiaoMei", wn9: "wn9_xiaomeitongxue_tts" },
  { name: "xiaoaitongxue", displayName: "XiaoAi", wn9: "wn9_xiaoaitongxue" },
  { name: "alexa", displayName: "Alexa", wn9: "wn9_alexa" },
  { name: "jarvis", displayName: "Jarvis", wn9: "wn9_jarvis_tts" },
  { name: "computer", displayName: "Computer", wn9: "wn9_computer_tts" },
  { name: "hijason", displayName: "Hi, Jason", wn9s: "wn9s_hijason_tts2", wn9: "wn9_hijason_tts2" },
  { name: "himfive", displayName: "Hi, M Five", wn9: "wn9_himfive" },
  { name: "hiwalle", displayName: "Hi, Wall-E", wn9: "wn9_hiwalle_tts2" },
  { name: "xiaozhi", displayName: "Hi, Xiaozhi", wn9s: "wn9s_nihaoxiaozhi", wn9: "wn9_nihaoxiaozhi_tts" },
];

// Font presets
export interface FontPreset {
  name: string;
  displayName: string;
  file: string;
  size: number;
  bpp: number;
}

export const FONT_PRESETS: FontPreset[] = [
  { name: "puhui_14_1", displayName: "Alibaba PuHuiTi 14px (bpp1)", file: "font_puhui_14_1.bin", size: 14, bpp: 1 },
  { name: "puhui_16_4", displayName: "Alibaba PuHuiTi 16px (bpp4)", file: "font_puhui_16_4.bin", size: 16, bpp: 4 },
  { name: "puhui_20_4", displayName: "Alibaba PuHuiTi 20px (bpp4)", file: "font_puhui_20_4.bin", size: 20, bpp: 4 },
  { name: "puhui_30_4", displayName: "Alibaba PuHuiTi 30px (bpp4)", file: "font_puhui_30_4.bin", size: 30, bpp: 4 },
];

// Emoji emotions
export const EMOJI_EMOTIONS = [
  { name: "neutral", emoji: "😶", displayName: "Neutral" },
  { name: "happy", emoji: "🙂", displayName: "Happy" },
  { name: "laughing", emoji: "😆", displayName: "Laughing" },
  { name: "funny", emoji: "😂", displayName: "Funny" },
  { name: "sad", emoji: "😔", displayName: "Sad" },
  { name: "angry", emoji: "😠", displayName: "Angry" },
  { name: "crying", emoji: "😭", displayName: "Crying" },
  { name: "loving", emoji: "😍", displayName: "Loving" },
  { name: "embarrassed", emoji: "😳", displayName: "Embarrassed" },
  { name: "surprised", emoji: "😯", displayName: "Surprised" },
  { name: "shocked", emoji: "😱", displayName: "Shocked" },
  { name: "thinking", emoji: "🤔", displayName: "Thinking" },
  { name: "winking", emoji: "😉", displayName: "Winking" },
  { name: "cool", emoji: "😎", displayName: "Cool" },
  { name: "relaxed", emoji: "😌", displayName: "Relaxed" },
  { name: "delicious", emoji: "🤤", displayName: "Delicious" },
  { name: "kissy", emoji: "😘", displayName: "Kissy" },
  { name: "confident", emoji: "😏", displayName: "Confident" },
  { name: "sleepy", emoji: "😴", displayName: "Sleepy" },
  { name: "silly", emoji: "😜", displayName: "Silly" },
  { name: "confused", emoji: "🙄", displayName: "Confused" },
] as const;

// Emoji preset packs
export interface EmojiPreset {
  name: string;
  displayName: string;
  size: number;
  path: string;
}

export const EMOJI_PRESETS: EmojiPreset[] = [
  { name: "twemoji32", displayName: "Twemoji 32x32", size: 32, path: "twemoji32" },
  { name: "twemoji64", displayName: "Twemoji 64x64", size: 64, path: "twemoji64" },
];

// Full asset configuration
export interface AssetConfig {
  // Hardware
  chip: ChipModel;
  screenWidth: number;
  screenHeight: number;
  colorFormat: ColorFormat;

  // Wake word
  wakeWord: string;

  // Font
  fontPreset: string;
  customFont?: File;
  customFontSize?: number;
  customFontBpp?: number;

  // Emoji
  emojiPreset: string;
  emojiSize: number;
  customEmojis?: Record<string, File>;

  // Background
  lightBackgroundColor: string;
  darkBackgroundColor: string;
  lightBackgroundImage?: File;
  darkBackgroundImage?: File;
  lightTextColor: string;
  darkTextColor: string;

  // Lunar Calendar (Âm lịch) - Vietnamese market
  enableLunarCalendar?: boolean;
  lunarFormat?: "short" | "full" | "can_chi" | "tiet_khi";
  showLunarSpecialDays?: boolean;
}

// Default config
export const DEFAULT_ASSET_CONFIG: AssetConfig = {
  chip: "esp32s3",
  screenWidth: 320,
  screenHeight: 240,
  colorFormat: "RGB565",
  wakeWord: "nihaoxiaozhi",
  fontPreset: "puhui_20_4",
  emojiPreset: "twemoji64",
  emojiSize: 64,
  lightBackgroundColor: "#ffffff",
  darkBackgroundColor: "#121212",
  lightTextColor: "#000000",
  darkTextColor: "#ffffff",
  // Lunar calendar defaults
  enableLunarCalendar: true,
  lunarFormat: "short",
  showLunarSpecialDays: true,
};
