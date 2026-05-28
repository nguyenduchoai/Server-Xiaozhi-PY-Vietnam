import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
    Button,
    Card,
    Input,
    Modal,
    Table,
    Select,
    Tag,
    Typography,
    Empty,
    Popconfirm
} from "@douyinfe/semi-ui";
import { IconSearch, IconDelete, IconRefresh } from "@douyinfe/semi-icons";
import { ArrowRightLeft, Wifi, WifiOff, Cpu } from "lucide-react";
import { adminApi } from "@/services/subscriptionService";

interface AdminDevice {
    id: string;
    mac_address: string;
    device_name: string | null;
    board: string | null;
    firmware_version: string | null;
    status: string | null;
    user_id: string;
    user_email: string | null;
    user_name: string | null;
    last_connected_at: string | null;
    created_at: string;
}

interface User {
    id: string;
    name: string;
    email: string;
}

const { Text, Title } = Typography;

export function AdminDevicesPage() {
    const [devices, setDevices] = useState<AdminDevice[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");
    const [statusFilter, setStatusFilter] = useState<string | null>(null);
    const [pagination, setPagination] = useState({
        page: 1,
        pageSize: 20,
        total: 0,
        totalPages: 0,
    });

    // Transfer dialog
    const [showTransferDialog, setShowTransferDialog] = useState(false);
    const [transferringDevice, setTransferringDevice] = useState<AdminDevice | null>(null);
    const [selectedUserId, setSelectedUserId] = useState<string>("");
    const [processing, setProcessing] = useState(false);

    const loadDevices = useCallback(async () => {
        try {
            setLoading(true);
            const response = await adminApi.getDevices({
                search: searchQuery || undefined,
                status: statusFilter || undefined,
                page: pagination.page,
                page_size: pagination.pageSize,
            });

            setDevices(response.data || []);
            setPagination(prev => ({
                ...prev,
                total: response.total || 0,
                totalPages: response.total_pages || 0,
            }));
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Không thể tải danh sách thiết bị");
        } finally {
            setLoading(false);
        }
    }, [searchQuery, statusFilter, pagination.page, pagination.pageSize]);

    const loadUsers = async () => {
        try {
            const response = await adminApi.getUsers({ page_size: 500 });
            setUsers(response.data || []);
        } catch (error: any) {
            console.error("Failed to load users:", error);
        }
    };

    useEffect(() => {
        loadDevices();
        loadUsers();
    }, [loadDevices]);

    const formatDate = (dateStr: string | null | undefined) => {
        if (!dateStr) return "—";
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return "—";
        return date.toLocaleString('vi-VN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    const getStatusTag = (status: string | null) => {
        if (status === "online") {
            return (
                <Tag color="green" type="light">
                    <div className="flex items-center gap-1">
                        <Wifi size={12} />
                        Online
                    </div>
                </Tag>
            );
        }
        if (status === "offline") {
            return (
                <Tag color="grey" type="light">
                    <div className="flex items-center gap-1">
                        <WifiOff size={12} />
                        Offline
                    </div>
                </Tag>
            );
        }
        return <Tag color="grey">{status || "—"}</Tag>;
    };

    // Handle delete device
    const handleDelete = async (device: AdminDevice) => {
        setProcessing(true);
        try {
            await adminApi.deleteDevice(device.id);
            toast.success(`Đã xóa thiết bị ${device.mac_address}`);
            loadDevices();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Không thể xóa thiết bị");
        } finally {
            setProcessing(false);
        }
    };

    // Handle transfer click
    const handleTransferClick = (device: AdminDevice) => {
        setTransferringDevice(device);
        setSelectedUserId("");
        setShowTransferDialog(true);
    };

    // Handle transfer submit
    const handleTransfer = async () => {
        if (!transferringDevice || !selectedUserId) return;

        setProcessing(true);
        try {
            const result = await adminApi.transferDevice(transferringDevice.id, selectedUserId);
            toast.success(result.message || "Đã chuyển thiết bị thành công");
            setShowTransferDialog(false);
            setTransferringDevice(null);
            loadDevices();
        } catch (error: any) {
            toast.error(error.response?.data?.detail || "Không thể chuyển thiết bị");
        } finally {
            setProcessing(false);
        }
    };

    const columns = [
        {
            title: 'Thiết bị',
            dataIndex: 'device_name',
            width: 200,
            render: (text: string, record: AdminDevice) => (
                <div>
                    <div className="flex items-center gap-2">
                        <Cpu size={16} className="text-blue-500" />
                        <Text strong>{text || record.mac_address}</Text>
                    </div>
                    {text && (
                        <Text type="tertiary" size="small" style={{ marginLeft: 24 }}>
                            {record.mac_address}
                        </Text>
                    )}
                </div>
            )
        },
        {
            title: 'Firmware',
            dataIndex: 'firmware_version',
            width: 120,
            render: (text: string, record: AdminDevice) => (
                <div>
                    <Text>{text || "—"}</Text>
                    {record.board && (
                        <div>
                            <Text type="tertiary" size="small">{record.board}</Text>
                        </div>
                    )}
                </div>
            )
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            width: 100,
            render: (text: string) => getStatusTag(text)
        },
        {
            title: 'Tài khoản',
            dataIndex: 'user_email',
            width: 200,
            render: (text: string, record: AdminDevice) => (
                <div>
                    <Text strong>{record.user_name || "—"}</Text>
                    <div>
                        <Text type="tertiary" size="small">{text || "—"}</Text>
                    </div>
                </div>
            )
        },
        {
            title: 'Kết nối lần cuối',
            dataIndex: 'last_connected_at',
            width: 150,
            render: (text: string) => (
                <Text type="secondary" size="small">{formatDate(text)}</Text>
            )
        },
        {
            title: 'Ngày tạo',
            dataIndex: 'created_at',
            width: 150,
            render: (text: string) => (
                <Text type="secondary" size="small">{formatDate(text)}</Text>
            )
        },
        {
            title: 'Thao tác',
            key: 'actions',
            width: 120,
            render: (_: unknown, record: AdminDevice) => (
                <div className="flex justify-end gap-2">
                    <Button
                        icon={<ArrowRightLeft size={14} />}
                        theme="borderless"
                        onClick={() => handleTransferClick(record)}
                        title="Chuyển thiết bị"
                    />
                    <Popconfirm
                        title="Xác nhận xóa"
                        content={`Bạn có chắc muốn xóa thiết bị ${record.device_name || record.mac_address}?`}
                        onConfirm={() => handleDelete(record)}
                        okText="Xóa"
                        cancelText="Hủy"
                        okType="danger"
                    >
                        <Button
                            icon={<IconDelete />}
                            theme="borderless"
                            type="danger"
                            title="Xóa thiết bị"
                        />
                    </Popconfirm>
                </div>
            )
        }
    ];

    return (
        <div className="space-y-6 p-6">
            <div className="flex justify-between items-center">
                <div>
                    <Title heading={3} style={{ margin: 0 }}>Quản lý Thiết bị (System)</Title>
                    <Text type="secondary">Quản lý tất cả thiết bị trong hệ thống - Chỉ SuperAdmin</Text>
                </div>
                <Button
                    onClick={() => loadDevices()}
                    icon={<IconRefresh />}
                    loading={loading}
                >
                    Làm mới
                </Button>
            </div>

            <Card bodyStyle={{ padding: 16 }}>
                <div className="flex justify-between items-center gap-4">
                    <Input
                        prefix={<IconSearch />}
                        placeholder="Tìm kiếm theo MAC, tên thiết bị, hoặc email..."
                        value={searchQuery}
                        onChange={(v) => {
                            setSearchQuery(v);
                            setPagination(prev => ({ ...prev, page: 1 }));
                        }}
                        onEnterPress={() => loadDevices()}
                        showClear
                        style={{ flex: 1 }}
                    />
                    <Select
                        placeholder="Trạng thái"
                        value={statusFilter ?? undefined}
                        onChange={(v) => {
                            setStatusFilter(v as string);
                            setPagination(prev => ({ ...prev, page: 1 }));
                        }}
                        style={{ width: 150 }}
                        showClear
                        optionList={[
                            { value: "online", label: "🟢 Online" },
                            { value: "offline", label: "⚫ Offline" },
                        ]}
                    />
                </div>
            </Card>

            <Card bodyStyle={{ padding: 0 }}>
                <Table
                    columns={columns}
                    dataSource={devices}
                    pagination={{
                        currentPage: pagination.page,
                        pageSize: pagination.pageSize,
                        total: pagination.total,
                        onPageChange: (page) => setPagination(prev => ({ ...prev, page })),
                        onPageSizeChange: (pageSize) => setPagination(prev => ({ ...prev, pageSize, page: 1 })),
                        showSizeChanger: true,
                        pageSizeOpts: [10, 20, 50, 100],
                    }}
                    loading={loading}
                    empty={<Empty title={loading ? "" : "Không có thiết bị nào"} />}
                    rowKey="id"
                />
            </Card>

            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card bodyStyle={{ padding: 16 }}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
                            <Cpu className="text-blue-500" size={20} />
                        </div>
                        <div>
                            <Text type="secondary" size="small">Tổng thiết bị</Text>
                            <Title heading={4} style={{ margin: 0 }}>{pagination.total}</Title>
                        </div>
                    </div>
                </Card>
                <Card bodyStyle={{ padding: 16 }}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                            <Wifi className="text-green-500" size={20} />
                        </div>
                        <div>
                            <Text type="secondary" size="small">Đang online</Text>
                            <Title heading={4} style={{ margin: 0 }}>
                                {devices.filter(d => d.status === "online").length}
                            </Title>
                        </div>
                    </div>
                </Card>
                <Card bodyStyle={{ padding: 16 }}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center">
                            <WifiOff className="text-gray-500" size={20} />
                        </div>
                        <div>
                            <Text type="secondary" size="small">Đang offline</Text>
                            <Title heading={4} style={{ margin: 0 }}>
                                {devices.filter(d => d.status === "offline").length}
                            </Title>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Transfer Dialog */}
            <Modal
                visible={showTransferDialog}
                onCancel={() => setShowTransferDialog(false)}
                title="Chuyển Thiết bị"
                onOk={handleTransfer}
                confirmLoading={processing}
                okText="Chuyển"
                cancelText="Hủy"
                okButtonProps={{ disabled: !selectedUserId }}
                centered
            >
                <div className="space-y-4">
                    {/* Device info */}
                    <div className="bg-gray-50 p-3 rounded">
                        <div className="flex items-center gap-2 mb-2">
                            <Cpu size={16} className="text-blue-500" />
                            <Text strong>{transferringDevice?.device_name || transferringDevice?.mac_address}</Text>
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                                <Text type="tertiary">MAC:</Text>
                                <Text style={{ marginLeft: 4 }}>{transferringDevice?.mac_address}</Text>
                            </div>
                            <div>
                                <Text type="tertiary">Owner hiện tại:</Text>
                                <Text style={{ marginLeft: 4 }}>{transferringDevice?.user_email}</Text>
                            </div>
                        </div>
                    </div>

                    {/* User selector */}
                    <div>
                        <Text strong style={{ display: 'block', marginBottom: 8 }}>Chọn người dùng mới</Text>
                        <Select
                            value={selectedUserId}
                            onChange={(v) => setSelectedUserId(v as string)}
                            style={{ width: '100%' }}
                            placeholder="Chọn người dùng..."
                            filter
                            optionList={users
                                .filter(u => u.id !== transferringDevice?.user_id)
                                .map(u => ({
                                    value: u.id,
                                    label: `${u.name} (${u.email})`,
                                }))}
                        />
                    </div>

                    {selectedUserId && (
                        <div className="bg-yellow-50 p-3 rounded border border-yellow-200">
                            <Text type="warning" size="small">
                                ⚠️ Thiết bị sẽ được chuyển ngay lập tức. Người dùng cũ sẽ không còn quyền truy cập thiết bị này.
                            </Text>
                        </div>
                    )}
                </div>
            </Modal>
        </div>
    );
}

export default AdminDevicesPage;
