/**
 * Asset Generator Dialog - Semi Design implementation
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Cpu,
  Mic,
  Type,
  Smile,
  Image,
  Download,
  Settings2,
  Check,
} from "lucide-react";

import { Modal, Button, Tabs, TabPane, Input, Select, Radio, Typography } from "@douyinfe/semi-ui";
import { cn } from "@/lib/utils";

import {
  type AssetConfig,
  type ChipModel,
  BOARD_PRESETS,
  WAKE_WORD_MODELS,
  FONT_PRESETS,
  EMOJI_PRESETS,
  DEFAULT_ASSET_CONFIG,
} from "./types";

const { Title, Text } = Typography;

interface AssetGeneratorDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  deviceName?: string;
  deviceBoard?: string;
}

export function AssetGeneratorDialog({
  open,
  onOpenChange,
  deviceName,
  deviceBoard: _deviceBoard,
}: AssetGeneratorDialogProps) {
  const { t } = useTranslation(["devices", "common"]);
  const [activeTab, setActiveTab] = useState("chip");
  const [config, setConfig] = useState<AssetConfig>(DEFAULT_ASSET_CONFIG);
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<string>("");

  // Update config helper
  const updateConfig = <K extends keyof AssetConfig>(
    key: K,
    value: AssetConfig[K]
  ) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  // Handle preset selection
  const handlePresetSelect = (presetName: string) => {
    const preset = BOARD_PRESETS.find((p) => p.name === presetName);
    if (preset) {
      setSelectedPreset(presetName);
      updateConfig("chip", preset.chip);
      updateConfig("screenWidth", preset.width);
      updateConfig("screenHeight", preset.height);
      updateConfig("colorFormat", preset.colorFormat);
    }
  };

  // Handle wake word selection
  const handleWakeWordSelect = (wakeWordName: string) => {
    updateConfig("wakeWord", wakeWordName);
  };

  // Handle generate assets
  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      // TODO: Implement actual asset generation
      await new Promise((resolve) => setTimeout(resolve, 2000));

      // Create a mock assets.bin file for download
      const blob = new Blob(["Assets generated for " + deviceName], {
        type: "application/octet-stream",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `assets_${config.chip}_${config.screenWidth}x${config.screenHeight}.bin`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      alert(t("asset_generated_success", "File assets.bin đã được tạo thành công!"));
    } catch (error) {
      console.error("Error generating assets:", error);
      alert(t("asset_generated_error", "Có lỗi xảy ra khi tạo file assets"));
    } finally {
      setIsGenerating(false);
    }
  };

  // Check if wake word is compatible with selected chip
  const isWakeWordCompatible = (wakeWord: typeof WAKE_WORD_MODELS[0]) => {
    const isC3orC6 = config.chip === "esp32c3" || config.chip === "esp32c6";
    if (isC3orC6) {
      return !!wakeWord.wn9s;
    }
    return !!wakeWord.wn9;
  };

  const tabs = [
    { id: "chip", label: t("chip_screen", "Chip & Màn hình"), icon: Cpu },
    { id: "wakeword", label: t("wake_word", "Từ đánh thức"), icon: Mic },
    { id: "font", label: t("font", "Font chữ"), icon: Type },
    { id: "emoji", label: t("emoji", "Biểu cảm"), icon: Smile },
    { id: "background", label: t("background", "Nền"), icon: Image },
  ];

  return (
    <Modal
      title={
        <div className="flex items-center gap-2">
          <Settings2 className="h-5 w-5" />
          <Title heading={5} className="!mb-0">
            {t("customize_device_ui", "Tùy chỉnh giao diện thiết bị")}
          </Title>
        </div>
      }
      visible={open}
      onCancel={() => onOpenChange(false)}
      footer={null}
      width={900}
      style={{ top: 40 }}
      bodyStyle={{ maxHeight: "calc(90vh - 120px)", overflowY: "auto" }}
    >
      <Text type="tertiary" className="block mb-4">
        {deviceName
          ? t("customize_device_desc", "Tạo file assets.bin để cá nhân hóa thiết bị {{name}}", { name: deviceName })
          : t("customize_device_desc_generic", "Tạo file assets.bin để cá nhân hóa thiết bị của bạn")}
      </Text>

      <Tabs type="line" activeKey={activeTab} onChange={(key) => setActiveTab(key)}>
        {tabs.map((tab) => (
          <TabPane
            key={tab.id}
            tab={
              <span className="flex items-center gap-1.5">
                <tab.icon className="h-4 w-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </span>
            }
            itemKey={tab.id}
          >
            {/* Tab 1: Chip & Screen */}
            {tab.id === "chip" && (
              <div className="space-y-4 mt-4">
                <div>
                  <Text strong size="small" className="block mb-3">
                    {t("select_board_preset", "Chọn board có sẵn")}
                  </Text>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {BOARD_PRESETS.map((preset) => (
                      <button
                        key={preset.name}
                        onClick={() => handlePresetSelect(preset.name)}
                        className={cn(
                          "flex items-center justify-between p-3 rounded-lg border text-left transition-colors",
                          selectedPreset === preset.name
                            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                            : "border-gray-200 dark:border-gray-700 hover:border-blue-300"
                        )}
                      >
                        <div>
                          <Text strong size="small">{preset.name}</Text>
                          <Text type="tertiary" size="small" className="block">
                            {preset.chip.toUpperCase()} • {preset.width}x{preset.height} • {preset.colorFormat}
                          </Text>
                        </div>
                        {selectedPreset === preset.name && (
                          <Check className="h-4 w-4 text-blue-500" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="border-t pt-4">
                  <Text strong size="small" className="block mb-3">
                    {t("custom_config", "Hoặc tùy chỉnh")}
                  </Text>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <Text size="small">{t("chip_model", "Loại chip")}</Text>
                      <Select
                        value={config.chip}
                        onChange={(v) => {
                          updateConfig("chip", v as ChipModel);
                          setSelectedPreset("");
                        }}
                        style={{ width: "100%" }}
                      >
                        <Select.Option value="esp32s3">ESP32-S3</Select.Option>
                        <Select.Option value="esp32c3">ESP32-C3</Select.Option>
                        <Select.Option value="esp32c6">ESP32-C6</Select.Option>
                        <Select.Option value="esp32p4">ESP32-P4</Select.Option>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Text size="small">{t("screen_width", "Chiều rộng")}</Text>
                      <Input
                        type="number"
                        value={String(config.screenWidth)}
                        onChange={(value) => {
                          updateConfig("screenWidth", parseInt(String(value)) || 320);
                          setSelectedPreset("");
                        }}
                      />
                    </div>

                    <div className="space-y-2">
                      <Text size="small">{t("screen_height", "Chiều cao")}</Text>
                      <Input
                        type="number"
                        value={String(config.screenHeight)}
                        onChange={(value) => {
                          updateConfig("screenHeight", parseInt(String(value)) || 240);
                          setSelectedPreset("");
                        }}
                      />
                    </div>

                    <div className="space-y-2">
                      <Text size="small">{t("color_format", "Màu sắc")}</Text>
                      <Select
                        value={config.colorFormat}
                        onChange={(v) => {
                          updateConfig("colorFormat", v as "RGB565" | "MONO");
                          setSelectedPreset("");
                        }}
                        style={{ width: "100%" }}
                      >
                        <Select.Option value="RGB565">RGB565 (16-bit)</Select.Option>
                        <Select.Option value="MONO">Monochrome</Select.Option>
                      </Select>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 2: Wake Word */}
            {tab.id === "wakeword" && (
              <div className="space-y-4 mt-4">
                <div>
                  <Text strong size="small" className="block mb-1">
                    {t("select_wake_word", "Chọn từ đánh thức")}
                  </Text>
                  <Text type="tertiary" size="small" className="block mb-3">
                    {config.chip === "esp32c3" || config.chip === "esp32c6"
                      ? t("wake_word_c3_note", "Chip C3/C6 chỉ hỗ trợ WakeNet9s")
                      : t("wake_word_s3_note", "Chip S3/P4 hỗ trợ WakeNet9")}
                  </Text>

                  <Radio.Group
                    value={config.wakeWord}
                    onChange={(e) => handleWakeWordSelect(e.target.value)}
                  >
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {WAKE_WORD_MODELS.map((ww) => {
                        const compatible = isWakeWordCompatible(ww);
                        return (
                          <div
                            key={ww.name}
                            className={cn(
                              "flex items-center justify-between rounded-lg border p-3 cursor-pointer transition-colors",
                              config.wakeWord === ww.name
                                ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                                : "border-gray-200 dark:border-gray-700",
                              !compatible && "opacity-50 cursor-not-allowed"
                            )}
                            onClick={() => compatible && handleWakeWordSelect(ww.name)}
                          >
                            <div>
                              <Text strong size="small">{ww.displayName}</Text>
                              <Text type="tertiary" size="small" className="block">{ww.name}</Text>
                            </div>
                            {config.wakeWord === ww.name && (
                              <Check className="h-4 w-4 text-blue-500" />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </Radio.Group>
                </div>
              </div>
            )}

            {/* Tab 3: Font */}
            {tab.id === "font" && (
              <div className="space-y-4 mt-4">
                <div>
                  <Text strong size="small" className="block mb-3">
                    {t("select_font", "Chọn font chữ")}
                  </Text>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {FONT_PRESETS.map((font) => (
                      <div
                        key={font.name}
                        onClick={() => updateConfig("fontPreset", font.name)}
                        className={cn(
                          "flex items-center justify-between rounded-lg border p-3 cursor-pointer transition-colors",
                          config.fontPreset === font.name
                            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                            : "border-gray-200 dark:border-gray-700 hover:border-blue-300"
                        )}
                      >
                        <div>
                          <Text strong size="small">{font.displayName}</Text>
                          <Text type="tertiary" size="small" className="block">
                            Size: {font.size}px • BPP: {font.bpp}
                          </Text>
                        </div>
                        {config.fontPreset === font.name && (
                          <Check className="h-4 w-4 text-blue-500" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border-t pt-4">
                  <Text strong size="small" className="block mb-3">
                    {t("custom_font", "Upload font tùy chỉnh")}
                  </Text>
                  <div className="flex items-center gap-4">
                    <input
                      type="file"
                      accept=".ttf,.woff,.otf"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          setConfig((prev) => ({ ...prev, customFont: file }));
                        }
                      }}
                      className="flex-1"
                    />
                    <div className="flex gap-2">
                      <Input
                        type="number"
                        placeholder="Size"
                        value={String(config.customFontSize || "")}
                        onChange={(value) =>
                          updateConfig("customFontSize", parseInt(String(value)) || undefined)
                        }
                        style={{ width: 80 }}
                      />
                      <Select
                        value={String(config.customFontBpp || 4)}
                        onChange={(v) => updateConfig("customFontBpp", parseInt(String(v)))}
                        style={{ width: 80 }}
                      >
                        <Select.Option value="1">BPP 1</Select.Option>
                        <Select.Option value="2">BPP 2</Select.Option>
                        <Select.Option value="4">BPP 4</Select.Option>
                      </Select>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Tab 4: Emoji */}
            {tab.id === "emoji" && (
              <div className="space-y-4 mt-4">
                <div>
                  <Text strong size="small" className="block mb-3">
                    {t("select_emoji_pack", "Chọn bộ biểu cảm")}
                  </Text>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {EMOJI_PRESETS.map((emoji) => (
                      <div
                        key={emoji.name}
                        onClick={() => {
                          updateConfig("emojiPreset", emoji.name);
                          updateConfig("emojiSize", emoji.size);
                        }}
                        className={cn(
                          "flex items-center justify-between rounded-lg border p-3 cursor-pointer transition-colors",
                          config.emojiPreset === emoji.name
                            ? "border-blue-500 bg-blue-50 dark:bg-blue-900/20"
                            : "border-gray-200 dark:border-gray-700 hover:border-blue-300"
                        )}
                      >
                        <div className="flex items-center gap-3">
                          <div className="text-2xl">😊</div>
                          <div>
                            <Text strong size="small">{emoji.displayName}</Text>
                            <Text type="tertiary" size="small" className="block">
                              {emoji.size}x{emoji.size} pixels
                            </Text>
                          </div>
                        </div>
                        {config.emojiPreset === emoji.name && (
                          <Check className="h-4 w-4 text-blue-500" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border-t pt-4">
                  <Text strong size="small" className="block mb-2">
                    {t("emoji_preview", "Các biểu cảm sẽ được đóng gói")}
                  </Text>
                  <div className="flex flex-wrap gap-2">
                    {["😶", "🙂", "😆", "😂", "😔", "😠", "😭", "😍", "😳", "😯", "😱", "🤔", "😉", "😎", "😌", "🤤", "😘", "😏", "😴", "😜", "🙄"].map(
                      (emoji, i) => (
                        <span
                          key={i}
                          className="text-2xl p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                          title={`Emotion ${i + 1}`}
                        >
                          {emoji}
                        </span>
                      )
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Tab 5: Background */}
            {tab.id === "background" && (
              <div className="space-y-4 mt-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {/* Light Mode */}
                  <div className="space-y-4">
                    <Text strong size="small">{t("light_mode", "Chế độ sáng")}</Text>

                    <div className="space-y-2">
                      <Text size="small">{t("background_color", "Màu nền")}</Text>
                      <div className="flex gap-2">
                        <input
                          type="color"
                          value={config.lightBackgroundColor}
                          onChange={(e) => updateConfig("lightBackgroundColor", e.target.value)}
                          className="w-12 h-10 p-1 cursor-pointer rounded border"
                        />
                        <Input
                          value={config.lightBackgroundColor}
                          onChange={(value) => updateConfig("lightBackgroundColor", String(value))}
                          placeholder="#ffffff"
                          className="flex-1"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Text size="small">{t("text_color", "Màu chữ")}</Text>
                      <div className="flex gap-2">
                        <input
                          type="color"
                          value={config.lightTextColor}
                          onChange={(e) => updateConfig("lightTextColor", e.target.value)}
                          className="w-12 h-10 p-1 cursor-pointer rounded border"
                        />
                        <Input
                          value={config.lightTextColor}
                          onChange={(value) => updateConfig("lightTextColor", String(value))}
                          placeholder="#000000"
                          className="flex-1"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Text size="small">{t("background_image", "Ảnh nền (tùy chọn)")}</Text>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            setConfig((prev) => ({ ...prev, lightBackgroundImage: file }));
                          }
                        }}
                        className="w-full text-sm"
                      />
                    </div>

                    {/* Preview */}
                    <div
                      className="rounded-lg border p-4 h-32 flex items-center justify-center"
                      style={{
                        backgroundColor: config.lightBackgroundColor,
                        color: config.lightTextColor,
                      }}
                    >
                      <Text strong size="small">Preview Light Mode</Text>
                    </div>
                  </div>

                  {/* Dark Mode */}
                  <div className="space-y-4">
                    <Text strong size="small">{t("dark_mode", "Chế độ tối")}</Text>

                    <div className="space-y-2">
                      <Text size="small">{t("background_color", "Màu nền")}</Text>
                      <div className="flex gap-2">
                        <input
                          type="color"
                          value={config.darkBackgroundColor}
                          onChange={(e) => updateConfig("darkBackgroundColor", e.target.value)}
                          className="w-12 h-10 p-1 cursor-pointer rounded border"
                        />
                        <Input
                          value={config.darkBackgroundColor}
                          onChange={(value) => updateConfig("darkBackgroundColor", String(value))}
                          placeholder="#121212"
                          className="flex-1"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Text size="small">{t("text_color", "Màu chữ")}</Text>
                      <div className="flex gap-2">
                        <input
                          type="color"
                          value={config.darkTextColor}
                          onChange={(e) => updateConfig("darkTextColor", e.target.value)}
                          className="w-12 h-10 p-1 cursor-pointer rounded border"
                        />
                        <Input
                          value={config.darkTextColor}
                          onChange={(value) => updateConfig("darkTextColor", String(value))}
                          placeholder="#ffffff"
                          className="flex-1"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Text size="small">{t("background_image", "Ảnh nền (tùy chọn)")}</Text>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) {
                            setConfig((prev) => ({ ...prev, darkBackgroundImage: file }));
                          }
                        }}
                        className="w-full text-sm"
                      />
                    </div>

                    {/* Preview */}
                    <div
                      className="rounded-lg border p-4 h-32 flex items-center justify-center"
                      style={{
                        backgroundColor: config.darkBackgroundColor,
                        color: config.darkTextColor,
                      }}
                    >
                      <Text strong size="small">Preview Dark Mode</Text>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </TabPane>
        ))}
      </Tabs>

      {/* Summary & Generate Button */}
      <div className="mt-6 pt-4 border-t">
        <div className="flex items-center justify-between">
          <div className="text-sm">
            <Text strong>{t("config_summary", "Tóm tắt cấu hình")}</Text>
            <Text type="tertiary" size="small" className="block mt-1">
              {config.chip.toUpperCase()} • {config.screenWidth}x{config.screenHeight} •{" "}
              {WAKE_WORD_MODELS.find((w) => w.name === config.wakeWord)?.displayName || config.wakeWord}
            </Text>
          </div>
          <div className="flex gap-2">
            <Button onClick={() => onOpenChange(false)}>
              {t("cancel", { ns: "common" })}
            </Button>
            <Button
              theme="solid"
              onClick={handleGenerate}
              disabled={isGenerating}
              loading={isGenerating}
              icon={!isGenerating && <Download className="h-4 w-4" />}
            >
              {isGenerating
                ? t("generating", "Đang tạo...")
                : t("generate_assets", "Tạo assets.bin")}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
