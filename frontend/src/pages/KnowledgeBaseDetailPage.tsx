/**
 * KnowledgeBaseDetailPage - View and manage entries in a knowledge base
 * 
 * Features:
 * - View KB info (name, description, stats)
 * - List entries with pagination
 * - Add text entry
 * - Upload file (drag-drop)
 * - Upload from URL
 * - Import from Google Sheets
 * - Import CSV
 * - Delete all data
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
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
    Spin,
    Input,
    Upload,
    Tabs,
    TabPane,
    Divider,
} from "@douyinfe/semi-ui";
import {
    IconPlus,
    IconDelete,
    IconArrowLeft,
    IconUpload,
    IconFile,
    IconClock,
    IconLink,
    IconCloud,
    IconClear,
} from "@douyinfe/semi-icons";
import { FileSpreadsheet, FileText } from "lucide-react";

import {
    useKnowledgeBase,
    useKnowledgeEntries,
    useCreateKnowledgeEntry,
    useUploadKnowledgeEntry,
    useDeleteKnowledgeEntry,
    type KnowledgeEntry,
} from "@/queries/knowledge-bases-queries";
import { apiClient } from "@/config/axios-instance";

const { Text, Paragraph } = Typography;

export default function KnowledgeBaseDetailPage() {
    const { t } = useTranslation();
    const { id: kbId } = useParams<{ id: string }>();
    const navigate = useNavigate();

    // States for modals
    const [page, setPage] = useState(1);
    const [addTextModalVisible, setAddTextModalVisible] = useState(false);
    const [uploadModalVisible, setUploadModalVisible] = useState(false);
    const [googleSheetsModalVisible, setGoogleSheetsModalVisible] = useState(false);
    const [csvModalVisible, setCsvModalVisible] = useState(false);
    const [uploadActiveTab, setUploadActiveTab] = useState("file");

    // Upload states
    const [urlValue, setUrlValue] = useState("");
    const [sheetsUrl, setSheetsUrl] = useState("");
    const [sheetName, setSheetName] = useState("Sheet1");
    const [isUploading, setIsUploading] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [isClearingAll, setIsClearingAll] = useState(false);

    // Image upload states for Add Knowledge modal
    // _knowledgeImageFile is kept for future server upload implementation
    const [_knowledgeImageFile, setKnowledgeImageFile] = useState<File | null>(null);
    const [knowledgeImagePreview, setKnowledgeImagePreview] = useState<string>("");
    const [knowledgeImageUrl, setKnowledgeImageUrl] = useState<string>("");
    const [imageUploadMode, setImageUploadMode] = useState<"url" | "file">("url");

    const { data: kb, isLoading: kbLoading, refetch: refetchKb } = useKnowledgeBase(kbId || "");
    const { data: entriesData, isLoading: entriesLoading, refetch } = useKnowledgeEntries(
        kbId || "",
        { page }
    );
    const createMutation = useCreateKnowledgeEntry(kbId || "");
    const uploadMutation = useUploadKnowledgeEntry(kbId || "");
    const deleteMutation = useDeleteKnowledgeEntry(kbId || "");

    // Template download URL - Both use same CSV format
    const templateCsvUrl = "/templates/knowledge-template.csv";
    const templateSheetsUrl = "/templates/knowledge-template.csv"; // Download CSV to import into Sheets

    // Handlers
    const handleAddText = async (values: { title?: string; content: string; image_url?: string }) => {
        try {
            const fullContent = values.title
                ? `# ${values.title}\n\n${values.content}`
                : values.content;

            // Use image URL from state (supports both URL input and file upload preview)
            const finalImageUrl = knowledgeImageUrl || knowledgeImagePreview || values.image_url || "";

            await createMutation.mutateAsync({
                content: fullContent,
                doc_type: "text",
                source: "manual",
                metadata: {
                    title: values.title || "",
                    image_url: finalImageUrl,
                },
            });
            Toast.success(t("knowledge:entry_created", "Đã thêm kiến thức"));

            // Reset states
            setAddTextModalVisible(false);
            setKnowledgeImageFile(null);
            setKnowledgeImagePreview("");
            setKnowledgeImageUrl("");
            setImageUploadMode("url");

            refetch();
        } catch (error) {
            Toast.error(t("knowledge:entry_create_error", "Không thể thêm kiến thức"));
        }
    };

    const handleFileUpload = async (file: File) => {
        try {
            setIsUploading(true);
            await uploadMutation.mutateAsync(file);
            Toast.success(t("knowledge:file_uploaded", "Đã tải lên file"));
            setUploadModalVisible(false);
            refetch();
        } catch (error) {
            Toast.error(t("knowledge:file_upload_error", "Không thể tải lên file"));
        } finally {
            setIsUploading(false);
        }
    };

    const handleUrlUpload = async () => {
        if (!urlValue.trim()) {
            Toast.warning("Vui lòng nhập URL");
            return;
        }
        try {
            setIsUploading(true);
            await apiClient.post(`/knowledge-unified/${kbId}/upload-url`, {
                url: urlValue,
            });
            Toast.success("Đã tải lên từ URL");
            setUrlValue("");
            setUploadModalVisible(false);
            refetch();
        } catch (error) {
            Toast.error("Không thể tải lên từ URL");
        } finally {
            setIsUploading(false);
        }
    };

    const handleGoogleSheetsImport = async () => {
        if (!sheetsUrl.trim()) {
            Toast.warning("Vui lòng nhập URL Google Sheets");
            return;
        }
        try {
            setIsImporting(true);
            await apiClient.post(`/knowledge-unified/${kbId}/import/sheets`, {
                url: sheetsUrl,
                sheet_name: sheetName || "Sheet1",
            });
            Toast.success("Đã đồng bộ dữ liệu từ Google Sheets");
            setSheetsUrl("");
            setSheetName("Sheet1");
            setGoogleSheetsModalVisible(false);
            refetch();
        } catch (error) {
            Toast.error("Không thể nhập từ Google Sheets");
        } finally {
            setIsImporting(false);
        }
    };

    const handleCsvUpload = async (file: File) => {
        try {
            setIsImporting(true);
            const formData = new FormData();
            formData.append("file", file);
            await apiClient.post(`/knowledge-unified/${kbId}/upload`, formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            Toast.success("Đã nhập CSV thành công");
            setCsvModalVisible(false);
            refetch();
        } catch (error) {
            Toast.error("Không thể nhập CSV");
        } finally {
            setIsImporting(false);
        }
    };

    const handleClearAllData = async () => {
        try {
            setIsClearingAll(true);
            await apiClient.delete(`/knowledge-unified/${kbId}/clear`);
            Toast.success("Đã xóa tất cả dữ liệu");
            refetch();
            refetchKb();
        } catch (error) {
            Toast.error("Không thể xóa dữ liệu");
        } finally {
            setIsClearingAll(false);
        }
    };

    const handleDeleteEntry = async (entryId: string) => {
        try {
            await deleteMutation.mutateAsync(entryId);
            Toast.success(t("knowledge:entry_deleted", "Đã xóa entry"));
            refetch();
        } catch (error) {
            Toast.error(t("knowledge:entry_delete_error", "Không thể xóa entry"));
        }
    };

    const columns = [
        {
            title: t("knowledge:content", "Nội dung"),
            dataIndex: "content",
            key: "content",
            render: (content: string) => (
                <Paragraph
                    ellipsis={{ rows: 2, showTooltip: true }}
                    style={{ marginBottom: 0, maxWidth: 500 }}
                >
                    {content}
                </Paragraph>
            ),
        },
        {
            title: t("knowledge:type", "Loại"),
            dataIndex: "doc_type",
            key: "doc_type",
            width: 100,
            render: (type: string) => {
                type TagColor = "blue" | "red" | "cyan" | "green" | "grey";
                const colors: Record<string, TagColor> = {
                    text: "blue",
                    pdf: "red",
                    docx: "cyan",
                    csv: "green",
                    excel: "green",
                };
                return <Tag color={colors[type] || "grey"}>{type?.toUpperCase()}</Tag>;
            },
        },
        {
            title: t("knowledge:source", "Nguồn"),
            dataIndex: "source",
            key: "source",
            width: 150,
            render: (source: string) => (
                <Text type="tertiary" ellipsis={{ showTooltip: true }} style={{ maxWidth: 150 }}>
                    {source}
                </Text>
            ),
        },
        {
            title: t("knowledge:created_at", "Ngày tạo"),
            dataIndex: "created_at",
            key: "created_at",
            width: 150,
            render: (date: string) => {
                const parsedDate = date ? new Date(date) : null;
                const isValid = parsedDate && !isNaN(parsedDate.getTime());
                return (
                    <Text type="tertiary">
                        <IconClock style={{ marginRight: 4 }} />
                        {isValid ? parsedDate.toLocaleDateString("vi-VN") : "-"}
                    </Text>
                );
            },
        },
        {
            title: t("common:actions", "Hành động"),
            key: "actions",
            width: 80,
            render: (_: unknown, record: KnowledgeEntry) => (
                <Popconfirm
                    title={t("knowledge:delete_entry_confirm", "Xóa entry này?")}
                    onConfirm={() => handleDeleteEntry(record.id)}
                >
                    <Button
                        theme="light"
                        type="danger"
                        size="small"
                        icon={<IconDelete />}
                    />
                </Popconfirm>
            ),
        },
    ];

    if (kbLoading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Spin size="large" />
            </div>
        );
    }

    if (!kb) {
        return (
            <div className="p-6">
                <Empty
                    title={t("knowledge:not_found", "Không tìm thấy kho tri thức")}
                    description={t("knowledge:not_found_desc", "Kho tri thức này không tồn tại hoặc đã bị xóa")}
                >
                    <Button onClick={() => navigate("/knowledge")}>
                        {t("common:go_back", "Quay lại")}
                    </Button>
                </Empty>
            </div>
        );
    }

    return (
        <div className="p-6 space-y-6">
            {/* Header Card with Info */}
            <Card title="Giới Thiệu Knowledge"
                headerExtraContent={
                    <Space>
                        <Button
                            icon={<IconUpload />}
                            theme="solid"
                            onClick={() => setUploadModalVisible(true)}
                        >
                            Upload Document
                        </Button>
                        <Button
                            icon={<FileSpreadsheet size={16} />}
                            theme="solid"
                            onClick={() => setCsvModalVisible(true)}
                        >
                            Nhập CSV
                        </Button>
                        <Button
                            icon={<IconLink />}
                            theme="solid"
                            onClick={() => setGoogleSheetsModalVisible(true)}
                        >
                            Nhập từ Google Sheets
                        </Button>
                        <Button
                            icon={<IconPlus />}
                            theme="solid"
                            type="secondary"
                            style={{ background: "#22c55e", borderColor: "#22c55e" }}
                            onClick={() => setAddTextModalVisible(true)}
                        >
                            Thêm Kiến Thức
                        </Button>
                        <Popconfirm
                            title="Xóa tất cả dữ liệu?"
                            content="Hành động này không thể hoàn tác. Tất cả entries sẽ bị xóa vĩnh viễn."
                            onConfirm={handleClearAllData}
                        >
                            <Button
                                icon={<IconClear />}
                                theme="solid"
                                type="danger"
                                loading={isClearingAll}
                            >
                                Xóa Dữ Liệu
                            </Button>
                        </Popconfirm>
                    </Space>
                }
            >
                <div className="flex items-center gap-4 mb-4">
                    <Button
                        theme="borderless"
                        icon={<IconArrowLeft />}
                        onClick={() => navigate("/knowledge")}
                    />
                </div>

                {/* Info Form */}
                <div className="grid grid-cols-2 gap-6 mb-6">
                    <div>
                        <Text strong className="block mb-2">Tên</Text>
                        <Text className="block p-2 bg-gray-50 rounded border border-gray-200">
                            {kb.name}
                        </Text>
                    </div>
                    <div>
                        <Text strong className="block mb-2">Tên Model</Text>
                        <Text className="block p-2 bg-gray-50 rounded border border-gray-200" type="tertiary">
                            {kb.embedding_model || "Default Embedding Model"}
                        </Text>
                    </div>
                </div>
                {kb.description && (
                    <div className="mb-6">
                        <Text strong className="block mb-2">Mô Tả</Text>
                        <Text className="block p-2 bg-gray-50 rounded border border-gray-200" type="tertiary">
                            {kb.description}
                        </Text>
                    </div>
                )}
            </Card>

            {/* Uploaded Documents Section */}
            <Card
                title={
                    <div className="flex items-center gap-2">
                        <IconFile />
                        Tài Liệu Đã Tải Lên
                    </div>
                }
            >
                {entriesData?.items.length === 0 && !entriesLoading ? (
                    <Empty
                        image={<IconCloud style={{ fontSize: 48, color: "#bbb" }} />}
                        title="Chưa có tài liệu nào được tải lên"
                    />
                ) : (
                    <Table
                        columns={columns}
                        dataSource={entriesData?.items || []}
                        loading={entriesLoading}
                        pagination={{
                            currentPage: page,
                            total: entriesData?.total || 0,
                            pageSize: 20,
                            onPageChange: setPage,
                        }}
                        rowKey="id"
                    />
                )}
            </Card>

            {/* ===== MODALS ===== */}

            {/* Add Text Modal - Full Fields */}
            <Modal
                title="Thêm Dữ Liệu Knowledge"
                visible={addTextModalVisible}
                onCancel={() => {
                    setAddTextModalVisible(false);
                    setKnowledgeImageFile(null);
                    setKnowledgeImagePreview("");
                    setKnowledgeImageUrl("");
                    setImageUploadMode("url");
                }}
                footer={null}
                width={650}
            >
                <Form onSubmit={handleAddText}>
                    <Form.Input
                        field="title"
                        label="Tên"
                        placeholder="Tiêu đề kiến thức (tùy chọn)"
                    />
                    <Form.TextArea
                        field="content"
                        label="Nội Dung"
                        placeholder="Nội dung kiến thức"
                        rows={5}
                        rules={[{ required: true, message: "Vui lòng nhập nội dung" }]}
                    />

                    {/* Image Section */}
                    <div className="mb-4">
                        <Text strong className="block mb-2">Ảnh sản phẩm (tùy chọn)</Text>
                        <div className="flex gap-4 mb-2">
                            <Button
                                size="small"
                                theme={imageUploadMode === "url" ? "solid" : "light"}
                                onClick={() => setImageUploadMode("url")}
                            >
                                URL Link
                            </Button>
                            <Button
                                size="small"
                                theme={imageUploadMode === "file" ? "solid" : "light"}
                                onClick={() => setImageUploadMode("file")}
                            >
                                Upload File
                            </Button>
                        </div>

                        {imageUploadMode === "url" ? (
                            <Input
                                value={knowledgeImageUrl}
                                onChange={(val) => {
                                    setKnowledgeImageUrl(val);
                                    setKnowledgeImagePreview(val);
                                }}
                                placeholder="https://example.com/image.jpg"
                            />
                        ) : (
                            <Upload
                                accept="image/jpeg,image/png,image/webp"
                                limit={1}
                                maxSize={500}
                                onSizeError={() => Toast.error("Ảnh tối đa 500KB")}
                                beforeUpload={({ file }) => {
                                    const img = new Image();
                                    img.onload = () => {
                                        if (img.width > 800 || img.height > 800) {
                                            Toast.error("Ảnh tối đa 800x800 pixels");
                                            return;
                                        }
                                        setKnowledgeImageFile(file.fileInstance as File);
                                        setKnowledgeImagePreview(URL.createObjectURL(file.fileInstance as File));
                                    };
                                    img.src = URL.createObjectURL(file.fileInstance as File);
                                    return false; // Prevent auto upload
                                }}
                                onRemove={() => {
                                    setKnowledgeImageFile(null);
                                    setKnowledgeImagePreview("");
                                }}
                            >
                                <Button icon={<IconUpload />} theme="light">
                                    Chọn ảnh (max 500KB, 800x800)
                                </Button>
                            </Upload>
                        )}

                        {/* Preview */}
                        {knowledgeImagePreview && (
                            <div className="mt-3 relative inline-block">
                                <img
                                    src={knowledgeImagePreview}
                                    alt="Preview"
                                    className="max-w-[200px] max-h-[200px] rounded border object-cover"
                                    onError={() => setKnowledgeImagePreview("")}
                                />
                                <Button
                                    size="small"
                                    type="danger"
                                    theme="solid"
                                    className="absolute top-1 right-1"
                                    icon={<IconDelete />}
                                    onClick={() => {
                                        setKnowledgeImagePreview("");
                                        setKnowledgeImageUrl("");
                                        setKnowledgeImageFile(null);
                                    }}
                                />
                            </div>
                        )}

                        <Text type="tertiary" size="small" className="block mt-2">
                            💡 Hình ảnh sẽ được hiển thị cùng với nội dung khi trả lời (JPEG, PNG, WebP)
                        </Text>
                    </div>

                    {/* Hidden field for form */}
                    <Form.Input
                        field="image_url"
                        style={{ display: "none" }}
                        initValue={knowledgeImageUrl || knowledgeImagePreview}
                    />

                    <div className="flex justify-end gap-2 mt-4">
                        <Button onClick={() => {
                            setAddTextModalVisible(false);
                            setKnowledgeImageFile(null);
                            setKnowledgeImagePreview("");
                            setKnowledgeImageUrl("");
                        }}>
                            Hủy
                        </Button>
                        <Button
                            theme="solid"
                            type="primary"
                            htmlType="submit"
                            loading={createMutation.isPending}
                        >
                            Tạo
                        </Button>
                    </div>
                </Form>
            </Modal>

            {/* Upload Document Modal with Tabs */}
            <Modal
                title="Tải Lên Tài Liệu"
                visible={uploadModalVisible}
                onCancel={() => setUploadModalVisible(false)}
                footer={null}
                width={500}
            >
                <Tabs activeKey={uploadActiveTab} onChange={setUploadActiveTab}>
                    <TabPane
                        tab={<span><IconFile style={{ marginRight: 8 }} />Tải Lên File</span>}
                        itemKey="file"
                    >
                        <div className="py-4">
                            <Upload
                                draggable
                                action=""
                                accept=".txt,.md,.pdf"
                                showUploadList={false}
                                customRequest={({ file }) => {
                                    handleFileUpload(file.fileInstance as File);
                                }}
                            >
                                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
                                    <IconCloud style={{ fontSize: 48, color: "#aaa", marginBottom: 16 }} />
                                    <Text className="block mb-2">Kéo và thả file vào đây</Text>
                                    <Button>Chọn file</Button>
                                    <Text type="tertiary" className="block mt-2" size="small">
                                        Định dạng hỗ trợ: TXT, MD, PDF (tối đa 10MB)
                                    </Text>
                                </div>
                            </Upload>
                        </div>
                        <div className="flex justify-end gap-2">
                            <Button onClick={() => setUploadModalVisible(false)}>Hủy</Button>
                            <Button theme="solid" type="primary" loading={isUploading}>
                                Tải Lên
                            </Button>
                        </div>
                    </TabPane>
                    <TabPane
                        tab={<span><IconLink style={{ marginRight: 8 }} />Tải Lên URL</span>}
                        itemKey="url"
                    >
                        <div className="py-4">
                            <Text strong className="block mb-2">URL</Text>
                            <Input
                                placeholder="https://example.com/document"
                                value={urlValue}
                                onChange={setUrlValue}
                            />
                            <Text type="tertiary" size="small" className="block mt-2">
                                💡 Nhập URL để tải và chia nhỏ nội dung
                            </Text>
                        </div>
                        <div className="flex justify-end gap-2">
                            <Button onClick={() => setUploadModalVisible(false)}>Hủy</Button>
                            <Button
                                theme="solid"
                                type="primary"
                                onClick={handleUrlUpload}
                                loading={isUploading}
                            >
                                Tải Lên
                            </Button>
                        </div>
                    </TabPane>
                </Tabs>
            </Modal>

            {/* Google Sheets Import Modal */}
            <Modal
                title="Nhập Từ Google Sheets"
                visible={googleSheetsModalVisible}
                onCancel={() => setGoogleSheetsModalVisible(false)}
                footer={null}
                width={500}
            >
                <div className="p-4 bg-blue-50 rounded-lg mb-4 flex gap-3">
                    <FileSpreadsheet size={24} className="text-blue-500 flex-shrink-0" />
                    <div>
                        <Text strong>Nhập từ Google Sheets</Text>
                        <Text type="tertiary" size="small" className="block">
                            Đồng bộ dữ liệu từ URL Google Sheets. Dữ liệu cần có cột: <strong>title</strong>, <strong>content</strong>, <strong>image_url</strong>
                        </Text>
                        <div className="mt-2">
                            <a
                                href={templateSheetsUrl}
                                download="knowledge-template.csv"
                                className="text-blue-600 hover:underline text-sm"
                            >
                                📥 Tải file mẫu CSV (để mở trong Excel/Sheets)
                            </a>
                        </div>
                    </div>
                </div>

                <div className="mb-4">
                    <Text strong className="block mb-2">URL</Text>
                    <Input
                        placeholder="https://example.com/document"
                        value={sheetsUrl}
                        onChange={setSheetsUrl}
                    />
                    <Text type="tertiary" size="small" className="block mt-1">
                        💡 Nhập URL đầy đủ của Google Sheets hoặc chỉ ID của sheet
                    </Text>
                </div>

                <div className="mb-4">
                    <Text strong className="block mb-2">Tên Tab Sheet</Text>
                    <Input
                        placeholder="Sheet1"
                        value={sheetName}
                        onChange={setSheetName}
                    />
                    <Text type="tertiary" size="small" className="block mt-1">
                        💡 Tên của tab/sheet cụ thể để Đồng bộ dữ liệu
                    </Text>
                </div>

                <Divider />
                <div className="flex justify-end gap-2">
                    <Button onClick={() => setGoogleSheetsModalVisible(false)}>Hủy</Button>
                    <Button
                        theme="solid"
                        type="primary"
                        icon={<IconCloud />}
                        onClick={handleGoogleSheetsImport}
                        loading={isImporting}
                    >
                        Đồng Bộ Dữ Liệu
                    </Button>
                </div>
            </Modal>

            {/* CSV Import Modal */}
            <Modal
                title="Nhập CSV"
                visible={csvModalVisible}
                onCancel={() => setCsvModalVisible(false)}
                footer={null}
                width={500}
            >
                <div className="py-4">
                    <Upload
                        draggable
                        action=""
                        accept=".csv"
                        showUploadList={false}
                        customRequest={({ file }) => {
                            handleCsvUpload(file.fileInstance as File);
                        }}
                    >
                        <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
                            <FileText size={48} style={{ color: "#aaa", marginBottom: 16, display: "inline-block" }} />
                            <Text className="block mb-2">Kéo và thả file CSV vào đây</Text>
                            <Button>Chọn file CSV</Button>
                            <Text type="tertiary" className="block mt-2" size="small">
                                Định dạng hỗ trợ: CSV (tối đa 10MB)
                            </Text>
                        </div>
                    </Upload>
                </div>
                <div className="flex justify-between items-center gap-2">
                    <a
                        href={templateCsvUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline text-sm"
                    >
                        📄 Tải file CSV mẫu
                    </a>
                    <div className="flex gap-2">
                        <Button onClick={() => setCsvModalVisible(false)}>Hủy</Button>
                        <Button theme="solid" type="primary" loading={isImporting}>
                            Nhập
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
