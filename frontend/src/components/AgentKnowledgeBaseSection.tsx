/**
 * AgentKnowledgeBaseSection - Display and manage linked Knowledge Bases for an Agent
 * Similar to ListReminders section
 */

import { memo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
    Button,
    Card,
    Modal,
    Toast,
    Empty,
    Skeleton,
    Checkbox,
    Typography,
} from "@douyinfe/semi-ui";
import {
    IconPlus,
    IconDelete,
    IconBox,
    IconLink,
    IconEyeOpened,
} from "@douyinfe/semi-icons";
import {
    useAgentKnowledgeBases,
    useUpdateAgentKnowledgeBases,
    useKnowledgeBases,
} from "@/queries/knowledge-bases-queries";

const { Text } = Typography;

interface AgentKnowledgeBaseSectionProps {
    agentId: string;
}

const AgentKnowledgeBaseSectionComponent = ({
    agentId,
}: AgentKnowledgeBaseSectionProps) => {
    const navigate = useNavigate();
    const { t } = useTranslation("knowledge");
    const [isLinkModalOpen, setIsLinkModalOpen] = useState(false);
    const [selectedKBs, setSelectedKBs] = useState<string[]>([]);

    // Fetch linked KBs for this agent
    const {
        data: linkedKBs,
        isLoading: isLoadingLinked,
        refetch: refetchLinked,
    } = useAgentKnowledgeBases(agentId);

    // Fetch all available KBs for linking
    const { data: allKBsResponse, isLoading: isLoadingAll } = useKnowledgeBases();

    // Mutation for updating linked KBs
    const { mutateAsync: updateLinkedKBs, isPending: isUpdating } =
        useUpdateAgentKnowledgeBases(agentId);

    const allKBs = allKBsResponse?.items ?? [];

    // Handle opening link modal
    const handleOpenLinkModal = () => {
        // Pre-select currently linked KBs
        setSelectedKBs(linkedKBs?.map((kb) => kb.id) ?? []);
        setIsLinkModalOpen(true);
    };

    // Handle saving linked KBs
    const handleSaveLinkedKBs = async () => {
        try {
            await updateLinkedKBs(selectedKBs);
            await refetchLinked();
            setIsLinkModalOpen(false);
            Toast.success(t("kbs_linked_success", "Đã cập nhật kho tri thức"));
        } catch (error) {
            console.error("Error updating linked KBs:", error);
            Toast.error(t("kbs_linked_error", "Không thể cập nhật kho tri thức"));
        }
    };

    // Handle unlinking a single KB
    const handleUnlinkKB = (kbId: string) => {
        Modal.confirm({
            title: t("unlink_kb_title", "Huỷ liên kết Kho Tri Thức"),
            content: t("unlink_kb_confirm", "Bạn có chắc muốn huỷ liên kết?"),
            okText: t("unlink", "Huỷ liên kết"),
            cancelText: t("cancel", "Hủy"),
            onOk: async () => {
                try {
                    const newLinkedIds = (linkedKBs ?? [])
                        .filter((kb) => kb.id !== kbId)
                        .map((kb) => kb.id);
                    await updateLinkedKBs(newLinkedIds);
                    await refetchLinked();
                    Toast.success(t("kb_unlinked", "Đã huỷ liên kết"));
                } catch (error) {
                    console.error("Error unlinking KB:", error);
                    Toast.error(t("unlink_error", "Không thể huỷ liên kết"));
                }
            },
        });
    };

    // Toggle KB selection
    const toggleKBSelection = (kbId: string) => {
        setSelectedKBs((prev) =>
            prev.includes(kbId) ? prev.filter((id) => id !== kbId) : [...prev, kbId]
        );
    };

    return (
        <div className="space-y-2">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h3 className="font-semibold text-sm flex items-center gap-2">
                    <IconBox className="text-orange-500" />
                    {t("knowledge_bases", "Kho Tri Thức")}
                    {linkedKBs && linkedKBs.length > 0 && (
                        <span className="text-xs text-gray-500">({linkedKBs.length})</span>
                    )}
                </h3>
                <Button
                    icon={<IconLink />}
                    theme="light"
                    onClick={handleOpenLinkModal}
                >
                    {t("link_kb", "Liên kết KB")}
                </Button>
            </div>

            {/* Linked KBs List */}
            {isLoadingLinked ? (
                <Skeleton.Image className="h-24 w-full" />
            ) : linkedKBs && linkedKBs.length > 0 ? (
                <Card bodyStyle={{ padding: 0 }}>
                    <div className="divide-y divide-gray-100">
                        {linkedKBs.map((kb) => (
                            <div
                                key={kb.id}
                                className="flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center">
                                        <IconBox className="text-orange-600" />
                                    </div>
                                    <div>
                                        <Text strong>{kb.name}</Text>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Button
                                        icon={<IconEyeOpened />}
                                        theme="borderless"
                                        size="small"
                                        onClick={() => navigate(`/knowledge/${kb.id}`)}
                                    />
                                    <Button
                                        icon={<IconDelete />}
                                        theme="borderless"
                                        type="danger"
                                        size="small"
                                        onClick={() => handleUnlinkKB(kb.id)}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </Card>
            ) : (
                <Card>
                    <Empty
                        image={<IconBox className="text-4xl text-gray-300" />}
                        description={
                            <Text type="tertiary">
                                {t("no_linked_kbs", "Chưa có kho tri thức nào được liên kết")}
                            </Text>
                        }
                    >
                        <Button
                            icon={<IconPlus />}
                            theme="solid"
                            onClick={handleOpenLinkModal}
                        >
                            {t("link_first_kb", "Liên kết Kho Tri Thức")}
                        </Button>
                    </Empty>
                </Card>
            )}

            {/* Link KB Modal */}
            <Modal
                title={
                    <div className="flex items-center gap-2">
                        <IconLink />
                        {t("link_kbs_title", "Liên kết Kho Tri Thức")}
                    </div>
                }
                visible={isLinkModalOpen}
                onOk={handleSaveLinkedKBs}
                onCancel={() => setIsLinkModalOpen(false)}
                confirmLoading={isUpdating}
                okText={t("save", "Lưu")}
                cancelText={t("cancel", "Hủy")}
                width={500}
            >
                {isLoadingAll ? (
                    <Skeleton.Image className="h-48 w-full" />
                ) : allKBs.length === 0 ? (
                    <Empty
                        description={
                            <div className="text-center">
                                <Text type="tertiary">
                                    {t("no_kbs_available", "Chưa có Kho Tri Thức nào")}
                                </Text>
                                <div className="mt-2">
                                    <Button
                                        icon={<IconPlus />}
                                        theme="light"
                                        onClick={() => navigate("/knowledge")}
                                    >
                                        {t("create_kb", "Tạo Kho Tri Thức")}
                                    </Button>
                                </div>
                            </div>
                        }
                    />
                ) : (
                    <div className="space-y-2 max-h-80 overflow-y-auto">
                        <Text type="tertiary" size="small">
                            {t("select_kbs_to_link", "Chọn các kho tri thức để liên kết với Agent:")}
                        </Text>
                        {allKBs.map((kb) => (
                            <div
                                key={kb.id}
                                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${selectedKBs.includes(kb.id)
                                    ? "border-blue-500 bg-blue-50"
                                    : "border-gray-200 hover:border-blue-300"
                                    }`}
                                onClick={() => toggleKBSelection(kb.id)}
                            >
                                <Checkbox
                                    checked={selectedKBs.includes(kb.id)}
                                    onChange={() => toggleKBSelection(kb.id)}
                                />
                                <div className="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center">
                                    <IconBox className="text-orange-600" />
                                </div>
                                <div className="flex-1">
                                    <Text strong>{kb.name}</Text>
                                    {kb.description && (
                                        <Text type="tertiary" size="small" className="block">
                                            {kb.description}
                                        </Text>
                                    )}
                                </div>
                                <Text type="tertiary" size="small">
                                    {kb.entry_count ?? 0} entries
                                </Text>
                            </div>
                        ))}
                    </div>
                )}
            </Modal>
        </div>
    );
};

export const AgentKnowledgeBaseSection = memo(AgentKnowledgeBaseSectionComponent);
