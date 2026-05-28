
import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
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
    Loader2,
    Package,
    AlertCircle
} from "lucide-react";
import { buildAssetsBin } from "@/components/asset-generator/AssetsBuilder";

import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { PageHead } from "@/components/PageHead";

import {
    type AssetConfig,
    type ChipModel,
    BOARD_PRESETS,
    WAKE_WORD_MODELS,
    FONT_PRESETS,
    DEFAULT_ASSET_CONFIG,
} from "@/components/asset-generator/types";
import { EmojiPackEditor, type CustomEmojis } from "@/components/asset-generator/EmojiPackEditor";

export function AssetGeneratorPage() {
    const { t } = useTranslation(["devices", "common"]);
    const [searchParams] = useSearchParams();

    const [activeTab, setActiveTab] = useState("chip");
    const [config, setConfig] = useState<AssetConfig>(DEFAULT_ASSET_CONFIG);
    const [isGenerating, setIsGenerating] = useState(false);
    const [buildProgress, setBuildProgress] = useState(0);
    const [buildMessage, setBuildMessage] = useState("");
    const [buildError, setBuildError] = useState<string | null>(null);
    const [selectedPreset, setSelectedPreset] = useState<string>("");
    const [customEmojis, setCustomEmojis] = useState<CustomEmojis>({});

    // Init from query params
    useEffect(() => {
        const boardParam = searchParams.get("deviceBoard");
        if (boardParam) {
            // Try to match preset
            const preset = BOARD_PRESETS.find(p => p.name.toLowerCase().includes(boardParam.toLowerCase()) || boardParam.toLowerCase().includes(p.name.toLowerCase()));
            if (preset) {
                handlePresetSelect(preset.name);
            }
        }
    }, [searchParams]);

    const deviceName = searchParams.get("deviceName");

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

    // Check if wake word is compatible with selected chip
    const isWakeWordCompatible = (wakeWord: typeof WAKE_WORD_MODELS[0]) => {
        const isC3orC6 = config.chip === "esp32c3" || config.chip === "esp32c6";
        if (isC3orC6) {
            return !!wakeWord.wn9s;
        }
        return !!wakeWord.wn9;
    };

    // Handle generate assets — builds actual assets.bin binary in browser
    const handleGenerate = async () => {
        setIsGenerating(true);
        setBuildProgress(0);
        setBuildMessage("");
        setBuildError(null);
        try {
            const result = await buildAssetsBin(
                config,
                customEmojis,
                (progress, message) => {
                    setBuildProgress(Math.round(progress));
                    setBuildMessage(message);
                }
            );

            // Download the generated .bin file
            const url = URL.createObjectURL(result.blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = result.filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            const sizeKB = (result.stats.totalSize / 1024).toFixed(1);
            setBuildMessage(
                `✅ ${result.filename} (${sizeKB} KB, ${result.stats.totalFiles} files)`
            );
        } catch (error) {
            console.error("Error generating assets.bin:", error);
            setBuildError(
                error instanceof Error ? error.message : "Unknown error"
            );
        } finally {
            setIsGenerating(false);
        }
    };

    const tabs = [
        { id: "chip", label: t("chip_screen", "Chip & Màn hình"), icon: Cpu },
        { id: "wakeword", label: t("wake_word", "Từ đánh thức"), icon: Mic },
        { id: "font", label: t("font", "Font chữ"), icon: Type },
        { id: "emoji", label: t("emoji", "Biểu cảm"), icon: Smile },
        { id: "background", label: t("background", "Nền"), icon: Image },
    ];

    return (
        <div className="container mx-auto space-y-6 p-6 pb-20">
            <PageHead title={t("asset_generator", "Tạo Asset (Font/Emoji)")} />

            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-3xl font-bold flex items-center gap-2">
                        <Package className="h-8 w-8" />
                        {t("asset_generator", "Tạo Asset (Font/Emoji)")}
                    </h1>
                    <p className="text-muted-foreground">
                        {deviceName
                            ? t("customize_device_desc", "Tạo file assets.bin để cá nhân hóa thiết bị {{name}}", { name: deviceName })
                            : t("customize_device_desc_generic", "Tạo file assets.bin để cá nhân hóa thiết bị của bạn")}
                    </p>
                </div>
            </div>

            <Card>
                <CardContent className="pt-6">
                    <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-0">
                        <TabsList className="grid w-full grid-cols-5 h-auto">
                            {tabs.map((tab) => (
                                <TabsTrigger
                                    key={tab.id}
                                    value={tab.id}
                                    className="flex flex-col sm:flex-row items-center gap-1.5 p-3 text-xs sm:text-sm h-full"
                                >
                                    <tab.icon className="h-5 w-5 mb-1 sm:mb-0" />
                                    <span>{tab.label}</span>
                                </TabsTrigger>
                            ))}
                        </TabsList>

                        {/* Tab 1: Chip & Screen */}
                        <TabsContent value="chip" className="space-y-6 mt-6">
                            <div className="space-y-4">
                                <h3 className="text-sm font-semibold flex items-center gap-2">
                                    <Cpu className="h-4 w-4" />
                                    {t("select_board_preset", "Chọn board có sẵn")}
                                </h3>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {BOARD_PRESETS.map((preset) => (
                                        <button
                                            key={preset.name}
                                            onClick={() => handlePresetSelect(preset.name)}
                                            className={cn(
                                                "flex items-center justify-between p-4 rounded-xl border text-left transition-all hover:shadow-md",
                                                selectedPreset === preset.name
                                                    ? "border-primary bg-primary/5 ring-1 ring-primary"
                                                    : "border-border hover:border-primary/50"
                                            )}
                                        >
                                            <div className="space-y-1">
                                                <p className="font-semibold">{preset.name}</p>
                                                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                                    <span className="bg-muted px-1.5 py-0.5 rounded">{preset.chip.toUpperCase()}</span>
                                                    <span>{preset.width}x{preset.height}</span>
                                                    <span>{preset.colorFormat}</span>
                                                </div>
                                            </div>
                                            {selectedPreset === preset.name && (
                                                <div className="bg-primary text-primary-foreground rounded-full p-1">
                                                    <Check className="h-3 w-3" />
                                                </div>
                                            )}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="rounded-xl border bg-muted/30 p-4 space-y-4">
                                <h3 className="text-sm font-semibold flex items-center gap-2">
                                    <Settings2 className="h-4 w-4" />
                                    {t("custom_config", "Hoặc tùy chỉnh thông số")}
                                </h3>
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                                    <div className="space-y-2">
                                        <Label>{t("chip_model", "Loại chip")}</Label>
                                        <Select
                                            value={config.chip}
                                            onValueChange={(v) => {
                                                updateConfig("chip", v as ChipModel);
                                                setSelectedPreset("");
                                            }}
                                        >
                                            <SelectTrigger className="bg-background">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="esp32s3">ESP32-S3</SelectItem>
                                                <SelectItem value="esp32c3">ESP32-C3</SelectItem>
                                                <SelectItem value="esp32c6">ESP32-C6</SelectItem>
                                                <SelectItem value="esp32p4">ESP32-P4</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>

                                    <div className="space-y-2">
                                        <Label>{t("screen_width", "Chiều rộng (px)")}</Label>
                                        <Input
                                            type="number"
                                            className="bg-background"
                                            value={config.screenWidth}
                                            onChange={(e) => {
                                                updateConfig("screenWidth", parseInt(e.target.value) || 320);
                                                setSelectedPreset("");
                                            }}
                                            min={120}
                                            max={800}
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label>{t("screen_height", "Chiều cao (px)")}</Label>
                                        <Input
                                            type="number"
                                            className="bg-background"
                                            value={config.screenHeight}
                                            onChange={(e) => {
                                                updateConfig("screenHeight", parseInt(e.target.value) || 240);
                                                setSelectedPreset("");
                                            }}
                                            min={120}
                                            max={600}
                                        />
                                    </div>

                                    <div className="space-y-2">
                                        <Label>{t("color_format", "Định dạng màu")}</Label>
                                        <Select
                                            value={config.colorFormat}
                                            onValueChange={(v) => {
                                                updateConfig("colorFormat", v as "RGB565" | "MONO");
                                                setSelectedPreset("");
                                            }}
                                        >
                                            <SelectTrigger className="bg-background">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="RGB565">RGB565 (16-bit)</SelectItem>
                                                <SelectItem value="MONO">Monochrome (1-bit)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                            </div>
                        </TabsContent>

                        {/* Tab 2: Wake Word */}
                        <TabsContent value="wakeword" className="space-y-6 mt-6">
                            <div>
                                <h3 className="text-sm font-semibold mb-2">
                                    {t("select_wake_word", "Chọn từ đánh thức")}
                                </h3>
                                <p className="text-sm text-muted-foreground mb-4">
                                    {config.chip === "esp32c3" || config.chip === "esp32c6"
                                        ? "Lưu ý: Chip C3/C6 chỉ hỗ trợ mô hình WakeNet9s (nhẹ hơn)."
                                        : "Chip S3/P4 mạnh mẽ hỗ trợ mô hình WakeNet9 đầy đủ."}
                                </p>

                                <RadioGroup
                                    value={config.wakeWord}
                                    onValueChange={handleWakeWordSelect}
                                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
                                >
                                    {WAKE_WORD_MODELS.map((ww) => {
                                        const compatible = isWakeWordCompatible(ww);
                                        return (
                                            <div key={ww.name}>
                                                <RadioGroupItem
                                                    value={ww.name}
                                                    id={`ww-${ww.name}`}
                                                    disabled={!compatible}
                                                    className="peer sr-only"
                                                />
                                                <Label
                                                    htmlFor={`ww-${ww.name}`}
                                                    className={cn(
                                                        "flex items-center justify-between rounded-xl border p-4 cursor-pointer transition-all hover:bg-muted/50",
                                                        "peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5 peer-data-[state=checked]:ring-1 peer-data-[state=checked]:ring-primary",
                                                        !compatible && "opacity-50 cursor-not-allowed bg-muted/20"
                                                    )}
                                                >
                                                    <div>
                                                        <p className="font-medium">{ww.displayName}</p>
                                                        <p className="text-xs text-muted-foreground font-mono mt-1">{ww.name}</p>
                                                    </div>
                                                    {config.wakeWord === ww.name && (
                                                        <div className="bg-primary text-primary-foreground rounded-full p-1">
                                                            <Check className="h-3 w-3" />
                                                        </div>
                                                    )}
                                                </Label>
                                            </div>
                                        );
                                    })}
                                </RadioGroup>
                            </div>
                        </TabsContent>

                        {/* Tab 3: Font */}
                        <TabsContent value="font" className="space-y-6 mt-6">
                            {/* ... Similar structure for Fonts - keeping it brief for file write ... */}
                            <div className="space-y-4">
                                <h3 className="text-sm font-semibold">
                                    {t("select_font", "Chọn font chữ có sẵn")}
                                </h3>
                                <RadioGroup
                                    value={config.fontPreset}
                                    onValueChange={(v) => updateConfig("fontPreset", v)}
                                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
                                >
                                    {FONT_PRESETS.map((font) => (
                                        <div key={font.name}>
                                            <RadioGroupItem value={font.name} id={`font-${font.name}`} className="peer sr-only" />
                                            <Label
                                                htmlFor={`font-${font.name}`}
                                                className={cn(
                                                    "flex items-center justify-between rounded-xl border p-4 cursor-pointer transition-all hover:bg-muted/50",
                                                    "peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5"
                                                )}
                                            >
                                                <div>
                                                    <p className="font-medium">{font.displayName}</p>
                                                    <div className="flex gap-2 text-xs text-muted-foreground mt-1">
                                                        <span className="bg-muted px-1 rounded">Size: {font.size}px</span>
                                                        <span className="bg-muted px-1 rounded">BPP: {font.bpp}</span>
                                                    </div>
                                                </div>
                                                {config.fontPreset === font.name && <Check className="h-4 w-4 text-primary" />}
                                            </Label>
                                        </div>
                                    ))}
                                </RadioGroup>
                            </div>

                            <div className="rounded-xl border bg-muted/30 p-4 space-y-4">
                                <h3 className="text-sm font-semibold">{t("custom_font", "Upload font tùy chỉnh (.ttf/.woff)")}</h3>
                                <div className="flex flex-col sm:flex-row gap-4 items-end">
                                    <div className="flex-1 w-full">
                                        <Label className="mb-2 block">File Font</Label>
                                        <Input
                                            type="file"
                                            accept=".ttf,.woff,.otf"
                                            onChange={(e) => {
                                                const file = e.target.files?.[0];
                                                if (file) setConfig((prev) => ({ ...prev, customFont: file }));
                                            }}
                                            className="bg-background"
                                        />
                                    </div>
                                    <div className="w-full sm:w-24">
                                        <Label className="mb-2 block">Size (px)</Label>
                                        <Input
                                            type="number"
                                            placeholder="24"
                                            value={config.customFontSize || ""}
                                            onChange={(e) => updateConfig("customFontSize", parseInt(e.target.value) || undefined)}
                                            className="bg-background"
                                        />
                                    </div>
                                    <div className="w-full sm:w-32">
                                        <Label className="mb-2 block">Bit Per Pixel</Label>
                                        <Select
                                            value={String(config.customFontBpp || 4)}
                                            onValueChange={(v) => updateConfig("customFontBpp", parseInt(v))}
                                        >
                                            <SelectTrigger className="bg-background">
                                                <SelectValue placeholder="BPP" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="1">1 bit (Mono)</SelectItem>
                                                <SelectItem value="2">2 bit (Gray)</SelectItem>
                                                <SelectItem value="4">4 bit (High)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </div>
                            </div>
                        </TabsContent>

                        {/* Tab 4: Emoji */}
                        <TabsContent value="emoji" className="space-y-6 mt-6">
                            <EmojiPackEditor
                                selectedPreset={config.emojiPreset}
                                onPresetChange={(preset) => updateConfig("emojiPreset", preset)}
                                customEmojis={customEmojis}
                                onCustomEmojisChange={setCustomEmojis}
                                emojiSize={config.emojiSize}
                                onEmojiSizeChange={(size) => updateConfig("emojiSize", size)}
                                screenWidth={config.screenWidth}
                                screenHeight={config.screenHeight}
                            />
                        </TabsContent>

                        {/* Tab 5: Background */}
                        <TabsContent value="background" className="space-y-6 mt-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                {/* Light Mode */}
                                <Card className="border-2 border-dashed">
                                    <CardHeader>
                                        <CardTitle className="text-base text-center">{t("light_mode", "Chế độ Sáng")}</CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div className="flex items-center gap-3">
                                            <Label className="w-20">Màu nền</Label>
                                            <Input type="color" value={config.lightBackgroundColor} onChange={(e) => updateConfig("lightBackgroundColor", e.target.value)} className="w-12 h-10 p-1" />
                                            <Input value={config.lightBackgroundColor} onChange={(e) => updateConfig("lightBackgroundColor", e.target.value)} className="flex-1" />
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <Label className="w-20">Màu chữ</Label>
                                            <Input type="color" value={config.lightTextColor} onChange={(e) => updateConfig("lightTextColor", e.target.value)} className="w-12 h-10 p-1" />
                                            <Input value={config.lightTextColor} onChange={(e) => updateConfig("lightTextColor", e.target.value)} className="flex-1" />
                                        </div>
                                        <div>
                                            <Label className="mb-1 block">Ảnh nền</Label>
                                            <Input type="file" accept="image/*" onChange={(e) => {
                                                const file = e.target.files?.[0];
                                                if (file) setConfig(p => ({ ...p, lightBackgroundImage: file }));
                                            }} />
                                        </div>

                                        {/* Preview Box */}
                                        <div className="h-32 rounded-lg flex items-center justify-center font-bold text-lg shadow-sm"
                                            style={{ backgroundColor: config.lightBackgroundColor, color: config.lightTextColor }}>
                                            Preview Light
                                        </div>
                                    </CardContent>
                                </Card>

                                {/* Dark Mode */}
                                <Card className="border-2 border-dashed bg-slate-950">
                                    <CardHeader>
                                        <CardTitle className="text-base text-center text-white">{t("dark_mode", "Chế độ Tối")}</CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div className="flex items-center gap-3">
                                            <Label className="w-20 text-slate-300">Màu nền</Label>
                                            <Input type="color" value={config.darkBackgroundColor} onChange={(e) => updateConfig("darkBackgroundColor", e.target.value)} className="w-12 h-10 p-1" />
                                            <Input value={config.darkBackgroundColor} onChange={(e) => updateConfig("darkBackgroundColor", e.target.value)} className="flex-1" />
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <Label className="w-20 text-slate-300">Màu chữ</Label>
                                            <Input type="color" value={config.darkTextColor} onChange={(e) => updateConfig("darkTextColor", e.target.value)} className="w-12 h-10 p-1" />
                                            <Input value={config.darkTextColor} onChange={(e) => updateConfig("darkTextColor", e.target.value)} className="flex-1" />
                                        </div>
                                        <div>
                                            <Label className="mb-1 block text-slate-300">Ảnh nền</Label>
                                            <Input type="file" accept="image/*" onChange={(e) => {
                                                const file = e.target.files?.[0];
                                                if (file) setConfig(p => ({ ...p, darkBackgroundImage: file }));
                                            }} />
                                        </div>

                                        {/* Preview Box */}
                                        <div className="h-32 rounded-lg flex items-center justify-center font-bold text-lg shadow-sm"
                                            style={{ backgroundColor: config.darkBackgroundColor, color: config.darkTextColor }}>
                                            Preview Dark
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>
                        </TabsContent>
                    </Tabs>
                </CardContent>

                <CardFooter className="flex flex-col gap-3 border-t p-6 bg-muted/10">
                    <div className="flex w-full justify-between items-center">
                        <div className="text-sm text-muted-foreground hidden sm:block">
                            <span className="font-semibold text-foreground">Summary:</span> {config.chip.toUpperCase()} • {config.screenWidth}x{config.screenHeight} • {config.wakeWord}
                        </div>
                        <Button onClick={handleGenerate} disabled={isGenerating} size="lg" className="w-full sm:w-auto">
                            {isGenerating ? (
                                <>
                                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                                    Đang tạo assets.bin... ({buildProgress}%)
                                </>
                            ) : (
                                <>
                                    <Download className="mr-2 h-5 w-5" />
                                    Tạo và tải về assets.bin
                                </>
                            )}
                        </Button>
                    </div>

                    {/* Build progress bar */}
                    {isGenerating && (
                        <div className="w-full space-y-1">
                            <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
                                <div
                                    className="bg-primary h-2 rounded-full transition-all duration-300"
                                    style={{ width: `${buildProgress}%` }}
                                />
                            </div>
                            <p className="text-xs text-muted-foreground truncate">{buildMessage}</p>
                        </div>
                    )}

                    {/* Build success message */}
                    {!isGenerating && buildMessage && !buildError && (
                        <div className="w-full text-sm text-green-600 dark:text-green-400 flex items-center gap-2">
                            <Check className="h-4 w-4" />
                            {buildMessage}
                        </div>
                    )}

                    {/* Build error message */}
                    {buildError && (
                        <div className="w-full text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
                            <AlertCircle className="h-4 w-4" />
                            {buildError}
                        </div>
                    )}
                </CardFooter>
            </Card>
        </div>
    );
}

export default AssetGeneratorPage;
