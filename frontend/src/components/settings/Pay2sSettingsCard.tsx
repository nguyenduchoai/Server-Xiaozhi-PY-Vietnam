/**
 * Pay2s Settings Card
 * 
 * Admin configuration panel for Pay2s payment gateway.
 */

import { useState, useEffect } from "react";
import {
    Card,
    Input,
    Switch,
    Select,
    InputNumber,
    Button,
    Typography,
    Divider,
    Banner,
    Toast,
} from "@douyinfe/semi-ui";
import { IconSave, IconRefresh } from "@douyinfe/semi-icons";
import { pay2sService } from "@/services/pay2sService";
import type { Pay2sSettings, BankInfo } from "@/services/pay2sService";
import { Shield, TestTube, ExternalLink } from "lucide-react";

const { Text, Title } = Typography;

interface Pay2sSettingsCardProps {
    onSaveSuccess?: () => void;
}

export const Pay2sSettingsCard = ({ onSaveSuccess }: Pay2sSettingsCardProps) => {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [settings, setSettings] = useState<Pay2sSettings>({
        pay2s_enabled: false,
        pay2s_sandbox_mode: true,
        pay2s_partner_code: "",
        pay2s_access_key: "",
        pay2s_secret_key: "",
        pay2s_payment_timeout_minutes: 15,
        pay2s_bank_account_number: "",
        pay2s_bank_id: "",
    });
    const [banks, setBanks] = useState<Record<string, BankInfo>>({});

    useEffect(() => {
        loadSettings();
        loadBanks();
    }, []);

    const loadSettings = async () => {
        try {
            setLoading(true);
            const data = await pay2sService.getSettings();
            setSettings(data);
        } catch {
            // Settings not available or not authorized - use defaults
        } finally {
            setLoading(false);
        }
    };

    const loadBanks = async () => {
        try {
            const data = await pay2sService.getBanks();
            setBanks(data);
        } catch (err) {
            // Use fallback banks
            setBanks({
                ACB: { name: "Asia Commercial Bank", code: "970416" },
                VCB: { name: "Vietcombank", code: "970436" },
                TCB: { name: "Techcombank", code: "970407" },
                BIDV: { name: "BIDV", code: "970418" },
                MBB: { name: "MB Bank", code: "970422" },
            });
        }
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            await pay2sService.updateSettings(settings);
            Toast.success("Đã lưu cấu hình Pay2s!");
            onSaveSuccess?.();
        } catch (err: any) {
            Toast.error(err.response?.data?.detail || "Không thể lưu cấu hình");
        } finally {
            setSaving(false);
        }
    };

    const bankOptions = Object.entries(banks).map(([code, info]) => ({
        value: code,
        label: `${code} - ${info.name}`,
    }));

    return (
        <Card
            title={
                <span className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-blue-500" />
                    Pay2s Payment Gateway
                </span>
            }
            headerExtraContent={
                <a
                    href="https://docs.pay2s.vn"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-blue-500 hover:underline"
                >
                    <ExternalLink className="h-4 w-4" />
                    Tài liệu API
                </a>
            }
            loading={loading}
        >
            {/* Enable/Disable */}
            <div className="flex items-center justify-between mb-4">
                <div>
                    <Text strong>Bật Pay2s</Text>
                    <Text type="tertiary" size="small" className="block">
                        Cho phép thanh toán qua Pay2s gateway
                    </Text>
                </div>
                <Switch
                    checked={settings.pay2s_enabled}
                    onChange={(checked) => setSettings({ ...settings, pay2s_enabled: checked })}
                />
            </div>

            {/* Sandbox Mode */}
            <div className="flex items-center justify-between mb-6">
                <div>
                    <Text strong className="flex items-center gap-1">
                        <TestTube className="h-4 w-4" />
                        Sandbox Mode
                    </Text>
                    <Text type="tertiary" size="small" className="block">
                        Sử dụng môi trường test (sandbox.pay2s.vn)
                    </Text>
                </div>
                <Switch
                    checked={settings.pay2s_sandbox_mode}
                    onChange={(checked) => setSettings({ ...settings, pay2s_sandbox_mode: checked })}
                />
            </div>

            {settings.pay2s_sandbox_mode && (
                <Banner
                    type="info"
                    description="Đang sử dụng môi trường Sandbox. Để chạy production, tắt Sandbox Mode."
                    className="mb-4"
                />
            )}

            <Divider margin="16px" />

            {/* Credentials */}
            <Title heading={5} className="mb-4">Thông tin xác thực</Title>

            <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                    <Text strong>Partner Code</Text>
                    <Input
                        placeholder="PAY2SXXXXXX"
                        value={settings.pay2s_partner_code}
                        onChange={(val) => setSettings({ ...settings, pay2s_partner_code: val })}
                    />
                </div>

                <div className="space-y-2">
                    <Text strong>Access Key</Text>
                    <Input
                        placeholder="Nhập Access Key"
                        value={settings.pay2s_access_key}
                        onChange={(val) => setSettings({ ...settings, pay2s_access_key: val })}
                    />
                </div>
            </div>

            <div className="space-y-2 mt-4">
                <Text strong>Secret Key</Text>
                <Input
                    mode="password"
                    placeholder={settings.pay2s_secret_key === "******" ? "••••••" : "Nhập Secret Key"}
                    value={settings.pay2s_secret_key === "******" ? "" : settings.pay2s_secret_key}
                    onChange={(val) => setSettings({ ...settings, pay2s_secret_key: val })}
                />
                <Text type="tertiary" size="small">
                    ⚠️ Secret Key chỉ hiển thị khi bạn nhập mới. Để trống nếu không muốn thay đổi.
                </Text>
            </div>

            <Divider margin="16px" />

            {/* Bank Account */}
            <Title heading={5} className="mb-4">Tài khoản ngân hàng nhận tiền</Title>

            <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                    <Text strong>Ngân hàng</Text>
                    <Select
                        placeholder="Chọn ngân hàng"
                        style={{ width: "100%" }}
                        value={settings.pay2s_bank_id}
                        onChange={(val) => setSettings({ ...settings, pay2s_bank_id: val as string })}
                        optionList={bankOptions}
                        showClear
                    />
                </div>

                <div className="space-y-2">
                    <Text strong>Số tài khoản</Text>
                    <Input
                        placeholder="Nhập số tài khoản"
                        value={settings.pay2s_bank_account_number}
                        onChange={(val) => setSettings({ ...settings, pay2s_bank_account_number: val })}
                    />
                </div>
            </div>

            <Divider margin="16px" />

            {/* Settings */}
            <Title heading={5} className="mb-4">Cài đặt khác</Title>

            <div className="space-y-2">
                <Text strong>Thời gian timeout (phút)</Text>
                <InputNumber
                    min={5}
                    max={30}
                    value={settings.pay2s_payment_timeout_minutes}
                    onChange={(val) => setSettings({ ...settings, pay2s_payment_timeout_minutes: val as number })}
                    suffix="phút"
                    style={{ width: 150 }}
                />
                <Text type="tertiary" size="small" className="block">
                    Thời gian tối đa để khách hàng hoàn tất thanh toán
                </Text>
            </div>

            <Divider margin="16px" />

            {/* Actions */}
            <div className="flex gap-3">
                <Button
                    theme="solid"
                    icon={<IconSave />}
                    loading={saving}
                    onClick={handleSave}
                >
                    Lưu cấu hình
                </Button>
                <Button
                    icon={<IconRefresh />}
                    onClick={loadSettings}
                >
                    Tải lại
                </Button>
            </div>
        </Card>
    );
};

export default Pay2sSettingsCard;
