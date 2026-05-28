/**
 * Emoji Pack Editor Page
 * Create or edit emoji packs with emotion grid
 */
import { useState, useCallback, memo, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
    Button,
    Card,
    Typography,
    Spin,
    Form,
    Modal,
    Banner
} from "@douyinfe/semi-ui";
import {
    IconArrowLeft,
    IconSave,
    IconEmoji
} from "@douyinfe/semi-icons";
import { Share2 } from "lucide-react";

import { PageHead } from "@/components";
import { useToast } from "@/hooks/use-toast";
import {
    useEmojiPackDetail,
    useCreateEmojiPack,
    useUpdateEmojiPack,
    useUploadEmotion,
    useDeleteEmotion,
    useShareEmojiPack,
    type EmotionAssetInfo
} from "@/queries/emoji-packs";


const { Title, Text } = Typography;

// 21 standard emotions
const EMOTION_NAMES = [
    "neutral", "happy", "laughing", "funny", "sad", "angry",
    "crying", "loving", "embarrassed", "surprised", "shocked", "thinking",
    "winking", "cool", "relaxed", "delicious", "kissy", "confident",
    "sleepy", "silly", "confused"
];

// Emotion display names (Vietnamese)
const EMOTION_LABELS: Record<string, string> = {
    neutral: "Bình thường",
    happy: "Vui vẻ",
    laughing: "Cười lớn",
    funny: "Hài hước",
    sad: "Buồn",
    angry: "Giận dữ",
    crying: "Khóc",
    loving: "Yêu thương",
    embarrassed: "Xấu hổ",
    surprised: "Ngạc nhiên",
    shocked: "Sốc",
    thinking: "Suy nghĩ",
    winking: "Nháy mắt",
    cool: "Cool",
    relaxed: "Thư giãn",
    delicious: "Ngon",
    kissy: "Hôn",
    confident: "Tự tin",
    sleepy: "Buồn ngủ",
    silly: "Ngớ ngẩn",
    confused: "Bối rối"
};

// Default emoji for each emotion
const DEFAULT_EMOJIS: Record<string, string> = {
    neutral: "😐",
    happy: "😊",
    laughing: "😆",
    funny: "😂",
    sad: "😔",
    angry: "😠",
    crying: "😭",
    loving: "😍",
    embarrassed: "😳",
    surprised: "😯",
    shocked: "😱",
    thinking: "🤔",
    winking: "😉",
    cool: "😎",
    relaxed: "😌",
    delicious: "🤤",
    kissy: "😘",
    confident: "😏",
    sleepy: "😴",
    silly: "😜",
    confused: "🙄"
};

// Base pack options
const BASE_PACK_OPTIONS = [
    { value: "twemoji", label: "Twemoji (Twitter)" },
    { value: "noto", label: "Noto Emoji (Google)" },
    { value: "openmoji", label: "OpenMoji" },
];

// Emotion cell component
interface EmotionCellProps {
    emotion: string;
    asset?: EmotionAssetInfo;
    onUpload: (file: File) => void;
    onReset: () => void;
    isUploading: boolean;
    targetSize: number;
}

const EmotionCell = memo(({
    emotion,
    asset,
    onUpload,
    onReset,
    isUploading,
    targetSize
}: EmotionCellProps) => {
    const inputRef = useRef<HTMLInputElement>(null);
    const isCustom = asset?.is_custom ?? false;

    const handleClick = () => {
        inputRef.current?.click();
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            onUpload(file);
        }
        // Reset input
        if (inputRef.current) {
            inputRef.current.value = "";
        }
    };

    return (
        <div className="relative group">
            <div
                className={`
          aspect-square rounded-lg border-2 flex flex-col items-center justify-center
          cursor-pointer transition-all
          ${isCustom ? "border-green-500 bg-green-50" : "border-muted hover:border-primary"}
          ${isUploading ? "opacity-50" : ""}
        `}
                onClick={handleClick}
            >
                {isUploading ? (
                    <Spin size="small" />
                ) : (
                    <>
                        {/* Emoji display */}
                        <div
                            className="text-4xl mb-1"
                            style={{ width: targetSize / 2, height: targetSize / 2 }}
                        >
                            {asset?.url ? (
                                <img
                                    src={asset.url}
                                    alt={emotion}
                                    className="w-full h-full object-contain"
                                    onError={(e) => {
                                        e.currentTarget.src = "";
                                        e.currentTarget.textContent = DEFAULT_EMOJIS[emotion];
                                    }}
                                />
                            ) : (
                                <span className="text-4xl">{DEFAULT_EMOJIS[emotion]}</span>
                            )}
                        </div>

                        {/* Emotion label */}
                        <Text size="small" type="tertiary" className="text-center">
                            {EMOTION_LABELS[emotion]}
                        </Text>

                        {/* Custom indicator */}
                        {isCustom && (
                            <span className="absolute top-1 right-1 w-2 h-2 bg-green-500 rounded-full" />
                        )}
                    </>
                )}
            </div>

            {/* Hidden file input */}
            <input
                ref={inputRef}
                type="file"
                accept="image/png,image/gif"
                className="hidden"
                onChange={handleFileChange}
            />

            {/* Reset button for custom emotions */}
            {isCustom && !isUploading && (
                <button
                    className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full
            opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                    onClick={(e) => {
                        e.stopPropagation();
                        onReset();
                    }}
                >
                    ×
                </button>
            )}
        </div>
    );
});

function EmojiPackEditorComponent() {
    const { packId } = useParams<{ packId: string }>();
    const navigate = useNavigate();
    const { t } = useTranslation(["emoji", "common"]);
    const { toast } = useToast();
    const [formApi, setFormApi] = useState<any>(null);

    const isNewPack = packId === "new";

    // State
    const [uploadingEmotion, setUploadingEmotion] = useState<string | null>(null);

    // Queries
    const {
        data: pack,
        isLoading: loadingPack,
        refetch: refetchPack
    } = useEmojiPackDetail(isNewPack ? "" : packId || "");

    // Mutations
    const { mutate: createPack, isPending: isCreating } = useCreateEmojiPack();
    const { mutate: updatePack, isPending: isUpdating } = useUpdateEmojiPack();
    const { mutate: uploadEmotion } = useUploadEmotion();
    const { mutate: deleteEmotion } = useDeleteEmotion();
    const { mutate: sharePack, isPending: isSharing } = useShareEmojiPack();

    // Form initial values
    const initialValues = {
        name: pack?.name || "",
        description: pack?.description || "",
        target_size: pack?.target_size || 64,
        base_pack: pack?.base_pack || "twemoji",
    };

    // Save handler
    const handleSave = useCallback(() => {
        if (!formApi) return;

        formApi.validate().then((values: any) => {
            if (isNewPack) {
                createPack(values, {
                    onSuccess: (newPack) => {
                        toast({
                            title: t("common:success"),
                            description: t("emoji:pack_created"),
                        });
                        navigate(`/emoji-packs/${newPack.id}/edit`);
                    },
                    onError: (error: any) => {
                        toast({
                            title: t("common:error"),
                            description: error.message,
                            variant: "destructive",
                        });
                    }
                });
            } else if (packId) {
                updatePack({ id: packId, payload: values }, {
                    onSuccess: () => {
                        toast({
                            title: t("common:success"),
                            description: t("emoji:pack_updated"),
                        });
                        refetchPack();
                    },
                    onError: (error: any) => {
                        toast({
                            title: t("common:error"),
                            description: error.message,
                            variant: "destructive",
                        });
                    }
                });
            }
        });
    }, [formApi, isNewPack, packId, createPack, updatePack, t, toast, navigate, refetchPack]);

    // Upload emotion handler
    const handleUploadEmotion = useCallback((emotion: string, file: File) => {
        if (!packId || isNewPack) return;

        // Validate file
        if (file.size > 500 * 1024) {
            toast({
                title: t("common:error"),
                description: t("emoji:file_too_large"),
                variant: "destructive",
            });
            return;
        }

        setUploadingEmotion(emotion);
        uploadEmotion(
            { packId, emotion, file },
            {
                onSuccess: () => {
                    toast({
                        title: t("common:success"),
                        description: t("emoji:emotion_uploaded", { emotion: EMOTION_LABELS[emotion] }),
                    });
                    refetchPack();
                },
                onError: (error: any) => {
                    toast({
                        title: t("common:error"),
                        description: error.message,
                        variant: "destructive",
                    });
                },
                onSettled: () => {
                    setUploadingEmotion(null);
                }
            }
        );
    }, [packId, isNewPack, uploadEmotion, t, toast, refetchPack]);

    // Reset emotion handler
    const handleResetEmotion = useCallback((emotion: string) => {
        if (!packId || isNewPack) return;

        Modal.confirm({
            title: t("emoji:reset_emotion"),
            content: t("emoji:reset_emotion_confirm", { emotion: EMOTION_LABELS[emotion] }),
            okText: t("common:confirm"),
            cancelText: t("common:cancel"),
            onOk: () => {
                deleteEmotion(
                    { packId, emotion },
                    {
                        onSuccess: () => {
                            toast({
                                title: t("common:success"),
                                description: t("emoji:emotion_reset"),
                            });
                            refetchPack();
                        },
                        onError: (error: any) => {
                            toast({
                                title: t("common:error"),
                                description: error.message,
                                variant: "destructive",
                            });
                        }
                    }
                );
            }
        });
    }, [packId, isNewPack, deleteEmotion, t, toast, refetchPack]);

    // Share handler
    const handleShare = useCallback((shareType: "public" | "private") => {
        if (!packId || isNewPack) return;

        sharePack(
            { packId, shareType },
            {
                onSuccess: (result) => {
                    toast({
                        title: t("common:success"),
                        description: result.message,
                    });
                    refetchPack();
                },
                onError: (error: any) => {
                    toast({
                        title: t("common:error"),
                        description: error.message,
                        variant: "destructive",
                    });
                }
            }
        );
    }, [packId, isNewPack, sharePack, t, toast, refetchPack]);

    // Loading state
    if (!isNewPack && loadingPack) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Spin size="large" />
            </div>
        );
    }

    return (
        <>
            <PageHead
                title={isNewPack ? "emoji:create_pack" : "emoji:edit_pack"}
                description="emoji:editor_description"
                translateTitle
                translateDescription
            />

            <div className="space-y-4 p-3 sm:space-y-6 sm:p-6">
                {/* Header */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex items-center gap-4">
                        <Button
                            icon={<IconArrowLeft />}
                            onClick={() => navigate("/emoji-packs")}
                        >
                            {t("common:back")}
                        </Button>

                        <Title heading={2} className="flex items-center gap-2">
                            <IconEmoji size="large" />
                            {isNewPack ? t("emoji:create_pack") : t("emoji:edit_pack")}
                        </Title>
                    </div>

                    <div className="flex gap-2">
                        {!isNewPack && pack && (
                            <Button
                                icon={<Share2 className="h-4 w-4" />}
                                onClick={() => handleShare(pack.is_public ? "private" : "public")}
                                loading={isSharing}
                            >
                                {pack.is_public ? t("emoji:make_private") : t("emoji:share_public")}
                            </Button>
                        )}

                        <Button
                            theme="solid"
                            icon={<IconSave />}
                            onClick={handleSave}
                            loading={isCreating || isUpdating}
                        >
                            {t("common:save")}
                        </Button>
                    </div>
                </div>

                {/* Info banner for new packs */}
                {isNewPack && (
                    <Banner
                        type="info"
                        description={t("emoji:new_pack_info")}
                    />
                )}

                {/* Form and Grid */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Left: Pack Settings */}
                    <Card className="lg:col-span-1">
                        <Title heading={4} className="mb-4">
                            {t("emoji:pack_settings")}
                        </Title>

                        <Form
                            initValues={initialValues}
                            getFormApi={(api) => setFormApi(api)}
                            labelPosition="top"
                        >
                            <Form.Input
                                field="name"
                                label={t("emoji:pack_name")}
                                placeholder={t("emoji:pack_name_placeholder")}
                                rules={[{ required: true, message: t("emoji:name_required") }]}
                            />

                            <Form.TextArea
                                field="description"
                                label={t("emoji:pack_description")}
                                placeholder={t("emoji:pack_description_placeholder")}
                                maxCount={200}
                            />

                            <Form.Select
                                field="base_pack"
                                label={t("emoji:base_pack")}
                                optionList={BASE_PACK_OPTIONS}
                                disabled={!isNewPack}
                            />

                            <Form.Select
                                field="target_size"
                                label={t("emoji:target_size")}
                                optionList={[
                                    { value: 32, label: "32x32" },
                                    { value: 48, label: "48x48" },
                                    { value: 64, label: "64x64" },
                                    { value: 128, label: "128x128" },
                                ]}
                                disabled={!isNewPack}
                            />
                        </Form>
                    </Card>

                    {/* Right: Emotion Grid */}
                    <Card className="lg:col-span-2">
                        <div className="flex items-center justify-between mb-4">
                            <Title heading={4}>
                                {t("emoji:emotion_grid")}
                            </Title>
                            <Text type="tertiary">
                                {t("emoji:click_to_upload")}
                            </Text>
                        </div>

                        {isNewPack ? (
                            <div className="text-center py-12">
                                <IconEmoji style={{ fontSize: 48 }} className="text-muted-foreground mb-4" />
                                <Text type="tertiary">
                                    {t("emoji:save_first_to_upload")}
                                </Text>
                            </div>
                        ) : (
                            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-7 gap-3">
                                {EMOTION_NAMES.map((emotion) => (
                                    <EmotionCell
                                        key={emotion}
                                        emotion={emotion}
                                        asset={pack?.emotions?.[emotion]}
                                        onUpload={(file) => handleUploadEmotion(emotion, file)}
                                        onReset={() => handleResetEmotion(emotion)}
                                        isUploading={uploadingEmotion === emotion}
                                        targetSize={pack?.target_size || 64}
                                    />
                                ))}
                            </div>
                        )}
                    </Card>
                </div>
            </div>
        </>
    );
}

export const EmojiPackEditorPage = memo(EmojiPackEditorComponent);
