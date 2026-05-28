/**
 * Feature-rich Device Customizer Page
 * Integrates DisplayCustomizerDialog logic into a full page experience
 */
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Button,
  Card,
  Typography,
  Spin,
  Steps,
  Divider,
  Layout,
  Space,
  Banner
} from "@douyinfe/semi-ui";
import { IconDownload, IconSave, IconSetting, IconClock, IconImage } from "@douyinfe/semi-icons";
import { Monitor, Usb, Cpu, Calendar, Server, Share2 } from "lucide-react";

import { useDisplayConfig } from "@/components/display-customizer/hooks/useDisplayConfig";
import { DisplayPreviewCanvas } from "@/components/display-customizer/DisplayPreviewCanvas";
import { SelectFeaturesStep } from "@/components/display-customizer/steps/SelectFeaturesStep";
import { BackgroundStep } from "@/components/display-customizer/steps/BackgroundStep";
import { ClockStep } from "@/components/display-customizer/steps/ClockStep";
import { WeatherStep } from "@/components/display-customizer/steps/WeatherStep";
import { EmojiStep } from "@/components/display-customizer/steps/EmojiStep";
import { packDisplayAssets } from "@/components/display-customizer/utils/assetPacker";
import { FlashDialog } from "@/components/display-customizer/FlashDialog";
import { PageHead } from "@/components";
import { useDeviceDetail } from "@/hooks";
import { useAdminConfig } from "@/hooks/useAdminConfig";
import { useCreateTheme } from "@/queries/theme-queries";
import { BOARD_PRESETS } from "@/components/asset-generator/types";


// Lunar Calendar Component (Inline for now, can extract later)


const { Title, Text } = Typography;
const { Content } = Layout;

export function DeviceCustomizePage() {
  const { deviceId } = useParams<{ deviceId: string }>();

  const { t } = useTranslation(["devices", "common"]);

  // Fetch device info using hook
  const { data: device, isLoading: loading } = useDeviceDetail(deviceId || "");

  // Fetch system config for MQTT defaults
  const { data: systemConfig } = useAdminConfig(true);

  // Wizard state
  const [currentStep, setCurrentStep] = useState(0);
  const [showFlashDialog, setShowFlashDialog] = useState(false);
  const [binaryData, setBinaryData] = useState<Uint8Array | null>(null);

  // Display config hook
  const {
    config,
    updateBackground,
    updateClock,
    updateWeather,
    updateEmoji,
    updateMqtt,
    toggleFeature,
    setPreset
  } = useDisplayConfig();

  // Theme creation
  const createThemeMutation = useCreateTheme();

  // Update board when device is loaded
  useEffect(() => {
    if (device?.board) {
      setPreset(device.board);
    }
  }, [device, setPreset]);

  // Pre-fill MQTT config from System
  useEffect(() => {
    if (systemConfig?.mqtt && config.enableMqtt) {
      // Parse URL: mqtt://host:port
      const url = systemConfig.mqtt.url || "";
      const match = url.match(/mqtt:\/\/(.+):(\d+)/);
      let broker = "minhthuc.local";
      let port = 1883;

      if (match) {
        broker = match[1];
        port = parseInt(match[2], 10);
      }

      updateMqtt({
        broker,
        port,
        username: systemConfig.mqtt.username || "",
        password: systemConfig.mqtt.password || "",
        // keep topicPrefix default for now
      });
    }
  }, [systemConfig, config.enableMqtt]); // Only update when enabled or config loaded

  // Steps configuration
  const steps = [
    { title: t("features", "Tính năng"), icon: <IconSetting />, description: "Chọn thành phần hiển thị" },
    { title: t("background", "Giao diện"), icon: <IconImage />, description: "Hình nền & Màu sắc" },
    { title: t("widgets", "Widget"), icon: <IconClock />, description: "Đồng hồ, Emoji..." },
    { title: t("preview", "Hoàn tất"), icon: <IconSave />, description: "Xem trước & Nạp" },
  ];

  // Logic to inject Lunar Calendar into Widget Step or create new step
  // Here we integrate Lunar Calendar into Widgets step (Step 2 - index 2)

  const handleDownload = async () => {
    try {
      // Safe defaults if device not loaded

      const name = device?.device_name || "device";

      const binary = await packDisplayAssets(config);
      const blob = new Blob([binary as any], { type: "application/octet-stream" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `display_config_${name.replace(/\s+/g, "_")}.bin`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download error:", error);
      alert("Error creating file: " + error);
    }
  };

  // Render MQTT Config Section
  const renderMqttConfig = () => (
    <div className="space-y-6 mt-6 pt-6 border-t border-gray-200">
      <div className="flex items-center gap-2">
        <Server className="h-5 w-5 text-green-600" />
        <h3 className="text-lg font-semibold m-0">
          {t("mqtt_config", "Cấu hình MQTT Realtime")}
        </h3>
      </div>

      <div className="bg-green-50 p-4 rounded-lg border border-green-200">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-gray-500">Broker Host</label>
            <input
              type="text"
              className="w-full px-3 py-2 border rounded bg-white"
              value={config.mqtt.broker}
              onChange={e => updateMqtt({ broker: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-gray-500">Port</label>
            <input
              type="number"
              className="w-full px-3 py-2 border rounded bg-white"
              value={config.mqtt.port}
              onChange={e => updateMqtt({ port: parseInt(e.target.value) })}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-gray-500">Username</label>
            <input
              type="text"
              className="w-full px-3 py-2 border rounded bg-white"
              value={config.mqtt.username}
              onChange={e => updateMqtt({ username: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase text-gray-500">Password</label>
            <input
              type="password"
              className="w-full px-3 py-2 border rounded bg-white"
              value={config.mqtt.password}
              onChange={e => updateMqtt({ password: e.target.value })}
            />
          </div>
          <div className="space-y-2 md:col-span-2">
            <label className="text-xs font-semibold uppercase text-gray-500">Topic Prefix</label>
            <input
              type="text"
              className="w-full px-3 py-2 border rounded bg-white font-mono text-sm"
              value={config.mqtt.topicPrefix}
              onChange={e => updateMqtt({ topicPrefix: e.target.value })}
            />
          </div>
        </div>
      </div>
    </div>
  );

  // Render Lunar Calendar Section
  const renderLunarCalendarConfig = () => (
    <div className="space-y-6 mt-6 pt-6 border-t border-gray-200">
      <div className="flex items-center gap-2">
        <Calendar className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold m-0">
          {t("lunar_calendar", "Âm lịch (Lunar Calendar)")}
        </h3>
      </div>

      <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="font-medium text-gray-900">{t("enable_lunar", "Hiển thị Âm lịch")}</p>
            <p className="text-sm text-gray-500">
              {t("enable_lunar_desc", "Hiển thị ngày âm lịch Việt Nam bên cạnh dương lịch")}
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={config.enableLunarCalendar || false}
              onChange={() => toggleFeature("enableLunarCalendar")}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>

        {config.enableLunarCalendar && (
          <div className="space-y-4 animate-in fade-in slide-in-from-top-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Format Selection */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Định dạng hiển thị</label>
                <div className="space-y-2">
                  {[
                    { val: "short", label: "Ngắn gọn", desc: "15/1 ÂL" },
                    { val: "full", label: "Đầy đủ", desc: "15 tháng Giêng" },
                  ].map(opt => (
                    <div key={opt.val} className="flex items-center space-x-2">
                      <input
                        type="radio"
                        id={`lunar-${opt.val}`}
                        name="lunarFormat"
                        checked={(config.weather.lunarFormat || 'short') === opt.val}
                        // Using weather config a placeholder
                        onChange={() => updateWeather({ lunarFormat: opt.val as any })}
                        className="text-blue-600"
                      />
                      <label htmlFor={`lunar-${opt.val}`} className="text-sm">
                        <span className="font-medium">{opt.label}</span> <span className="text-gray-400">- {opt.desc}</span>
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Features
        return (
          <SelectFeaturesStep
            config={config}
            onToggle={toggleFeature}
          />
        );
      case 1: // Background
        return (
          <BackgroundStep
            config={config}
            onUpdate={updateBackground}
          />
        );
      case 2: // Widgets (Clock, Weather, Lunar)
        return (
          <div className="space-y-8">
            {config.enableClock ? (
              <ClockStep config={config} onUpdate={updateClock} />
            ) : (
              <Banner type="info" description="Bạn chưa bật Đồng hồ. Quay lại bước 1 để bật nếu muốn." />
            )}

            <Divider />

            {config.enableWeather ? (
              <WeatherStep config={config} onUpdate={updateWeather} />
            ) : (
              <Banner type="info" description="Bạn chưa bật Thời tiết. Quay lại bước 1 để bật nếu muốn." />
            )}

            <Divider />

            {config.enableEmoji ? (
              <EmojiStep config={config} onUpdate={updateEmoji} />
            ) : (
              <Banner type="info" description="Bạn chưa bật Biểu cảm AI. Quay lại bước 1 để bật nếu muốn." />
            )}

            {/* Lunar Calendar integrated here */}
            {renderLunarCalendarConfig()}

            {/* MQTT Config integrated here */}
            {config.enableMqtt && renderMqttConfig()}
          </div>
        );
      case 3: // Preview & Finalize
        return (
          <div className="text-center py-8 space-y-6">
            <div className="flex justify-center">
              <div className="p-4 border rounded-full bg-green-50 inline-flex items-center justify-center">
                <Cpu className="w-12 h-12 text-green-600" />
              </div>
            </div>

            <div>
              <Title heading={3}>Sẵn sàng nạp vào thiết bị!</Title>
              <Text type="secondary" className="text-lg">
                Bạn đã hoàn tất thiết kế giao diện cho {device?.device_name}.
                Kết nối thiết bị qua USB hoặc tải file cấu hình về.
              </Text>
            </div>

            <div className="flex flex-col items-center gap-4 mt-6">
              <div className="text-center mb-4">
                <Text type="secondary" className="text-sm">
                  <strong>Chọn 1 trong 3 thao tác:</strong>
                </Text>
              </div>

              <div className="flex flex-wrap justify-center gap-4">
                {/* Option 1: Download .packl for SD Card */}
                <div className="flex flex-col items-center gap-2 p-4 border rounded-lg hover:border-blue-500 transition-colors">
                  <Button
                    size="large"
                    icon={<IconDownload />}
                    onClick={async () => {
                      try {
                        const { downloadAsPackl } = await import('@/components/display-customizer/utils/assetPacker');
                        await downloadAsPackl(config, device?.device_name || 'theme');
                      } catch (error) {
                        console.error("Download error:", error);
                        alert("Error creating file: " + error);
                      }
                    }}
                    style={{ height: '50px', padding: '0 30px' }}
                  >
                    Tải file .packl
                  </Button>
                  <Text type="secondary" className="text-xs text-center max-w-40">
                    Chép vào SD card:<br />
                    <code className="bg-gray-100 px-1 rounded">/presets/theme/</code>
                  </Text>
                </div>

                {/* Option 2: Download .bin for manual flashing */}
                <div className="flex flex-col items-center gap-2 p-4 border rounded-lg hover:border-green-500 transition-colors">
                  <Button
                    size="large"
                    icon={<IconDownload />}
                    onClick={handleDownload}
                    style={{ height: '50px', padding: '0 30px' }}
                  >
                    Tải file .bin
                  </Button>
                  <Text type="secondary" className="text-xs text-center max-w-40">
                    Nạp thủ công bằng<br />esptool/ESP Flash Tool
                  </Text>
                </div>

                {/* Option 3: Flash via WebSerial */}
                <div className="flex flex-col items-center gap-2 p-4 border rounded-lg hover:border-purple-500 transition-colors">
                  <Button
                    size="large"
                    theme="solid"
                    type="primary"
                    icon={<Usb className="w-5 h-5" />}
                    onClick={async () => {
                      try {
                        const bin = await packDisplayAssets(config);
                        setBinaryData(bin);
                        setShowFlashDialog(true);
                      } catch (e) {
                        console.error(e);
                        alert("Error packing config");
                      }
                    }}
                    style={{ height: '50px', padding: '0 30px' }}
                  >
                    Nạp qua USB
                  </Button>
                  <Text type="secondary" className="text-xs text-center max-w-40">
                    Nạp trực tiếp từ trình duyệt<br />qua cáp USB (WebSerial)
                  </Text>
                </div>

                {/* Option 4: Publish to Gallery */}
                <div className="flex flex-col items-center gap-2 p-4 border rounded-lg hover:border-pink-500 transition-colors">
                  <Button
                    size="large"
                    icon={<Share2 className="w-5 h-5" />}
                    loading={createThemeMutation.isPending}
                    onClick={async () => {
                      const name = prompt('Nhập tên theme:', `${device?.device_name || 'My'} Theme`);
                      if (!name) return;
                      const desc = prompt('Mô tả ngắn:', 'Custom theme by user');
                      try {
                        await createThemeMutation.mutateAsync({
                          name,
                          description: desc || '',
                          screen_type: `${config.screenWidth}x${config.screenHeight}`,
                          category: 'custom',
                          theme_data: {
                            colors: {
                              primary: config.clock?.color || '#ffffff',
                              secondary: '#9ca3af',
                              background: config.background?.color || '#000000',
                              text: config.clock?.color || '#ffffff'
                            },
                            widgets: {
                              clock: { enabled: config.enableClock },
                              weather: { enabled: config.enableWeather },
                            }
                          }
                        });
                        alert('✅ Theme đã được publish thành công!');
                      } catch (err) {
                        console.error(err);
                        alert('Lỗi khi publish theme');
                      }
                    }}
                    style={{ height: '50px', padding: '0 30px' }}
                  >
                    Public ra Kho Theme
                  </Button>
                  <Text type="secondary" className="text-xs text-center max-w-40">
                    Chia sẻ theme<br />lên Kho Theme
                  </Text>
                </div>
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  if (loading) {
    return <div className="flex h-screen items-center justify-center"><Spin size="large" /></div>;
  }

  return (
    <Layout className="min-h-screen bg-gray-50">
      <PageHead
        title={t("customize_ui", "Tạo Theme")}
        description={`${device?.device_name || "Device"} • ${config.screenWidth}x${config.screenHeight}`}
      />

      <Content className="container mx-auto px-4 py-6 max-w-7xl">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full">
          {/* Left Panel: Configuration Steps */}
          <div className="lg:col-span-7 xl:col-span-8 flex flex-col gap-6">
            <Card className="flex-1 shadow-sm border-gray-100" bodyStyle={{ padding: '24px' }}>
              <Steps current={currentStep} onChange={setCurrentStep} className="mb-8 pointer-events-auto">
                {steps.map((s, idx) => (
                  <Steps.Step key={idx} title={s.title} description={s.description} icon={s.icon} />
                ))}
              </Steps>

              <div className="min-h-[400px]">
                {renderStepContent()}
              </div>

              <Divider className="my-6" />

              <div className="flex justify-between items-center">
                <Button
                  disabled={currentStep === 0}
                  onClick={() => setCurrentStep(c => c - 1)}
                  theme="light"
                >
                  Quay lại
                </Button>
                <Space>
                  {currentStep === steps.length - 1 ? (
                    <></> // Actions are in the step content
                  ) : (
                    <Button
                      theme="solid"
                      type="primary"
                      onClick={() => setCurrentStep(c => c + 1)}
                    >
                      Tiếp theo
                    </Button>
                  )}
                </Space>
              </div>
            </Card>
          </div>

          {/* Right Panel: Live Preview */}
          <div className="lg:col-span-5 xl:col-span-4">
            <div className="sticky top-6">
              <Card
                title={<span className="flex items-center gap-2"><Monitor size={18} /> {t("preview", "Xem trước")}</span>}
                className="shadow-md border-gray-200 overflow-hidden"
                bodyStyle={{ padding: 0, backgroundColor: '#f9fafb' }}
                headerStyle={{ borderBottom: '1px solid #f0f0f0' }}
              >
                <div className="p-6 flex items-center justify-center bg-[url('https://sv.isleofdog.com/grid.svg')] min-h-[400px]">
                  <div className="relative shadow-2xl rounded-lg overflow-hidden border-4 border-gray-800 bg-black">
                    <DisplayPreviewCanvas
                      config={config}
                      scale={Math.min(1, 350 / config.screenWidth)}
                    />
                    {/* Reflection effect */}
                    <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent pointer-events-none"></div>
                  </div>
                </div>
                <div className="bg-white p-4 border-t text-center text-gray-500 text-xs">
                  {config.screenWidth} x {config.screenHeight} pixels • {config.boardPreset || "Generic"}
                </div>
              </Card>

              {/* Quick Tips */}
              <Card className="mt-4 shadow-sm" bodyStyle={{ padding: '16px' }}>
                <Title heading={6} className="mb-2 text-gray-700">Mẹo thiết kế</Title>
                <ul className="text-sm text-gray-600 list-disc pl-5 space-y-1">
                  <li>Sử dụng ảnh nền tối để tiết kiệm pin</li>
                  <li>Font chữ lớn giúp dễ đọc hơn</li>
                  <li>Đồng bộ thời gian sẽ tự động khi kết nối WiFi</li>
                </ul>
              </Card>
            </div>
          </div>
        </div>
      </Content>

      {/* Flash Dialog Integration */}
      <FlashDialog
        open={showFlashDialog}
        onOpenChange={setShowFlashDialog}
        binaryData={binaryData}
        deviceName={device?.device_name || "Device"}
        flashAddress={BOARD_PRESETS.find(p => p.name === config.boardPreset)?.dataPartitionAddress || 0x310000}
      />
    </Layout>
  );
}

export default DeviceCustomizePage;
