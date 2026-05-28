/**
 * ServerConfigPage - Cấu hình Server Endpoints
 * Quản lý các server endpoints cho thiết bị kết nối
 * 
 * Refactored to use Semi Design for UI consistency
 */

import { useState } from "react";
import {
    Card,
    Typography,
    Button,
    Table,
    Tag,
    Modal,
    Form,
    Empty,
    Spin,
    Popconfirm,
    Toast,
    Space,
} from "@douyinfe/semi-ui";
import {
    IconPlus,
    IconEdit,
    IconDelete,
    IconRefresh,
    IconServer,
    IconLink,
    IconWifi,
} from "@douyinfe/semi-icons";
import { Server, Globe } from "lucide-react";

import {
    useServers,
    useCreateServer,
    useUpdateServer,
    useDeleteServer,
    type ServerConfig,
} from "@/queries/server-queries";

const { Title, Text } = Typography;

// Form initial state
const INITIAL_FORM = {
    name: "",
    description: "",
    websocket_url: "",
    api_url: "",
    mqtt_host: "",
    mqtt_port: 1883,
    region: "",
};

// Region options
const REGION_OPTIONS = [
    { value: "VN", label: "🇻🇳 Việt Nam" },
    { value: "SG", label: "🇸🇬 Singapore" },
    { value: "US", label: "🇺🇸 Mỹ" },
    { value: "EU", label: "🇪🇺 Châu Âu" },
];

export default function ServerConfigPage() {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingServer, setEditingServer] = useState<ServerConfig | null>(null);
    const [formData, setFormData] = useState(INITIAL_FORM);

    // Queries
    const { data: servers, isLoading, refetch } = useServers();

    // Mutations
    const createMutation = useCreateServer();
    const updateMutation = useUpdateServer();
    const deleteMutation = useDeleteServer();

    // Open create modal
    const handleCreate = () => {
        setFormData(INITIAL_FORM);
        setEditingServer(null);
        setIsModalOpen(true);
    };

    // Open edit modal
    const handleEdit = (server: ServerConfig) => {
        setFormData({
            name: server.name,
            description: server.description || "",
            websocket_url: server.websocket_url,
            api_url: server.api_url,
            mqtt_host: server.mqtt_host || "",
            mqtt_port: server.mqtt_port,
            region: server.region || "",
        });
        setEditingServer(server);
        setIsModalOpen(true);
    };

    // Submit form
    const handleSubmit = async () => {
        try {
            if (editingServer) {
                await updateMutation.mutateAsync({
                    serverId: editingServer.id,
                    data: formData,
                });
                Toast.success("Đã cập nhật server");
            } else {
                await createMutation.mutateAsync({
                    ...formData,
                    mqtt_port: formData.mqtt_port || 1883,
                });
                Toast.success("Đã tạo server mới");
            }
            setIsModalOpen(false);
            setFormData(INITIAL_FORM);
            setEditingServer(null);
        } catch {
            Toast.error("Không thể lưu server");
        }
    };

    // Delete server
    const handleDelete = async (server: ServerConfig) => {
        try {
            await deleteMutation.mutateAsync(server.id);
            Toast.success("Đã xóa server");
        } catch {
            Toast.error("Không thể xóa server");
        }
    };

    // Table columns
    const columns = [
        {
            title: "Server",
            dataIndex: "name",
            key: "name",
            render: (name: string, record: ServerConfig) => (
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${record.is_active ? 'bg-green-100' : 'bg-gray-100'}`}>
                        <Globe size={20} className={record.is_active ? 'text-green-600' : 'text-gray-400'} />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <Text strong>{name}</Text>
                            {record.is_default && (
                                <Tag color="blue" size="small">Mặc định</Tag>
                            )}
                        </div>
                        <Text type="tertiary" size="small">
                            {record.description || "Không có mô tả"}
                        </Text>
                    </div>
                </div>
            ),
        },
        {
            title: "WebSocket URL",
            dataIndex: "websocket_url",
            key: "websocket_url",
            render: (url: string) => (
                <Text copyable={{ content: url }} size="small" style={{ fontFamily: 'monospace' }}>
                    {url}
                </Text>
            ),
        },
        {
            title: "MQTT",
            key: "mqtt",
            render: (_: any, record: ServerConfig) => (
                <Text size="small" style={{ fontFamily: 'monospace' }}>
                    {record.mqtt_host || "N/A"}:{record.mqtt_port}
                </Text>
            ),
        },
        {
            title: "Khu vực",
            dataIndex: "region",
            key: "region",
            render: (region: string) => {
                const regionOption = REGION_OPTIONS.find(r => r.value === region);
                return region ? (
                    <Tag color="light-blue">{regionOption?.label || region}</Tag>
                ) : (
                    <Text type="tertiary">-</Text>
                );
            },
        },
        {
            title: "Trạng thái",
            dataIndex: "is_active",
            key: "is_active",
            render: (active: boolean) => (
                <Tag color={active ? "green" : "grey"}>
                    {active ? "Active" : "Inactive"}
                </Tag>
            ),
        },
        {
            title: "Thao tác",
            key: "actions",
            render: (_: any, record: ServerConfig) => (
                <Space>
                    <Button
                        icon={<IconEdit />}
                        type="tertiary"
                        onClick={() => handleEdit(record)}
                    />
                    {!record.is_default && (
                        <Popconfirm
                            title="Xác nhận xóa"
                            content={`Bạn có chắc muốn xóa server "${record.name}"?`}
                            onConfirm={() => handleDelete(record)}
                        >
                            <Button
                                icon={<IconDelete />}
                                type="danger"
                            />
                        </Popconfirm>
                    )}
                </Space>
            ),
        },
    ];

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-96">
                <Spin size="large" tip="Đang tải danh sách server..." />
            </div>
        );
    }

    return (
        <div className="space-y-6 p-6">
            {/* Header */}
            <div className="flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <div className="p-3 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500">
                        <Server size={28} className="text-white" />
                    </div>
                    <div>
                        <Title heading={3} style={{ margin: 0 }}>
                            Cấu hình Server
                        </Title>
                        <Text type="secondary">
                            Quản lý các server endpoints cho thiết bị kết nối
                        </Text>
                    </div>
                </div>

                <Space>
                    <Button
                        icon={<IconRefresh />}
                        onClick={() => refetch()}
                    >
                        Làm mới
                    </Button>
                    <Button
                        icon={<IconPlus />}
                        theme="solid"
                        onClick={handleCreate}
                    >
                        Thêm Server
                    </Button>
                </Space>
            </div>

            {/* Server Table */}
            <Card bodyStyle={{ padding: 0 }}>
                {servers?.length === 0 ? (
                    <Empty
                        title="Chưa có server nào"
                        description="Thêm server để thiết bị có thể kết nối"
                        style={{ padding: 60 }}
                    >
                        <Button icon={<IconPlus />} theme="solid" onClick={handleCreate}>
                            Thêm Server
                        </Button>
                    </Empty>
                ) : (
                    <Table
                        columns={columns}
                        dataSource={servers}
                        rowKey="id"
                        pagination={false}
                    />
                )}
            </Card>

            {/* Create/Edit Modal */}
            <Modal
                title={
                    <div className="flex items-center gap-2">
                        <IconServer />
                        {editingServer ? "Cập nhật Server" : "Thêm Server mới"}
                    </div>
                }
                visible={isModalOpen}
                onOk={handleSubmit}
                onCancel={() => {
                    setIsModalOpen(false);
                    setFormData(INITIAL_FORM);
                    setEditingServer(null);
                }}
                okText={editingServer ? "Cập nhật" : "Tạo Server"}
                cancelText="Hủy"
                confirmLoading={createMutation.isPending || updateMutation.isPending}
                okButtonProps={{
                    disabled: !formData.name || !formData.websocket_url || !formData.api_url,
                }}
            >
                <Form layout="vertical" style={{ paddingTop: 16 }}>
                    <Form.Input
                        field="name"
                        label="Tên Server"
                        placeholder="Production Vietnam"
                        initValue={formData.name}
                        onChange={(value) => setFormData(d => ({ ...d, name: value }))}
                    />
                    <Form.Input
                        field="description"
                        label="Mô tả"
                        placeholder="Server chính tại Việt Nam"
                        initValue={formData.description}
                        onChange={(value) => setFormData(d => ({ ...d, description: value }))}
                    />
                    <Form.Input
                        field="websocket_url"
                        label="WebSocket URL"
                        prefix={<IconLink />}
                        placeholder="wss://example.com/ws"
                        initValue={formData.websocket_url}
                        onChange={(value) => setFormData(d => ({ ...d, websocket_url: value }))}
                    />
                    <Form.Input
                        field="api_url"
                        label="API URL"
                        prefix={<IconLink />}
                        placeholder="https://example.com/api/v1"
                        initValue={formData.api_url}
                        onChange={(value) => setFormData(d => ({ ...d, api_url: value }))}
                    />
                    <div className="grid grid-cols-2 gap-4">
                        <Form.Input
                            field="mqtt_host"
                            label="MQTT Host"
                            prefix={<IconWifi />}
                            placeholder="mqtt.example.com"
                            initValue={formData.mqtt_host}
                            onChange={(value) => setFormData(d => ({ ...d, mqtt_host: value }))}
                        />
                        <Form.InputNumber
                            field="mqtt_port"
                            label="MQTT Port"
                            initValue={formData.mqtt_port}
                            onChange={(value) => setFormData(d => ({ ...d, mqtt_port: Number(value) || 1883 }))}
                        />
                    </div>
                    <Form.Select
                        field="region"
                        label="Khu vực"
                        placeholder="Chọn khu vực"
                        initValue={formData.region}
                        onChange={(value) => setFormData(d => ({ ...d, region: value as string }))}
                        optionList={REGION_OPTIONS}
                    />
                </Form>
            </Modal>
        </div>
    );
}
