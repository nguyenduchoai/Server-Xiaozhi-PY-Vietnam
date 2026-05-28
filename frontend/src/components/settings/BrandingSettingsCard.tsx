/**
 * BrandingSettingsCard Component
 * 
 * Admin UI for editing Branding/Parent Company settings
 */

import {
    Card,
    Input,
    Typography
} from "@douyinfe/semi-ui";
import { Building2, ExternalLink } from "lucide-react";

const { Text } = Typography;

export interface BrandingSettings {
    parent_company_name: string;
    parent_company_url: string;
    company_badge_text: string;
}

interface BrandingSettingsCardProps {
    settings: BrandingSettings;
    onChange: (settings: BrandingSettings) => void;
}

export function BrandingSettingsCard({ settings, onChange }: BrandingSettingsCardProps) {
    const updateField = (field: keyof BrandingSettings, value: string) => {
        onChange({ ...settings, [field]: value });
    };

    return (
        <Card
            title={
                <span>
                    <Building2 className="h-5 w-5 inline mr-2" />
                    Thông tin Công ty Mẹ
                </span>
            }
            headerExtraContent={<Text type="tertiary">Hiển thị badge và link công ty mẹ trên Landing Page</Text>}
            style={{ marginTop: 16 }}
        >
            <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                        <Text strong>Tên công ty mẹ</Text>
                        <Input
                            value={settings.parent_company_name}
                            onChange={(val) => updateField("parent_company_name", val)}
                            placeholder="Bizino.AI"
                        />
                    </div>
                    <div className="space-y-2">
                        <Text strong>Badge text</Text>
                        <Input
                            value={settings.company_badge_text}
                            onChange={(val) => updateField("company_badge_text", val)}
                            placeholder="by Bizino.AI"
                        />
                        <Text type="tertiary" size="small">Hiển thị bên cạnh logo</Text>
                    </div>
                </div>

                <div className="space-y-2">
                    <Text strong>
                        <ExternalLink className="h-4 w-4 inline mr-1" />
                        URL Công ty mẹ
                    </Text>
                    <Input
                        value={settings.parent_company_url}
                        onChange={(val) => updateField("parent_company_url", val)}
                        placeholder="https://bizino.ai"
                    />
                    <Text type="tertiary" size="small">Link khi click vào badge</Text>
                </div>

                {/* Preview */}
                <div className="mt-4 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
                    <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 8 }}>Preview:</Text>
                    <div className="flex items-center gap-2">
                        <span className="text-lg font-bold">YourBrand</span>
                        <a
                            href={settings.parent_company_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-2 py-1 bg-blue-500/20 text-blue-500 text-xs rounded-full hover:bg-blue-500/30"
                        >
                            {settings.company_badge_text || "by Bizino.AI"}
                        </a>
                    </div>
                </div>
            </div>
        </Card>
    );
}

export default BrandingSettingsCard;
