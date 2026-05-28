/**
 * FAQSettingsCard Component
 * 
 * Admin UI for editing FAQ section settings
 */

import {
    Card,
    Input,
    TextArea,
    Button,
    Switch,
    Typography,
    Divider
} from "@douyinfe/semi-ui";
import {
    IconPlus,
    IconDelete
} from "@douyinfe/semi-icons";
import { HelpCircle } from "lucide-react";

const { Text } = Typography;

export interface FAQItem {
    question: string;
    answer: string;
}

export interface FAQSettings {
    faq_enabled: boolean;
    faq_title: string;
    faq_subtitle: string;
    faq_list: FAQItem[];
}

interface FAQSettingsCardProps {
    settings: FAQSettings;
    onChange: (settings: FAQSettings) => void;
}

export function FAQSettingsCard({ settings, onChange }: FAQSettingsCardProps) {
    const updateField = <K extends keyof FAQSettings>(field: K, value: FAQSettings[K]) => {
        onChange({ ...settings, [field]: value });
    };

    const addFAQ = () => {
        updateField("faq_list", [...settings.faq_list, { question: "", answer: "" }]);
    };

    const removeFAQ = (index: number) => {
        updateField("faq_list", settings.faq_list.filter((_, i) => i !== index));
    };

    const updateFAQ = (index: number, field: keyof FAQItem, value: string) => {
        updateField(
            "faq_list",
            settings.faq_list.map((item, i) =>
                i === index ? { ...item, [field]: value } : item
            )
        );
    };

    return (
        <Card
            title={
                <span>
                    <HelpCircle className="h-5 w-5 inline mr-2" />
                    FAQ - Câu hỏi thường gặp
                </span>
            }
            headerExtraContent={
                <div className="flex items-center gap-4">
                    <Text type="tertiary">Hiển thị trên Landing Page</Text>
                    <Switch
                        checked={settings.faq_enabled}
                        onChange={(checked) => updateField("faq_enabled", checked)}
                    />
                </div>
            }
            style={{ marginTop: 16 }}
        >
            <div className="space-y-4">
                {/* Section Header */}
                <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                        <Text strong>Tiêu đề section</Text>
                        <Input
                            value={settings.faq_title}
                            onChange={(val) => updateField("faq_title", val)}
                            placeholder="Câu hỏi thường gặp"
                        />
                    </div>
                    <div className="space-y-2">
                        <Text strong>Phụ đề</Text>
                        <Input
                            value={settings.faq_subtitle}
                            onChange={(val) => updateField("faq_subtitle", val)}
                            placeholder="Những điều bạn cần biết"
                        />
                    </div>
                </div>

                <Divider />

                {/* FAQ List */}
                <div className="space-y-4">
                    <Text strong>Danh sách câu hỏi ({settings.faq_list.length})</Text>

                    {settings.faq_list.map((faq, index) => (
                        <div key={index} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg space-y-3">
                            <div className="flex justify-between items-start">
                                <Text strong className="text-blue-500">#{index + 1}</Text>
                                <Button
                                    type="danger"
                                    size="small"
                                    icon={<IconDelete />}
                                    onClick={() => removeFAQ(index)}
                                />
                            </div>

                            <div className="space-y-2">
                                <Text size="small">Câu hỏi</Text>
                                <Input
                                    value={faq.question}
                                    onChange={(val) => updateFAQ(index, "question", val)}
                                    placeholder="Làm thế nào để...?"
                                />
                            </div>

                            <div className="space-y-2">
                                <Text size="small">Trả lời</Text>
                                <TextArea
                                    value={faq.answer}
                                    onChange={(val) => updateFAQ(index, "answer", val)}
                                    placeholder="Bạn có thể..."
                                    rows={3}
                                />
                            </div>
                        </div>
                    ))}

                    <Button icon={<IconPlus />} onClick={addFAQ} block>
                        Thêm câu hỏi
                    </Button>
                </div>
            </div>
        </Card>
    );
}

export default FAQSettingsCard;
