/**
 * HomeAssistant Quick Setup Component
 * 
 * Provides a streamlined UI for configuring HomeAssistant MCP integration
 * without requiring users to manually write JSON configuration.
 */

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import {
    Card,
    Form,
    Button,
    Input,
    Banner,
    Toast,
    Spin,
    Typography,
    Collapsible
} from "@douyinfe/semi-ui";
import {
    IconHome,
    IconTick,
    IconClose,
    IconLink,
    IconKey,
    IconCopy,
    IconInfoCircle
} from "@douyinfe/semi-icons";

const { Text, Title } = Typography;

interface HomeAssistantConfig {
    url: string;
    accessToken: string;
}

interface ConnectionTestResult {
    success: boolean;
    message: string;
    haVersion?: string;
    locationName?: string;
}

interface HomeAssistantQuickSetupProps {
    onConfigGenerated?: (config: Record<string, unknown>) => void;
}

export const HomeAssistantQuickSetup = ({ onConfigGenerated }: HomeAssistantQuickSetupProps) => {
    const { t } = useTranslation(["mcp-configs", "common"]);

    const [config, setConfig] = useState<HomeAssistantConfig>({
        url: "",
        accessToken: ""
    });
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);
    const [showAdvanced, setShowAdvanced] = useState(false);

    /**
     * Test connection to HomeAssistant
     */
    const testConnection = useCallback(async () => {
        if (!config.url || !config.accessToken) {
            Toast.warning(t("ha.fill_all_fields", "Please fill in all fields"));
            return;
        }

        setTesting(true);
        setTestResult(null);

        try {
            // Normalize URL
            let haUrl = config.url.trim();
            if (!haUrl.startsWith("http://") && !haUrl.startsWith("https://")) {
                haUrl = `http://${haUrl}`;
            }
            haUrl = haUrl.replace(/\/$/, ""); // Remove trailing slash

            // Test HA API endpoint
            const response = await fetch(`${haUrl}/api/config`, {
                headers: {
                    "Authorization": `Bearer ${config.accessToken}`,
                    "Content-Type": "application/json"
                }
            });

            if (response.ok) {
                const data = await response.json();
                setTestResult({
                    success: true,
                    message: t("ha.connection_success", "Connection successful!"),
                    haVersion: data.version,
                    locationName: data.location_name
                });
                Toast.success(t("ha.connection_success", "Connection successful!"));
            } else if (response.status === 401) {
                setTestResult({
                    success: false,
                    message: t("ha.invalid_token", "Invalid access token. Please check your Long-Lived Access Token.")
                });
            } else {
                setTestResult({
                    success: false,
                    message: t("ha.connection_failed", `Connection failed: HTTP ${response.status}`)
                });
            }
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Unknown error";

            // Check for CORS error (common when testing from browser)
            if (errorMessage.includes("CORS") || errorMessage.includes("fetch")) {
                setTestResult({
                    success: false,
                    message: t("ha.cors_error", "Cannot test directly from browser (CORS). The configuration may still work - try generating and using it.")
                });
            } else {
                setTestResult({
                    success: false,
                    message: t("ha.connection_error", `Connection error: ${errorMessage}`)
                });
            }
        } finally {
            setTesting(false);
        }
    }, [config, t]);

    /**
     * Generate MCP configuration JSON
     */
    const generateMcpConfig = useCallback(() => {
        if (!config.url || !config.accessToken) {
            Toast.warning(t("ha.fill_all_fields", "Please fill in all fields"));
            return null;
        }

        // Normalize URL
        let haUrl = config.url.trim();
        if (!haUrl.startsWith("http://") && !haUrl.startsWith("https://")) {
            haUrl = `http://${haUrl}`;
        }
        haUrl = haUrl.replace(/\/$/, "");

        // Generate MCP config following xinnan-tech format
        const mcpConfig = {
            "Home Assistant": {
                command: "mcp-proxy",
                args: [`${haUrl}/mcp_server/sse`],
                env: {
                    API_ACCESS_TOKEN: config.accessToken
                },
                type: "sse",
                description: "Control smart home devices via HomeAssistant MCP"
            }
        };

        return mcpConfig;
    }, [config, t]);

    /**
     * Copy generated config to clipboard
     */
    const copyConfigToClipboard = useCallback(() => {
        const mcpConfig = generateMcpConfig();
        if (mcpConfig) {
            const configJson = JSON.stringify(mcpConfig, null, 2);
            navigator.clipboard.writeText(configJson).then(() => {
                Toast.success(t("ha.config_copied", "Configuration copied to clipboard!"));
            });
        }
    }, [generateMcpConfig, t]);

    /**
     * Send config to parent component
     */
    const handleApplyConfig = useCallback(() => {
        const mcpConfig = generateMcpConfig();
        if (mcpConfig && onConfigGenerated) {
            onConfigGenerated(mcpConfig);
            Toast.success(t("ha.config_applied", "HomeAssistant configuration applied!"));
        }
    }, [generateMcpConfig, onConfigGenerated, t]);

    return (
        <Card
            title={
                <div className="flex items-center gap-2">
                    <IconHome className="text-blue-500" />
                    <span>{t("ha.title", "HomeAssistant Integration")}</span>
                </div>
            }
            headerExtraContent={
                <Text type="tertiary" size="small">
                    {t("ha.subtitle", "Quick Setup")}
                </Text>
            }
            className="mb-4"
        >
            {/* Prerequisites Banner */}
            <Banner
                type="info"
                icon={<IconInfoCircle />}
                description={
                    <div>
                        <strong>{t("ha.prerequisites", "Prerequisites")}:</strong>
                        <ol className="mt-2 ml-4 list-decimal text-sm">
                            <li>{t("ha.prereq_1", "Install 'Model Context Protocol Server' integration in HomeAssistant")}</li>
                            <li>{t("ha.prereq_2", "Create a Long-Lived Access Token in HA (Profile → Security → Long-Lived Access Tokens)")}</li>
                            <li>{t("ha.prereq_3", "Ensure your server can reach HomeAssistant (same network)")}</li>
                        </ol>
                    </div>
                }
                className="mb-4"
            />

            <Form layout="vertical">
                {/* HomeAssistant URL */}
                <Form.Slot label={t("ha.url_label", "HomeAssistant URL")}>
                    <Input
                        placeholder="192.168.1.100:8123"
                        prefix={<IconLink />}
                        value={config.url}
                        onChange={(value) => setConfig(prev => ({ ...prev, url: value }))}
                    />
                    <div className="text-xs text-gray-500 mt-1">
                        {t("ha.url_help", "e.g., 192.168.1.100:8123 or homeassistant.local:8123")}
                    </div>
                </Form.Slot>

                {/* Access Token */}
                <Form.Slot label={t("ha.token_label", "Long-Lived Access Token")}>
                    <Input
                        placeholder="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
                        prefix={<IconKey />}
                        mode="password"
                        value={config.accessToken}
                        onChange={(value) => setConfig(prev => ({ ...prev, accessToken: value }))}
                    />
                    <div className="text-xs text-gray-500 mt-1">
                        {t("ha.token_help", "Generate from HA Profile → Security → Long-Lived Access Tokens")}
                    </div>
                </Form.Slot>

                {/* Action Buttons */}
                <div className="flex gap-2 mt-4">
                    <Button
                        theme="solid"
                        type="primary"
                        icon={testing ? <Spin size="small" /> : <IconTick />}
                        onClick={testConnection}
                        disabled={testing || !config.url || !config.accessToken}
                    >
                        {testing ? t("ha.testing", "Testing...") : t("ha.test_connection", "Test Connection")}
                    </Button>

                    <Button
                        icon={<IconCopy />}
                        onClick={copyConfigToClipboard}
                        disabled={!config.url || !config.accessToken}
                    >
                        {t("ha.copy_config", "Copy Config")}
                    </Button>

                    {onConfigGenerated && (
                        <Button
                            theme="solid"
                            type="secondary"
                            onClick={handleApplyConfig}
                            disabled={!config.url || !config.accessToken}
                        >
                            {t("ha.apply_config", "Apply Config")}
                        </Button>
                    )}
                </div>
            </Form>

            {/* Test Result */}
            {testResult && (
                <div className="mt-4">
                    <Banner
                        type={testResult.success ? "success" : "warning"}
                        icon={testResult.success ? <IconTick /> : <IconClose />}
                        title={testResult.message}
                        description={
                            testResult.success && testResult.haVersion ? (
                                <div className="text-sm mt-1">
                                    <div>HA Version: {testResult.haVersion}</div>
                                    {testResult.locationName && <div>Location: {testResult.locationName}</div>}
                                </div>
                            ) : null
                        }
                    />
                </div>
            )}

            {/* Advanced: Generated Config Preview */}
            <Collapsible
                isOpen={showAdvanced}
                collapseHeight={0}
                className="mt-4"
            >
                <div className="mt-4 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
                    <Title heading={6} className="mb-2">
                        {t("ha.generated_config", "Generated MCP Config")}
                    </Title>
                    <pre className="text-xs overflow-auto max-h-40 bg-gray-900 text-green-400 p-3 rounded">
                        {config.url && config.accessToken
                            ? JSON.stringify(generateMcpConfig(), null, 2)
                            : t("ha.fill_fields_preview", "Fill in the fields above to preview config")}
                    </pre>
                </div>
            </Collapsible>

            <Button
                type="tertiary"
                size="small"
                className="mt-2"
                onClick={() => setShowAdvanced(!showAdvanced)}
            >
                {showAdvanced
                    ? t("ha.hide_config", "Hide Generated Config")
                    : t("ha.show_config", "Show Generated Config")}
            </Button>

            {/* Tuya Local Guide */}
            <div className="mt-6 border-t pt-4">
                <Title heading={6} className="mb-3 flex items-center gap-2">
                    <span className="text-orange-500">🔌</span>
                    {t("ha.tuya_title", "Điều khiển thiết bị Tuya")}
                </Title>
                <Banner
                    type="warning"
                    icon={null}
                    description={
                        <div className="text-sm">
                            <p className="mb-2">
                                {t("ha.tuya_desc", "Để điều khiển thiết bị Tuya (đèn, ổ cắm, máy lạnh...) bằng giọng nói, cần cài thêm tuya-local integration:")}
                            </p>
                            <ol className="ml-4 list-decimal space-y-1">
                                <li>
                                    <a
                                        href="https://hacs.xyz/"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:underline"
                                    >
                                        {t("ha.tuya_step1", "Cài HACS (Home Assistant Community Store)")}
                                    </a>
                                </li>
                                <li>
                                    {t("ha.tuya_step2", "Trong HACS, tìm và cài \"Tuya Local\"")}
                                </li>
                                <li>
                                    <a
                                        href="https://iot.tuya.com/"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:underline"
                                    >
                                        {t("ha.tuya_step3", "Đăng ký tài khoản Tuya IoT Platform")}
                                    </a>
                                    {" → "}{t("ha.tuya_step3b", "lấy local_key của thiết bị")}
                                </li>
                                <li>
                                    {t("ha.tuya_step4", "Thêm thiết bị trong HA: Settings → Devices → Add Integration → Tuya Local")}
                                </li>
                                <li>
                                    {t("ha.tuya_step5", "Sau đó cấu hình HomeAssistant MCP ở trên")}
                                </li>
                            </ol>
                            <div className="mt-3 flex gap-2">
                                <a
                                    href="https://github.com/make-all/tuya-local"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded hover:bg-gray-300 dark:hover:bg-gray-600"
                                >
                                    📚 GitHub: tuya-local
                                </a>
                                <a
                                    href="https://github.com/make-all/tuya-local/blob/main/DEVICES.md"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs bg-gray-200 dark:bg-gray-700 px-2 py-1 rounded hover:bg-gray-300 dark:hover:bg-gray-600"
                                >
                                    📋 {t("ha.tuya_devices", "Danh sách thiết bị hỗ trợ")}
                                </a>
                            </div>
                        </div>
                    }
                    className="mb-0"
                />
            </div>
        </Card>
    );
};

export default HomeAssistantQuickSetup;
