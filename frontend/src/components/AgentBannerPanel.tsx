import { useState, useEffect, useRef } from "react";
import {
    Typography, Button, Toast, Form, ArrayField, Empty, RadioGroup, Radio, Tag, Modal, Upload
} from "@douyinfe/semi-ui";
import { IconSave, IconPlus, IconDelete, IconPlay, IconPause, IconDesktop, IconUpload } from "@douyinfe/semi-icons";
import { Monitor, Image as ImageIcon } from "lucide-react";
import apiClient from "@/config/axios-instance";

const { Text } = Typography;

interface AgentBannerPanelProps {
    agentId: string;
    agentName?: string;
    agent?: { banner_images?: BannerConfig[] };
    onRefresh?: () => void;
}

interface BannerConfig {
    id?: string;
    url?: string;
    video_url?: string;
    media_type?: "image" | "video";
    fallback_url?: string;
    enabled?: boolean | "true" | "false";
    priority?: number;
    duration?: number;
    transition?: "fade" | "slide" | "zoom" | "none";
    scale_mode?: React.CSSProperties["objectFit"];
    caption?: string;
    start_time?: string;
    end_time?: string;
    starts_at?: string;
    ends_at?: string;
}

interface BannerFormValues {
    banner_images?: BannerConfig[];
}

interface BannerFormApi {
    setValue: (field: string, value: unknown) => void;
    setError: (field: string, value: string) => void;
}

interface UploadRequestArgs {
    file: { fileInstance: File };
    onProgress: (data: { percent: number }) => void;
    onSuccess: (response?: unknown) => void;
    onError: (error: unknown) => void;
}

const errorMessage = (error: unknown, fallback: string) => {
    if (error instanceof Error) return error.message;
    return fallback;
};

const PREVIEW_SIZES = [
    { label: "Full HD (1920x1080)", w: 1920, h: 1080 },
    { label: "HD+ (1366x768)", w: 1366, h: 768 },
    { label: "HD (1280x720)", w: 1280, h: 720 },
];

const isVideoUrl = (url?: string) => /\.(mp4|webm|mov|m4v|m3u8)(\?|$)/i.test(url || "");

const resolveBannerMediaType = (banner?: BannerConfig) => {
    if (banner?.media_type === "video" || banner?.media_type === "image") {
        return banner.media_type;
    }
    return isVideoUrl(banner?.video_url || banner?.url) ? "video" : "image";
};

const resolveBannerMediaUrl = (banner?: BannerConfig) => {
    if (!banner) return "";
    return banner.video_url || banner.url || "";
};

export const AgentBannerPanel = ({ agentId, agent, onRefresh }: AgentBannerPanelProps) => {
    const [saving, setSaving] = useState(false);
    const [banners, setBanners] = useState<BannerConfig[]>([]);
    
    // Preview states
    const [previewSize, setPreviewSize] = useState(0); // index of PREVIEW_SIZES
    const [isPlaying, setIsPlaying] = useState(true);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [showPreviewModal, setShowPreviewModal] = useState(false);
    const formApiRef = useRef<BannerFormApi | null>(null);

    useEffect(() => {
        if (agent?.banner_images) {
            setBanners(agent.banner_images);
            if (formApiRef.current) {
                formApiRef.current.setValue('banner_images', agent.banner_images);
            }
        }
    }, [agent?.banner_images]);

    useEffect(() => {
        if (currentIndex >= banners.length) {
            setCurrentIndex(0);
        }
    }, [banners.length, currentIndex]);

    // Slideshow effect
    useEffect(() => {
        if (!isPlaying || banners.length === 0) return;
        
        const currentBanner = banners[currentIndex] || {};
        const durationSeconds = Math.min(
            120,
            Math.max(1, Number(currentBanner.duration) || 5)
        );
        
        const timer = setTimeout(() => {
            setCurrentIndex((prev) => (prev + 1) % banners.length);
        }, durationSeconds * 1000);
        
        return () => clearTimeout(timer);
    }, [isPlaying, banners, currentIndex]);

    const handleSave = async (values: BannerFormValues) => {
        setSaving(true);
        try {
            const normalizedBanners = (values.banner_images || []).map((banner, index) => ({
                ...banner,
                id: banner.id || `banner-${index + 1}`,
                media_type: resolveBannerMediaType(banner),
                url: banner.url || banner.video_url || "",
                enabled: banner.enabled !== false && banner.enabled !== "false",
                priority: Number(banner.priority) || 0,
                duration: Math.min(120, Math.max(1, Number(banner.duration) || 5)),
            }));
            await apiClient.put(`/agents/${agentId}`, {
                banner_images: normalizedBanners
            });
            Toast.success("Đã lưu cấu hình banner");
            onRefresh?.();
        } catch (err: unknown) {
            Toast.error(errorMessage(err, "Lỗi khi lưu"));
        } finally {
            setSaving(false);
        }
    };

    const previewResolution = PREVIEW_SIZES[previewSize];
    const currentBannerPreview = banners[currentIndex];
    const currentMediaType = resolveBannerMediaType(currentBannerPreview);
    const currentMediaUrl = resolveBannerMediaUrl(currentBannerPreview);

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h3 className="text-lg font-semibold flex items-center gap-2">
                        <Monitor size={20} className="text-blue-500" />
                        Cấu hình Kiosk Banner
                    </h3>
                    <Text type="tertiary">
                        Quản lý các hình ảnh quảng cáo, hiển thị lúc Kiosk rảnh (không có tương tác) trên thiết bị đầu cuối.
                    </Text>
                </div>
                <Button 
                    icon={<IconDesktop />} 
                    theme="solid" 
                    type="primary"
                    onClick={() => setShowPreviewModal(true)}
                    disabled={banners.length === 0}
                >
                    Live Preview
                </Button>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                {/* Left: Form Editor */}
                <div className="p-4 border rounded-xl bg-gray-50 dark:bg-slate-900 border-gray-200 dark:border-gray-800">
                    <Form
                        getFormApi={(formApi) => formApiRef.current = formApi}
                        initValues={{ banner_images: banners }}
                        onSubmit={handleSave}
                        onValueChange={(values) => setBanners(values.banner_images || [])}
                    >
                        {({ formApi }) => {
                            return (
                                <div className="space-y-4">
                                    <ArrayField field="banner_images" initValue={banners}>
                                        {({ add, arrayFields }) => (
                                            <>
                                                <div className="flex items-center justify-between mb-4">
                                                    <Text strong>Danh sách Slide ({arrayFields.length})</Text>
                                                    <Button icon={<IconPlus />} size="small" theme="light" onClick={add}>
                                                        Thêm Banner
                                                    </Button>
                                                </div>

                                                <div className="space-y-4">
                                                    {arrayFields.map(({ field, key, remove }, i) => (
                                                        <div key={key} className="p-4 border border-gray-200 dark:border-gray-700 bg-white dark:bg-slate-800 rounded-lg relative transition hover:shadow-md">
                                                            <div className="absolute top-2 right-2">
                                                                <Button icon={<IconDelete />} theme="borderless" type="danger" size="small" onClick={remove} />
                                                            </div>
                                                            <div className="flex gap-2">
                                                                <Tag color="blue" shape="circle" className="mt-1">{i + 1}</Tag>
                                                                <div className="flex-1 space-y-4">
                                                                    <div className="flex items-end gap-2">
                                                                        <div className="flex-1">
                                                                            <Form.Input field={`${field}.url`} label="Media URL (ảnh/video)" rules={[{ required: true }]} placeholder="https://..." />
                                                                        </div>
                                                                        <Upload
                                                                            action=""
                                                                            customRequest={async ({ file, onProgress, onSuccess, onError }: UploadRequestArgs) => {
                                                                                try {
                                                                                    const formData = new FormData();
                                                                                    formData.append("file", file.fileInstance);
                                                                                    const res = await apiClient.post("/sales/upload-image", formData, {
                                                                                        headers: { "Content-Type": "multipart/form-data" },
                                                                                        onUploadProgress: (progressEvent) => {
                                                                                            if (progressEvent.total) {
                                                                                                const percent = Math.floor((progressEvent.loaded / progressEvent.total) * 100);
                                                                                                onProgress({ percent });
                                                                                            }
                                                                                        }
                                                                                    });
                                                                                    
                                                                                    // Phải gán trực tiếp tại đây để tránh lỗi event loop của Upload component
                                                                                    if (res && res.data && res.data.url) {
                                                                                        formApi.setValue(`${field}.url`, res.data.url);
                                                                                        formApi.setError(`${field}.url`, '');
                                                                                        Toast.success("Upload thành công");
                                                                                    }
                                                                                    
                                                                                    onSuccess(res.data);
                                                                                } catch (err: unknown) {
                                                                                    Toast.error("Upload thất bại: " + errorMessage(err, "Lỗi không xác định"));
                                                                                    onError(err);
                                                                                }
                                                                            }}
                                                                            showUploadList={false}
                                                                            accept="image/*"
                                                                        >
                                                                            <Button
                                                                                htmlType="button"
                                                                                onClick={(e) => e.preventDefault()}
                                                                                icon={<IconUpload />}
                                                                                theme="light"
                                                                                style={{ marginBottom: "16px" }}
                                                                            >
                                                                                Upload Ảnh
                                                                            </Button>
                                                                        </Upload>
                                                                    </div>
                                                                    
                                                                    <div className="grid grid-cols-2 gap-4">
                                                                        <Form.Select field={`${field}.media_type`} label="Loại media" initValue="image" style={{ width: '100%' }}>
                                                                            <Form.Select.Option value="image">Ảnh</Form.Select.Option>
                                                                            <Form.Select.Option value="video">Video</Form.Select.Option>
                                                                        </Form.Select>
                                                                        <Form.InputNumber field={`${field}.duration`} label="Thời gian (giây)" min={1} max={60} initValue={5} />
                                                                    </div>
                                                                    <div className="grid grid-cols-2 gap-4">
                                                                        <Form.Select field={`${field}.transition`} label="Hiệu ứng" initValue="fade" style={{ width: '100%' }}>
                                                                            <Form.Select.Option value="fade">Fade</Form.Select.Option>
                                                                            <Form.Select.Option value="slide">Slide</Form.Select.Option>
                                                                            <Form.Select.Option value="zoom">Zoom</Form.Select.Option>
                                                                            <Form.Select.Option value="none">Không/None</Form.Select.Option>
                                                                        </Form.Select>
                                                                    </div>
                                                                    <div className="grid grid-cols-3 gap-4">
                                                                        <Form.Select field={`${field}.enabled`} label="Trạng thái" initValue="true" style={{ width: '100%' }}>
                                                                            <Form.Select.Option value="true">Đang phát</Form.Select.Option>
                                                                            <Form.Select.Option value="false">Tạm tắt</Form.Select.Option>
                                                                        </Form.Select>
                                                                        <Form.InputNumber field={`${field}.priority`} label="Ưu tiên" min={0} max={100} initValue={0} />
                                                                        <Form.Input field={`${field}.id`} label="Mã banner" placeholder={`banner-${i + 1}`} />
                                                                    </div>
                                                                    <div className="grid grid-cols-2 gap-4">
                                                                        <Form.Input field={`${field}.start_time`} label="Giờ bắt đầu" placeholder="09:00" />
                                                                        <Form.Input field={`${field}.end_time`} label="Giờ kết thúc" placeholder="22:00" />
                                                                    </div>
                                                                    <Form.Input field={`${field}.fallback_url`} label="Fallback image URL" placeholder="Ảnh dự phòng nếu ảnh chính lỗi" />
                                                                    
                                                                    <div className="grid grid-cols-2 gap-4">
                                                                        <Form.Select field={`${field}.scale_mode`} label="Scale Mode" initValue="cover" style={{ width: '100%' }}>
                                                                            <Form.Select.Option value="cover">Crop vừa màn (Cover)</Form.Select.Option>
                                                                            <Form.Select.Option value="contain">Giữ nguyên Aspect (Contain)</Form.Select.Option>
                                                                            <Form.Select.Option value="stretch">Kéo dãn (Stretch)</Form.Select.Option>
                                                                        </Form.Select>
                                                                        <Form.Input field={`${field}.caption`} label="Caption / Mô tả" />
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                    {arrayFields.length === 0 && (
                                                        <Empty title="Chưa có banner nào" description="Nhấp Thêm Banner để bắt đầu" />
                                                    )}
                                                </div>
                                            </>
                                        )}
                                    </ArrayField>
                                    
                                    <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-800">
                                        <Button icon={<IconSave />} htmlType="submit" theme="solid" type="primary" loading={saving}>
                                            Lưu Cấu Hình
                                        </Button>
                                    </div>
                                </div>
                            );
                        }}
                    </Form>
                </div>

                {/* Right: Inline Emulator */}
                <div className="hidden xl:block">
                    <Text strong className="block mb-4">Preview Box (Dành cho SmartTV / Kiosk Mode)</Text>
                    
                    <div className="border-[8px] border-slate-800 rounded-[20px] overflow-hidden bg-black relative shadow-2xl" 
                         style={{ aspectRatio: `${previewResolution.w} / ${previewResolution.h}` }}>
                        
                        {banners.length > 0 && currentBannerPreview ? (
                            <div className="w-full h-full relative" 
                                 style={{
                                    animation: currentBannerPreview.transition === 'fade' ? 'fadeIn 0.5s ease' : 
                                              currentBannerPreview.transition === 'zoom' ? 'zoomIn 0.8s ease' : 'none'
                                 }}>
                                {currentMediaType === "video" ? (
                                    <video
                                        src={currentMediaUrl}
                                        poster={currentBannerPreview.fallback_url}
                                        className="w-full h-full"
                                        style={{ objectFit: currentBannerPreview.scale_mode as React.CSSProperties['objectFit'] || 'cover' }}
                                        autoPlay
                                        muted
                                        loop
                                        playsInline
                                    />
                                ) : (
                                    <img
                                        src={currentMediaUrl}
                                        alt="banner"
                                        className="w-full h-full"
                                        style={{
                                            objectFit: currentBannerPreview.scale_mode as React.CSSProperties['objectFit'] || 'cover'
                                        }}
                                        onError={(e) => { (e.target as HTMLImageElement).src = currentBannerPreview.fallback_url || 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" fill="%23333"><rect width="100%" height="100%"/><text x="50%" y="50%" fill="%23fff" text-anchor="middle" dy=".3em">Lỗi hình ảnh</text></svg>' }}
                                    />
                                )}
                                
                                {/* Emotion GIF Overlay (Bottom Left per user requirement) */}
                                <div className="absolute left-6 bottom-6 w-[20%] max-w-[200px] aspect-square rounded-full flex items-center justify-center overflow-hidden z-20 shadow-2xl backdrop-blur-sm"
                                     style={{ 
                                        opacity: 0.8,
                                        background: 'rgba(0,0,0,0.1)',
                                        border: '4px solid rgba(255,255,255,0.2)',
                                        animation: 'scaleDown 0.5s ease-out'
                                     }}>
                                    <div className="w-full h-full bg-blue-500 flex items-center justify-center animate-pulse">
                                       <span className="text-white font-bold text-[4cqi]">^_^</span>
                                    </div>
                                    <div className="absolute inset-0 flex items-center justify-center text-white text-xs lowercase">Xiaozhi Avatar Sync</div>
                                </div>
                                
                                {currentBannerPreview.caption && (
                                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-6 pt-12 z-10">
                                        <h2 className="text-white text-2xl font-bold">{currentBannerPreview.caption}</h2>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="w-full h-full flex flex-col items-center justify-center text-gray-500">
                                <ImageIcon size={48} className="opacity-20 mb-4" />
                                <Text className="text-gray-400">Không có dữ liệu trình chiếu</Text>
                            </div>
                        )}
                    </div>
                    
                    <style dangerouslySetInnerHTML={{__html: `
                        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
                        @keyframes zoomIn { from { opacity: 0; transform: scale(1.1); } to { opacity: 1; transform: scale(1); } }
                        @keyframes scaleDown { from { transform: scale(1.5); opacity: 0; } to { transform: scale(1); opacity: 0.8; } }
                    `}} />
                </div>
            </div>

            {/* Modal: Live Device Preview */}
            <Modal
                visible={showPreviewModal}
                onCancel={() => setShowPreviewModal(false)}
                footer={null}
                width="95vw"
                closeOnEsc
                className="bg-slate-900"
                style={{ top: '2vh', padding: 0 }}
                bodyStyle={{ padding: 0, overflow: 'hidden' }}
            >
                <div className="h-[90vh] flex flex-col bg-slate-950 text-white p-4">
                    <div className="flex items-center justify-between mb-4 bg-slate-900 p-4 rounded-xl">
                        <div className="flex gap-4 items-center">
                            <RadioGroup type="button" value={previewSize} onChange={e => setPreviewSize(e.target.value)}>
                                {PREVIEW_SIZES.map((s, idx) => <Radio value={idx} key={idx}>{s.label}</Radio>)}
                            </RadioGroup>
                        </div>
                        
                        <div className="flex items-center gap-4">
                            <Text className="text-slate-300 font-mono text-sm">
                                [ Slide {currentIndex + 1} / {banners.length} ] - {banners[currentIndex]?.duration || 5}s
                            </Text>
                            <Button 
                                theme="solid" 
                                type={isPlaying ? "danger" : "primary"} 
                                icon={isPlaying ? <IconPause /> : <IconPlay />}
                                onClick={() => setIsPlaying(!isPlaying)}
                            >
                                {isPlaying ? 'Pause' : 'Play'}
                            </Button>
                        </div>
                    </div>

                    <div className="flex-1 flex items-center justify-center overflow-auto bg-black p-4 rounded-xl border border-slate-800">
                        <div 
                            className="bg-black relative shadow-2xl transition-all duration-300 ring-4 ring-slate-800" 
                            style={{ 
                                width: '100%',
                                maxWidth: previewResolution.w,
                                maxHeight: '100%',
                                aspectRatio: `${previewResolution.w} / ${previewResolution.h}` 
                            }}
                        >
                            {banners.length > 0 && currentBannerPreview && (
                                <div className="w-full h-full relative" 
                                     key={currentIndex}
                                     style={{
                                        animation: currentBannerPreview.transition === 'fade' ? 'fadeIn 0.5s ease' : 
                                                  currentBannerPreview.transition === 'zoom' ? 'zoomIn 0.8s ease' : 'none'
                                     }}>
                                    {currentMediaType === "video" ? (
                                        <video
                                            src={currentMediaUrl}
                                            poster={currentBannerPreview.fallback_url}
                                            className="w-full h-full"
                                            style={{ objectFit: currentBannerPreview.scale_mode || 'cover' }}
                                            autoPlay
                                            muted
                                            loop
                                            playsInline
                                        />
                                    ) : (
                                        <img
                                            src={currentMediaUrl}
                                            alt="banner"
                                            className="w-full h-full"
                                            style={{ objectFit: currentBannerPreview.scale_mode || 'cover' }}
                                        />
                                    )}
                                    
                                    {/* Emotion Avatar Box */}
                                    <div className="absolute left-8 bottom-8 w-[200px] h-[200px] rounded-full flex items-center justify-center overflow-hidden z-20 shadow-[0_0_40px_rgba(0,0,0,0.5)] backdrop-blur-md bg-white/10"
                                         style={{ 
                                            opacity: 0.8,
                                            border: '2px solid rgba(255,255,255,0.5)',
                                            animation: 'scaleDown 0.5s ease-out'
                                         }}>
                                        <div className="text-center">
                                            <div className="text-6xl mb-2 flex justify-center">
                                                <div className="w-24 h-24 rounded-full bg-blue-500 animate-pulse flex items-center justify-center">
                                                   <span className="text-white text-3xl font-black">AI</span>
                                                </div>
                                            </div>
                                            <div className="text-white text-sm font-semibold opacity-80">Listening...</div>
                                        </div>
                                    </div>
                                    
                                    {currentBannerPreview.caption && (
                                        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-12 pt-24 z-10">
                                            <h2 className="text-white text-4xl font-bold ml-64">{currentBannerPreview.caption}</h2>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </Modal>
        </div>
    );
};
