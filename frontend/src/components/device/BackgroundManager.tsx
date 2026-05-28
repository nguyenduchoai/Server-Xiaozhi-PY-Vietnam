import { useState, useRef } from "react";
import {
    Upload, Image as ImageIcon, Trash2, Check, Loader2,
    Monitor, Palette, RefreshCw
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

import {
    useDeviceBackgrounds,
    useUploadBackground,
    useDeleteBackground,
    useApplyBackground,
    type Background,
} from "@/queries/background-queries";

interface BackgroundManagerProps {
    deviceId: string;
    screenType?: string;
}

const BACKGROUND_TYPES = [
    { id: "idle", name: "Chờ (Idle)", icon: "😴" },
    { id: "listening", name: "Đang nghe", icon: "👂" },
    { id: "speaking", name: "Đang nói", icon: "🗣️" },
    { id: "custom1", name: "Tùy chỉnh 1", icon: "🎨" },
    { id: "custom2", name: "Tùy chỉnh 2", icon: "✨" },
];

const SCREEN_TYPES = [
    { id: "240x240", name: "240x240" },
    { id: "284x240", name: "284x240 (OSTB)" },
    { id: "320x240", name: "320x240" },
];

export function BackgroundManager({ deviceId, screenType: defaultScreenType = "240x240" }: BackgroundManagerProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [selectedType, setSelectedType] = useState("idle");
    const [screenType, setScreenType] = useState(defaultScreenType);
    const [uploading, setUploading] = useState(false);

    // Queries
    const { data: backgroundsData, isLoading, refetch } = useDeviceBackgrounds(deviceId);
    const uploadMutation = useUploadBackground();
    const deleteMutation = useDeleteBackground();
    const applyMutation = useApplyBackground();

    const backgrounds = backgroundsData?.backgrounds || [];

    const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        // Validate
        if (!file.type.startsWith("image/")) {
            toast.error("Vui lòng chọn file ảnh");
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            toast.error("File quá lớn (tối đa 5MB)");
            return;
        }

        setUploading(true);
        try {
            await uploadMutation.mutateAsync({
                deviceId,
                file,
                backgroundType: selectedType,
                screenType,
            });
            toast.success("Đã tải lên background");
            refetch();
        } catch {
            toast.error("Không thể tải lên");
        } finally {
            setUploading(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = "";
            }
        }
    };

    const handleDelete = async (bg: Background) => {
        try {
            await deleteMutation.mutateAsync({
                deviceId,
                backgroundId: bg.id,
            });
            toast.success("Đã xóa background");
            refetch();
        } catch {
            toast.error("Không thể xóa");
        }
    };

    const handleApply = async (bg: Background) => {
        try {
            await applyMutation.mutateAsync({
                deviceId,
                backgroundType: bg.background_type,
                fileUrl: bg.file_url,
            });
            toast.success("Đã gửi đến thiết bị");
        } catch {
            toast.error("Không thể gửi đến thiết bị");
        }
    };

    return (
        <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-gradient-to-br from-pink-500 to-purple-500">
                            <ImageIcon className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <CardTitle className="text-white">Hình nền tùy chỉnh</CardTitle>
                            <CardDescription className="text-slate-400">
                                Upload ảnh nền cho các trạng thái thiết bị
                            </CardDescription>
                        </div>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => refetch()}
                        className="text-slate-400"
                    >
                        <RefreshCw className="w-4 h-4" />
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Upload Section */}
                <div className="p-4 rounded-lg border-2 border-dashed border-slate-600 bg-slate-900/50">
                    <div className="flex flex-wrap items-center gap-4">
                        <div className="flex-1 min-w-[200px]">
                            <Select value={selectedType} onValueChange={setSelectedType}>
                                <SelectTrigger className="bg-slate-800 border-slate-700">
                                    <SelectValue placeholder="Chọn loại" />
                                </SelectTrigger>
                                <SelectContent>
                                    {BACKGROUND_TYPES.map((type) => (
                                        <SelectItem key={type.id} value={type.id}>
                                            {type.icon} {type.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <div className="flex-1 min-w-[150px]">
                            <Select value={screenType} onValueChange={setScreenType}>
                                <SelectTrigger className="bg-slate-800 border-slate-700">
                                    <Monitor className="w-4 h-4 mr-2" />
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {SCREEN_TYPES.map((type) => (
                                        <SelectItem key={type.id} value={type.id}>
                                            {type.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleFileSelect}
                            className="hidden"
                        />
                        <Button
                            onClick={() => fileInputRef.current?.click()}
                            disabled={uploading}
                            className="bg-purple-600 hover:bg-purple-700"
                        >
                            {uploading ? (
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            ) : (
                                <Upload className="w-4 h-4 mr-2" />
                            )}
                            Tải lên
                        </Button>
                    </div>
                    <p className="text-xs text-slate-500 mt-2">
                        Hỗ trợ: PNG, JPG, WEBP (tối đa 5MB). Ảnh sẽ được resize tự động.
                    </p>
                </div>

                {/* Backgrounds Grid */}
                {isLoading ? (
                    <div className="grid grid-cols-3 gap-4">
                        {[1, 2, 3].map((i) => (
                            <Skeleton key={i} className="aspect-square rounded-lg bg-slate-700" />
                        ))}
                    </div>
                ) : backgrounds.length === 0 ? (
                    <div className="text-center py-8">
                        <Palette className="w-12 h-12 mx-auto text-slate-600 mb-2" />
                        <p className="text-slate-400">Chưa có hình nền nào</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                        {backgrounds.map((bg) => (
                            <div
                                key={bg.id}
                                className="group relative aspect-square rounded-lg overflow-hidden bg-slate-700 border border-slate-600"
                            >
                                <img
                                    src={bg.file_url}
                                    alt={bg.background_type}
                                    className="w-full h-full object-cover"
                                />

                                {/* Overlay */}
                                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2">
                                    <Button
                                        size="sm"
                                        onClick={() => handleApply(bg)}
                                        disabled={applyMutation.isPending}
                                        className="bg-green-600 hover:bg-green-700"
                                    >
                                        <Check className="w-4 h-4 mr-1" />
                                        Áp dụng
                                    </Button>
                                    <Button
                                        size="sm"
                                        variant="destructive"
                                        onClick={() => handleDelete(bg)}
                                        disabled={deleteMutation.isPending}
                                    >
                                        <Trash2 className="w-4 h-4 mr-1" />
                                        Xóa
                                    </Button>
                                </div>

                                {/* Badge */}
                                <Badge className="absolute top-2 left-2 bg-slate-900/80">
                                    {BACKGROUND_TYPES.find(t => t.id === bg.background_type)?.icon}{" "}
                                    {BACKGROUND_TYPES.find(t => t.id === bg.background_type)?.name || bg.background_type}
                                </Badge>

                                {/* Size info */}
                                <div className="absolute bottom-2 right-2 text-xs text-white/80 bg-slate-900/80 px-2 py-1 rounded">
                                    {bg.width}x{bg.height}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}

export default BackgroundManager;
