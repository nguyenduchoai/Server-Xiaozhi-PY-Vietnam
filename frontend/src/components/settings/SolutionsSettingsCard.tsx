/**
 * SolutionsSettingsCard Component
 * 
 * Admin UI for editing Solutions section (B2B landing pages)
 */

import {
    Card,
    Input,
    TextArea,
    Button,
    Switch,
    Typography,
    Divider,
    TagInput
} from "@douyinfe/semi-ui";
import {
    IconPlus,
    IconDelete
} from "@douyinfe/semi-icons";
import { Lightbulb } from "lucide-react";

const { Text } = Typography;

export interface SolutionItem {
    id: string;
    icon: string;
    title: string;
    subtitle: string;
    description: string;
    features: string[];
    use_cases: string[];
    gradient: string;
}

export interface SolutionsSettings {
    solutions_enabled: boolean;
    solutions_title: string;
    solutions_subtitle: string;
    solutions_list: SolutionItem[];
}

interface SolutionsSettingsCardProps {
    settings: SolutionsSettings;
    onChange: (settings: SolutionsSettings) => void;
}

// Common Lucide icon names for dropdown
const ICON_OPTIONS = [
    "Headphones", "Video", "Mic", "Bot", "Users", "Building2",
    "ShoppingCart", "MessageSquare", "BarChart", "Settings",
    "Zap", "Shield", "Globe", "Clock", "Phone", "Mail"
];

// Gradient presets
const GRADIENT_PRESETS = [
    "from-blue-600 to-cyan-500",
    "from-violet-600 to-pink-500",
    "from-orange-500 to-red-500",
    "from-green-500 to-teal-500",
    "from-purple-600 to-blue-500",
    "from-yellow-500 to-orange-500",
];

export function SolutionsSettingsCard({ settings, onChange }: SolutionsSettingsCardProps) {
    const updateField = <K extends keyof SolutionsSettings>(field: K, value: SolutionsSettings[K]) => {
        onChange({ ...settings, [field]: value });
    };

    const addSolution = () => {
        const newId = `solution-${Date.now()}`;
        updateField("solutions_list", [
            ...settings.solutions_list,
            {
                id: newId,
                icon: "Bot",
                title: "",
                subtitle: "",
                description: "",
                features: [],
                use_cases: [],
                gradient: GRADIENT_PRESETS[settings.solutions_list.length % GRADIENT_PRESETS.length]
            }
        ]);
    };

    const removeSolution = (index: number) => {
        updateField("solutions_list", settings.solutions_list.filter((_, i) => i !== index));
    };

    const updateSolution = (index: number, field: keyof SolutionItem, value: unknown) => {
        updateField(
            "solutions_list",
            settings.solutions_list.map((item, i) =>
                i === index ? { ...item, [field]: value } : item
            )
        );
    };

    return (
        <Card
            title={
                <span>
                    <Lightbulb className="h-5 w-5 inline mr-2" />
                    Giải pháp (Solutions)
                </span>
            }
            headerExtraContent={
                <div className="flex items-center gap-4">
                    <Text type="tertiary">Dành cho Landing Page B2B</Text>
                    <Switch
                        checked={settings.solutions_enabled}
                        onChange={(checked) => updateField("solutions_enabled", checked)}
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
                            value={settings.solutions_title}
                            onChange={(val) => updateField("solutions_title", val)}
                            placeholder="4 Giải pháp AI"
                        />
                    </div>
                    <div className="space-y-2">
                        <Text strong>Phụ đề</Text>
                        <Input
                            value={settings.solutions_subtitle}
                            onChange={(val) => updateField("solutions_subtitle", val)}
                            placeholder="Tự động hóa doanh nghiệp của bạn"
                        />
                    </div>
                </div>

                <Divider />

                {/* Solutions List */}
                <div className="space-y-4">
                    <Text strong>Danh sách giải pháp ({settings.solutions_list.length})</Text>

                    {settings.solutions_list.map((solution, index) => (
                        <div key={solution.id} className="p-4 border rounded-lg space-y-4 bg-gray-50 dark:bg-gray-800">
                            <div className="flex justify-between items-center">
                                <div
                                    className={`px-3 py-1 rounded-full text-white text-sm font-bold bg-gradient-to-r ${solution.gradient}`}
                                >
                                    #{index + 1} - {solution.title || "New Solution"}
                                </div>
                                <Button
                                    type="danger"
                                    size="small"
                                    icon={<IconDelete />}
                                    onClick={() => removeSolution(index)}
                                />
                            </div>

                            <div className="grid gap-4 md:grid-cols-3">
                                <div className="space-y-2">
                                    <Text size="small">Icon (Lucide)</Text>
                                    <Input
                                        value={solution.icon}
                                        onChange={(val) => updateSolution(index, "icon", val)}
                                        placeholder="Headphones"
                                    />
                                    <Text type="tertiary" size="small">
                                        {ICON_OPTIONS.slice(0, 6).join(", ")}...
                                    </Text>
                                </div>
                                <div className="space-y-2">
                                    <Text size="small">Tiêu đề</Text>
                                    <Input
                                        value={solution.title}
                                        onChange={(val) => updateSolution(index, "title", val)}
                                        placeholder="AI Tư Vấn Quầy"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Text size="small">Phụ đề</Text>
                                    <Input
                                        value={solution.subtitle}
                                        onChange={(val) => updateSolution(index, "subtitle", val)}
                                        placeholder="Thay thế nhân viên tại quầy"
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Text size="small">Mô tả chi tiết</Text>
                                <TextArea
                                    value={solution.description}
                                    onChange={(val) => updateSolution(index, "description", val)}
                                    placeholder="Mô tả giải pháp..."
                                    rows={2}
                                />
                            </div>

                            <div className="grid gap-4 md:grid-cols-2">
                                <div className="space-y-2">
                                    <Text size="small">Tính năng (Enter để thêm)</Text>
                                    <TagInput
                                        value={solution.features}
                                        onChange={(val) => updateSolution(index, "features", val || [])}
                                        placeholder="24/7, Đa ngôn ngữ..."
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Text size="small">Use Cases (Enter để thêm)</Text>
                                    <TagInput
                                        value={solution.use_cases}
                                        onChange={(val) => updateSolution(index, "use_cases", val || [])}
                                        placeholder="Ngân hàng, Retail..."
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Text size="small">Gradient</Text>
                                <div className="flex gap-2 flex-wrap">
                                    {GRADIENT_PRESETS.map((grad) => (
                                        <button
                                            key={grad}
                                            onClick={() => updateSolution(index, "gradient", grad)}
                                            className={`w-8 h-8 rounded-lg bg-gradient-to-r ${grad} ${solution.gradient === grad ? "ring-2 ring-offset-2 ring-blue-500" : ""
                                                }`}
                                        />
                                    ))}
                                </div>
                            </div>
                        </div>
                    ))}

                    <Button icon={<IconPlus />} onClick={addSolution} block disabled={settings.solutions_list.length >= 6}>
                        Thêm giải pháp {settings.solutions_list.length >= 6 ? "(Tối đa 6)" : ""}
                    </Button>
                </div>
            </div>
        </Card>
    );
}

export default SolutionsSettingsCard;
