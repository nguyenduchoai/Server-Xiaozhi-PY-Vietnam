/**
 * Emoji Pack Management Page
 * Lists user's emoji packs and community packs
 */
import { useState, useCallback, memo } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
    Button,
    Card,
    Typography,
    Spin,
    Empty,
    Tag,
    Tabs,
    TabPane,
    Skeleton,
    Modal
} from "@douyinfe/semi-ui";
import {
    IconPlus,
    IconEmoji,
    IconGlobe
} from "@douyinfe/semi-icons";
import { Grid3X3 } from "lucide-react";

import { PageHead } from "@/components";
import { useToast } from "@/hooks/use-toast";
import {
    useEmojiPackList,
    useCommunityEmojiPacks,
    useDeleteEmojiPack,
    useCloneEmojiPack
} from "@/queries/emoji-packs";

const { Title, Text } = Typography;

// Emotion grid preview component
const EmotionGridPreview = memo(({ packId: _packId }: { packId: string }) => {
    return (
        <div className="grid grid-cols-3 gap-1 p-2 bg-muted/30 rounded">
            {Array.from({ length: 9 }).map((_, i) => (
                <div
                    key={i}
                    className="w-8 h-8 bg-muted rounded flex items-center justify-center text-lg"
                >
                    {["😐", "😊", "😢", "😠", "😍", "😎", "🤔", "😴", "😂"][i]}
                </div>
            ))}
        </div>
    );
});

// Pack card component
interface EmojiPackCardProps {
    pack: {
        id: string;
        name: string;
        description?: string;
        base_pack: string;
        emotion_count: number;
        is_public: boolean;
        is_featured: boolean;
        download_count: number;
        created_at: string;
        author?: { name: string };
    };
    onEdit?: (id: string) => void;
    onDelete?: (id: string) => void;
    onClone?: (id: string) => void;
    isOwner?: boolean;
}

const EmojiPackCard = memo(({
    pack,
    onEdit,
    onDelete,
    onClone,
    isOwner = false
}: EmojiPackCardProps) => {
    const { t } = useTranslation(["emoji", "common"]);

    const handleCardClick = () => {
        if (isOwner && onEdit) {
            onEdit(pack.id);
        }
    };

    return (
        <div
            className="cursor-pointer transition-all hover:shadow-md rounded-lg"
            onClick={handleCardClick}
        >
            <Card className="h-full" bodyStyle={{ padding: 16 }}>
                {/* Header with badges */}
                <div className="flex items-start justify-between gap-2 mb-3">
                    <div className="flex items-center gap-2 flex-wrap">
                        <Tag color="blue" type="solid" size="small">
                            {pack.base_pack}
                        </Tag>
                        {pack.is_public && (
                            <Tag color="green" size="small">
                                <IconGlobe size="small" className="mr-1" />
                                {t("emoji:public")}
                            </Tag>
                        )}
                        {pack.is_featured && (
                            <Tag color="yellow" size="small">
                                {t("emoji:featured")}
                            </Tag>
                        )}
                    </div>

                    {/* Download count for community packs */}
                    {!isOwner && pack.download_count > 0 && (
                        <Text type="tertiary" size="small">
                            {pack.download_count} {t("emoji:downloads")}
                        </Text>
                    )}
                </div>

                {/* Pack name */}
                <Title heading={5} className="mb-2 line-clamp-1">
                    {pack.name}
                </Title>

                {/* Description */}
                {pack.description && (
                    <Text type="tertiary" className="block mb-3 line-clamp-2 text-sm">
                        {pack.description}
                    </Text>
                )}

                {/* Preview grid */}
                <EmotionGridPreview packId={pack.id} />

                {/* Footer */}
                <div className="flex items-center justify-between mt-3 pt-3 border-t">
                    <Text type="tertiary" size="small">
                        {pack.emotion_count} {t("emoji:emotions")}
                    </Text>

                    <div className="flex gap-2">
                        {isOwner ? (
                            <>
                                <Button
                                    size="small"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onEdit?.(pack.id);
                                    }}
                                >
                                    {t("common:edit")}
                                </Button>
                                <Button
                                    size="small"
                                    type="danger"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onDelete?.(pack.id);
                                    }}
                                >
                                    {t("common:delete")}
                                </Button>
                            </>
                        ) : (
                            <Button
                                size="small"
                                theme="solid"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onClone?.(pack.id);
                                }}
                            >
                                {t("emoji:clone")}
                            </Button>
                        )}
                    </div>
                </div>
            </Card>
        </div>
    );
});

function EmojiPackPageComponent() {
    const { t } = useTranslation(["emoji", "common"]);
    const navigate = useNavigate();
    const { toast } = useToast();

    const [activeTab, setActiveTab] = useState("my-packs");

    // Queries
    const { data: myPacks, isLoading: loadingMyPacks, refetch: refetchMyPacks } = useEmojiPackList({
        filter: "mine",
        page: 1,
        page_size: 20
    });

    const { data: communityPacks, isLoading: loadingCommunity } = useCommunityEmojiPacks({
        page: 1,
        page_size: 20
    });

    // Mutations
    const { mutate: deletePack, isPending: isDeleting } = useDeleteEmojiPack();
    const { mutate: clonePack, isPending: isCloning } = useCloneEmojiPack();

    // Handlers
    const handleCreatePack = useCallback(() => {
        navigate("/emoji-packs/new");
    }, [navigate]);

    const handleEditPack = useCallback((packId: string) => {
        navigate(`/emoji-packs/${packId}/edit`);
    }, [navigate]);

    const handleDeletePack = useCallback((packId: string) => {
        Modal.confirm({
            title: t("emoji:delete_pack"),
            content: t("emoji:delete_pack_confirm"),
            okText: t("common:delete"),
            okType: "danger",
            cancelText: t("common:cancel"),
            onOk: () => {
                deletePack(packId, {
                    onSuccess: () => {
                        toast({
                            title: t("common:success"),
                            description: t("emoji:pack_deleted"),
                        });
                        refetchMyPacks();
                    },
                    onError: (error) => {
                        toast({
                            title: t("common:error"),
                            description: error.message,
                            variant: "destructive",
                        });
                    }
                });
            }
        });
    }, [deletePack, t, toast, refetchMyPacks]);

    const handleClonePack = useCallback((packId: string) => {
        clonePack(packId, {
            onSuccess: (data) => {
                toast({
                    title: t("common:success"),
                    description: t("emoji:pack_cloned"),
                });
                navigate(`/emoji-packs/${data.id}/edit`);
            },
            onError: (error) => {
                toast({
                    title: t("common:error"),
                    description: error.message,
                    variant: "destructive",
                });
            }
        });
    }, [clonePack, t, toast, navigate]);

    return (
        <>
            <PageHead
                title="emoji:page_title"
                description="emoji:page_description"
                translateTitle
                translateDescription
            />

            <div className="space-y-4 p-3 sm:space-y-6 sm:p-6">
                {/* Header */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex-1">
                        <Title heading={2} className="flex items-center gap-2">
                            <IconEmoji size="large" />
                            {t("emoji:emoji_packs")}
                        </Title>
                        <Text type="tertiary" className="mt-2 block">
                            {t("emoji:manage_description")}
                        </Text>
                    </div>

                    <Button
                        theme="solid"
                        icon={<IconPlus />}
                        onClick={handleCreatePack}
                    >
                        {t("emoji:create_pack")}
                    </Button>
                </div>

                {/* Tabs */}
                <Tabs activeKey={activeTab} onChange={setActiveTab}>
                    <TabPane
                        tab={
                            <span className="flex items-center gap-2">
                                <Grid3X3 className="h-4 w-4" />
                                {t("emoji:my_packs")}
                            </span>
                        }
                        itemKey="my-packs"
                    >
                        {loadingMyPacks ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mt-4">
                                {Array.from({ length: 4 }).map((_, i) => (
                                    <Skeleton key={i} placeholder={<Skeleton.Image style={{ height: 200 }} />} loading />
                                ))}
                            </div>
                        ) : myPacks?.data?.length ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mt-4">
                                {myPacks.data.map((pack: any) => (
                                    <EmojiPackCard
                                        key={pack.id}
                                        pack={pack}
                                        onEdit={handleEditPack}
                                        onDelete={handleDeletePack}
                                        isOwner
                                    />
                                ))}
                            </div>
                        ) : (
                            <Empty
                                image={<IconEmoji style={{ fontSize: 48 }} />}
                                title={t("emoji:no_packs")}
                                description={t("emoji:no_packs_description")}
                                style={{ padding: 40 }}
                            >
                                <Button onClick={handleCreatePack}>
                                    {t("emoji:create_pack")}
                                </Button>
                            </Empty>
                        )}
                    </TabPane>

                    <TabPane
                        tab={
                            <span className="flex items-center gap-2">
                                <IconGlobe />
                                {t("emoji:community")}
                            </span>
                        }
                        itemKey="community"
                    >
                        {loadingCommunity ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mt-4">
                                {Array.from({ length: 4 }).map((_, i) => (
                                    <Skeleton key={i} placeholder={<Skeleton.Image style={{ height: 200 }} />} loading />
                                ))}
                            </div>
                        ) : communityPacks?.data?.length ? (
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 mt-4">
                                {communityPacks.data.map((pack: any) => (
                                    <EmojiPackCard
                                        key={pack.id}
                                        pack={pack}
                                        onClone={handleClonePack}
                                        isOwner={false}
                                    />
                                ))}
                            </div>
                        ) : (
                            <Empty
                                image={<IconGlobe style={{ fontSize: 48 }} />}
                                title={t("emoji:no_community_packs")}
                                description={t("emoji:no_community_packs_description")}
                                style={{ padding: 40 }}
                            />
                        )}
                    </TabPane>
                </Tabs>
            </div>

            {/* Loading overlay for mutations */}
            {(isDeleting || isCloning) && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <Spin size="large" />
                </div>
            )}
        </>
    );
}

export const EmojiPackPage = memo(EmojiPackPageComponent);
