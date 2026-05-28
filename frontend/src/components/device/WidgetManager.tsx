import { useState, useEffect } from "react";
import {
    Clock, Cloud, Calendar as CalendarIcon, Moon, Loader2, Save
} from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

import { useDeviceTheme, useUpdateWidgets } from "@/queries/theme-queries";

interface WidgetManagerProps {
    deviceId: string;
}

interface WidgetConfig {
    clock: boolean;
    weather: boolean;
    calendar: boolean;
    lunar: boolean;
}

const WIDGETS = [
    {
        id: "clock",
        name: "Đồng hồ",
        description: "Hiển thị giờ hiện tại",
        icon: Clock,
        color: "text-blue-400",
    },
    {
        id: "weather",
        name: "Thời tiết",
        description: "Hiển thị nhiệt độ và thời tiết",
        icon: Cloud,
        color: "text-yellow-400",
    },
    {
        id: "calendar",
        name: "Lịch dương",
        description: "Hiển thị ngày tháng năm",
        icon: CalendarIcon,
        color: "text-green-400",
    },
    {
        id: "lunar",
        name: "Lịch âm",
        description: "Hiển thị ngày âm lịch",
        icon: Moon,
        color: "text-purple-400",
    },
];

export function WidgetManager({ deviceId }: WidgetManagerProps) {
    const [widgets, setWidgets] = useState<WidgetConfig>({
        clock: true,
        weather: true,
        calendar: false,
        lunar: true,
    });
    const [hasChanges, setHasChanges] = useState(false);

    // Queries
    const { data: themeData, isLoading } = useDeviceTheme(deviceId);
    const updateMutation = useUpdateWidgets();

    // Initialize from server data
    useEffect(() => {
        if (themeData?.widgets) {
            setWidgets({
                clock: themeData.widgets.clock ?? true,
                weather: themeData.widgets.weather ?? true,
                calendar: themeData.widgets.calendar ?? false,
                lunar: themeData.widgets.lunar ?? true,
            });
        }
    }, [themeData]);

    const handleToggle = (widgetId: keyof WidgetConfig) => {
        setWidgets(prev => ({
            ...prev,
            [widgetId]: !prev[widgetId],
        }));
        setHasChanges(true);
    };

    const handleSave = async () => {
        try {
            await updateMutation.mutateAsync({
                deviceId,
                widgets,
            });
            toast.success("Đã cập nhật widget và gửi đến thiết bị");
            setHasChanges(false);
        } catch {
            toast.error("Không thể cập nhật widget");
        }
    };

    if (isLoading) {
        return (
            <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="py-8 text-center">
                    <Loader2 className="w-8 h-8 mx-auto animate-spin text-slate-400" />
                </CardContent>
            </Card>
        );
    }

    return (
        <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle className="text-white flex items-center gap-2">
                            <Clock className="w-5 h-5 text-blue-400" />
                            Widget hiển thị
                        </CardTitle>
                        <CardDescription className="text-slate-400">
                            Chọn các widget hiển thị trên màn hình chờ
                        </CardDescription>
                    </div>
                    {hasChanges && (
                        <Button
                            onClick={handleSave}
                            disabled={updateMutation.isPending}
                            className="bg-green-600 hover:bg-green-700"
                        >
                            {updateMutation.isPending ? (
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            ) : (
                                <Save className="w-4 h-4 mr-2" />
                            )}
                            Lưu & Gửi
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {WIDGETS.map((widget) => {
                    const Icon = widget.icon;
                    const isEnabled = widgets[widget.id as keyof WidgetConfig];

                    return (
                        <div
                            key={widget.id}
                            className={`flex items-center justify-between p-4 rounded-lg border transition-all ${isEnabled
                                    ? "bg-slate-700/50 border-slate-600"
                                    : "bg-slate-800/30 border-slate-700/50"
                                }`}
                        >
                            <div className="flex items-center gap-4">
                                <div className={`p-2 rounded-lg bg-slate-700/50 ${widget.color}`}>
                                    <Icon className="w-5 h-5" />
                                </div>
                                <div>
                                    <Label className="text-white font-medium">
                                        {widget.name}
                                    </Label>
                                    <p className="text-sm text-slate-400">
                                        {widget.description}
                                    </p>
                                </div>
                            </div>
                            <Switch
                                checked={isEnabled}
                                onCheckedChange={() => handleToggle(widget.id as keyof WidgetConfig)}
                            />
                        </div>
                    );
                })}

                {/* Preview */}
                <div className="mt-6 p-4 rounded-lg bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700">
                    <p className="text-xs text-slate-500 mb-3">Xem trước màn hình</p>
                    <div className="aspect-square max-w-[200px] mx-auto bg-slate-950 rounded-lg p-4 flex flex-col justify-between">
                        {/* Clock */}
                        {widgets.clock && (
                            <div className="text-center">
                                <div className="text-2xl font-bold text-white">14:15</div>
                            </div>
                        )}

                        {/* Middle content */}
                        <div className="flex-1 flex items-center justify-center">
                            <div className="text-4xl">😊</div>
                        </div>

                        {/* Bottom row */}
                        <div className="flex justify-between text-xs text-slate-400">
                            {widgets.weather && <span>🌤️ 32°C</span>}
                            {widgets.calendar && <span>📅 27/01</span>}
                            {widgets.lunar && <span>🌙 28/12</span>}
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}

export default WidgetManager;
