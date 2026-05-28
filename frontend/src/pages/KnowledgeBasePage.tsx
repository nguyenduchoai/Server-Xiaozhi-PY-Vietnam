/**
 * KnowledgeBasePage - List and manage independent knowledge bases
 * 
 * Features:
 * - List all user's knowledge bases with entry/agent counts
 * - Create new knowledge base
 * - Delete knowledge base
 * - Navigate to detail page
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
    Card,
    Table,
    Button,
    Modal,
    Form,
    Toast,
    Typography,
    Empty,
    Popconfirm,
    Space,
    Tag,
} from "@douyinfe/semi-ui";
import {
    IconPlus,
    IconDelete,
    IconFile,
    IconUser,
} from "@douyinfe/semi-icons";

import {
    useKnowledgeBases,
    useCreateKnowledgeBase,
    useDeleteKnowledgeBase,
    type KnowledgeBase,
} from "@/queries/knowledge-bases-queries";

const { Title, Text } = Typography;

export default function KnowledgeBasePage() {
    const { t } = useTranslation();
    const navigate = useNavigate();

    const [page, setPage] = useState(1);
    const [createModalVisible, setCreateModalVisible] = useState(false);

    const { data, isLoading, refetch } = useKnowledgeBases({ page });
    const createMutation = useCreateKnowledgeBase();
    const deleteMutation = useDeleteKnowledgeBase();

    const handleCreate = async (values: { name: string; description?: string }) => {
        try {
            await createMutation.mutateAsync(values);
            Toast.success(t("knowledge:create_success", "Tạo kho tri thức thành công"));
            setCreateModalVisible(false);
            refetch();
        } catch (error) {
            Toast.error(t("knowledge:create_error", "Không thể tạo kho tri thức"));
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await deleteMutation.mutateAsync(id);
            Toast.success(t("knowledge:delete_success", "Đã xóa kho tri thức"));
            refetch();
        } catch (error) {
            Toast.error(t("knowledge:delete_error", "Không thể xóa kho tri thức"));
        }
    };

    const columns = [
        {
            title: t("knowledge:name", "Tên"),
            dataIndex: "name",
            key: "name",
            render: (name: string, record: KnowledgeBase) => (
                <Button
                    theme="borderless"
                    onClick={() => navigate(`/knowledge/${record.id}`)}
                    style={{ padding: 0, height: "auto" }}
                >
                    <Text strong>{name}</Text>
                </Button>
            ),
        },
        {
            title: t("knowledge:description", "Mô tả"),
            dataIndex: "description",
            key: "description",
            render: (desc: string | null) => (
                <Text type="tertiary" ellipsis={{ showTooltip: true }} style={{ maxWidth: 300 }}>
                    {desc || "-"}
                </Text>
            ),
        },
        {
            title: t("knowledge:entries", "Entries"),
            dataIndex: "entry_count",
            key: "entry_count",
            width: 100,
            render: (count: number) => (
                <Tag color="blue" prefixIcon={<IconFile />}>
                    {count}
                </Tag>
            ),
        },
        {
            title: t("knowledge:agents", "Agents"),
            dataIndex: "agent_count",
            key: "agent_count",
            width: 100,
            render: (count: number) => (
                <Tag color="green" prefixIcon={<IconUser />}>
                    {count}
                </Tag>
            ),
        },
        {
            title: t("common:actions", "Hành động"),
            key: "actions",
            width: 120,
            render: (_: unknown, record: KnowledgeBase) => (
                <Space>
                    <Button
                        theme="light"
                        size="small"
                        onClick={() => navigate(`/knowledge/${record.id}`)}
                    >
                        {t("common:view", "Xem")}
                    </Button>
                    <Popconfirm
                        title={t("knowledge:delete_confirm", "Xác nhận xóa kho tri thức này?")}
                        onConfirm={() => handleDelete(record.id)}
                    >
                        <Button
                            theme="light"
                            type="danger"
                            size="small"
                            icon={<IconDelete />}
                        />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div className="p-6">
            <Card>
                <div className="flex justify-between items-center mb-6">
                    <Title heading={3}>
                        {t("knowledge:page_title", "📚 Kho Tri Thức")}
                    </Title>
                    <Button
                        theme="solid"
                        type="primary"
                        icon={<IconPlus />}
                        onClick={() => setCreateModalVisible(true)}
                    >
                        {t("knowledge:create", "Tạo mới")}
                    </Button>
                </div>

                {data?.items.length === 0 && !isLoading ? (
                    <Empty
                        title={t("knowledge:empty_title", "Chưa có kho tri thức nào")}
                        description={t(
                            "knowledge:empty_description",
                            "Tạo kho tri thức để lưu trữ và chia sẻ kiến thức giữa các Agent"
                        )}
                    >
                        <Button
                            theme="solid"
                            type="primary"
                            onClick={() => setCreateModalVisible(true)}
                        >
                            {t("knowledge:create_first", "Tạo kho tri thức đầu tiên")}
                        </Button>
                    </Empty>
                ) : (
                    <Table
                        columns={columns}
                        dataSource={data?.items || []}
                        loading={isLoading}
                        pagination={{
                            currentPage: page,
                            total: data?.total || 0,
                            pageSize: 20,
                            onPageChange: setPage,
                        }}
                        rowKey="id"
                    />
                )}
            </Card>

            {/* Create Modal */}
            <Modal
                title={t("knowledge:create_title", "Tạo Kho Tri Thức Mới")}
                visible={createModalVisible}
                onCancel={() => setCreateModalVisible(false)}
                footer={null}
                width={500}
            >
                <Form onSubmit={handleCreate}>
                    <Form.Input
                        field="name"
                        label={t("knowledge:name_label", "Tên kho tri thức")}
                        placeholder={t("knowledge:name_placeholder", "VD: Company Wiki")}
                        rules={[{ required: true, message: t("validation:required") }]}
                    />
                    <Form.TextArea
                        field="description"
                        label={t("knowledge:description_label", "Mô tả (tùy chọn)")}
                        placeholder={t(
                            "knowledge:description_placeholder",
                            "Mô tả ngắn về nội dung kho tri thức"
                        )}
                        rows={3}
                    />
                    <div className="flex justify-end gap-2 mt-4">
                        <Button onClick={() => setCreateModalVisible(false)}>
                            {t("common:cancel", "Hủy")}
                        </Button>
                        <Button
                            theme="solid"
                            type="primary"
                            htmlType="submit"
                            loading={createMutation.isPending}
                        >
                            {t("knowledge:create", "Tạo mới")}
                        </Button>
                    </div>
                </Form>
            </Modal>
        </div>
    );
}
