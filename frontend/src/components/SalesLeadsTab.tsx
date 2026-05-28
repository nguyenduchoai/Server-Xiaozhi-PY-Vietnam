/**
 * SalesLeadsTab — Khách hàng quan tâm sản phẩm (Sales Leads)
 * 
 * Displays leads auto-captured from AI voice conversations + manual entries.
 * Supports filtering, status management, and inline editing.
 */
import { useState, useEffect, useCallback } from 'react';
import {
    Card, Button, Typography, Empty, Spin, Toast, Table, Tag, Space,
    Input, Select, Popconfirm, Modal, Form, Tooltip, Pagination,
} from '@douyinfe/semi-ui';
import { IconPlus, IconDelete, IconSearch, IconRefresh } from '@douyinfe/semi-icons';
import { Users, Phone, Mail, MessageSquare, Sparkles } from 'lucide-react';
import axiosInstance from '@/config/axios-instance';

const { Title, Text } = Typography;

interface Lead {
    id: string;
    customer_name?: string;
    customer_phone?: string;
    customer_email?: string;
    product_id?: string;
    product_name: string;
    inquiry_text?: string;
    ai_response?: string;
    source: string;
    device_id?: string;
    status: string;
    priority: number;
    notes?: string;
    notified: boolean;
    agent_id?: string;
    created_at?: string;
}

interface LeadStats {
    total: number;
    by_status: Record<string, number>;
    by_source: Record<string, number>;
    top_products: { name: string; count: number }[];
}

const STATUS_MAP: Record<string, { color: string; label: string }> = {
    new: { color: 'orange', label: 'Mới' },
    contacted: { color: 'blue', label: 'Đã liên hệ' },
    converted: { color: 'green', label: 'Đã chuyển đổi' },
    archived: { color: 'grey', label: 'Lưu trữ' },
};

const SOURCE_MAP: Record<string, string> = {
    voice: '🎙️ Giọng nói',
    web: '🌐 Web Chat',
    mqtt: '📡 Thiết bị',
    manual: '✍️ Thủ công',
};

const PRIORITY_MAP: Record<number, { color: string; label: string }> = {
    0: { color: 'grey', label: 'Bình thường' },
    1: { color: 'orange', label: 'Quan trọng' },
    2: { color: 'red', label: 'Khẩn cấp' },
};

export const SalesLeadsTab = () => {
    const [leads, setLeads] = useState<Lead[]>([]);
    const [stats, setStats] = useState<LeadStats | null>(null);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState<string | undefined>();
    const [sourceFilter, setSourceFilter] = useState<string | undefined>();
    const [showCreateDlg, setShowCreateDlg] = useState(false);
    const [editingLead, setEditingLead] = useState<Lead | null>(null);

    const loadLeads = useCallback(async () => {
        setLoading(true);
        try {
            const params: Record<string, any> = { page, page_size: 15 };
            if (search) params.search = search;
            if (statusFilter) params.status = statusFilter;
            if (sourceFilter) params.source = sourceFilter;
            const { data } = await axiosInstance.get('/sales/leads', { params });
            setLeads(data.items || []);
            setTotal(data.total || 0);
        } catch {
            Toast.error('Không thể tải danh sách khách hàng');
        } finally {
            setLoading(false);
        }
    }, [page, search, statusFilter, sourceFilter]);

    const loadStats = useCallback(async () => {
        try {
            const { data } = await axiosInstance.get('/sales/leads/stats');
            setStats(data);
        } catch { /* ignore */ }
    }, []);

    useEffect(() => { loadLeads(); }, [loadLeads]);
    useEffect(() => { loadStats(); }, []);

    const handleUpdateStatus = async (id: string, status: string) => {
        try {
            await axiosInstance.put(`/sales/leads/${id}`, { status });
            setLeads(prev => prev.map(l => l.id === id ? { ...l, status } : l));
            loadStats();
            Toast.success('Đã cập nhật');
        } catch {
            Toast.error('Cập nhật thất bại');
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await axiosInstance.delete(`/sales/leads/${id}`);
            setLeads(prev => prev.filter(l => l.id !== id));
            setTotal(prev => prev - 1);
            loadStats();
            Toast.success('Đã xoá');
        } catch {
            Toast.error('Xoá thất bại');
        }
    };

    const handleCreate = async (values: any) => {
        try {
            await axiosInstance.post('/sales/leads', values);
            Toast.success('Đã thêm khách hàng');
            setShowCreateDlg(false);
            loadLeads();
            loadStats();
        } catch (err: any) {
            Toast.error(err?.response?.data?.detail || 'Lỗi');
        }
    };

    const handleUpdateNotes = async (id: string, notes: string) => {
        try {
            await axiosInstance.put(`/sales/leads/${id}`, { notes });
            setLeads(prev => prev.map(l => l.id === id ? { ...l, notes } : l));
        } catch { /* silent */ }
    };

    const fmtDate = (iso?: string) => {
        if (!iso) return '-';
        const d = new Date(iso);
        return d.toLocaleDateString('vi-VN') + ' ' + d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
    };

    const columns = [
        {
            title: 'Khách hàng',
            dataIndex: 'customer_name',
            width: 160,
            render: (_: any, r: Lead) => (
                <div>
                    <Text strong>{r.customer_name || 'Ẩn danh'}</Text>
                    {r.customer_phone && (
                        <div className="flex items-center gap-1 mt-0.5">
                            <Phone size={11} className="text-gray-400" />
                            <Text type="tertiary" size="small">{r.customer_phone}</Text>
                        </div>
                    )}
                    {r.customer_email && (
                        <div className="flex items-center gap-1">
                            <Mail size={11} className="text-gray-400" />
                            <Text type="tertiary" size="small">{r.customer_email}</Text>
                        </div>
                    )}
                </div>
            ),
        },
        {
            title: 'Sản phẩm quan tâm',
            dataIndex: 'product_name',
            width: 180,
            render: (name: string, r: Lead) => (
                <div>
                    <Text strong style={{ color: 'var(--apple-blue)' }}>{name}</Text>
                    {r.inquiry_text && (
                        <Tooltip content={r.inquiry_text}>
                            <div className="flex items-center gap-1 mt-0.5 cursor-help">
                                <MessageSquare size={11} className="text-gray-400" />
                                <Text type="tertiary" size="small" ellipsis={{ showTooltip: false }} style={{ maxWidth: 140 }}>
                                    {r.inquiry_text}
                                </Text>
                            </div>
                        </Tooltip>
                    )}
                </div>
            ),
        },
        {
            title: 'Nguồn',
            dataIndex: 'source',
            width: 100,
            render: (s: string) => <Tag size="small">{SOURCE_MAP[s] || s}</Tag>,
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            width: 130,
            render: (status: string, r: Lead) => (
                <Select
                    value={status}
                    size="small"
                    onChange={(val) => handleUpdateStatus(r.id, val as string)}
                    style={{ width: 120 }}
                    optionList={Object.entries(STATUS_MAP).map(([k, v]) => ({
                        value: k, label: v.label,
                    }))}
                    renderSelectedItem={({ value }: any) => {
                        const s = STATUS_MAP[value as string];
                        return <Tag size="small" color={s?.color || 'grey'}>{s?.label || value}</Tag>;
                    }}
                />
            ),
        },
        {
            title: 'Ưu tiên',
            dataIndex: 'priority',
            width: 90,
            render: (p: number) => {
                const info = PRIORITY_MAP[p] || PRIORITY_MAP[0];
                return <Tag size="small" color={info.color}>{info.label}</Tag>;
            },
        },
        {
            title: 'Thời gian',
            dataIndex: 'created_at',
            width: 130,
            render: (d: string) => <Text type="tertiary" size="small">{fmtDate(d)}</Text>,
        },
        {
            title: '',
            width: 60,
            render: (_: any, r: Lead) => (
                <Space>
                    <Popconfirm title="Xoá lead này?" onConfirm={() => handleDelete(r.id)}>
                        <Button icon={<IconDelete />} size="small" theme="borderless" type="danger" />
                    </Popconfirm>
                </Space>
            ),
        },
    ];

    return (
        <div className="space-y-4" style={{ marginTop: 16 }}>
            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="p-4 rounded-xl text-center" style={{ background: 'var(--apple-surface-secondary)', border: '1px solid var(--apple-border-primary)' }}>
                        <Text type="tertiary" size="small" className="block mb-1">Tổng lead</Text>
                        <Title heading={3} style={{ margin: 0, color: 'var(--apple-blue)' }}>{stats.total}</Title>
                    </div>
                    <div className="p-4 rounded-xl text-center" style={{ background: 'var(--apple-surface-secondary)', border: '1px solid var(--apple-border-primary)' }}>
                        <Text type="tertiary" size="small" className="block mb-1">Mới</Text>
                        <Title heading={3} style={{ margin: 0, color: '#FF9500' }}>{stats.by_status?.new || 0}</Title>
                    </div>
                    <div className="p-4 rounded-xl text-center" style={{ background: 'var(--apple-surface-secondary)', border: '1px solid var(--apple-border-primary)' }}>
                        <Text type="tertiary" size="small" className="block mb-1">Đã liên hệ</Text>
                        <Title heading={3} style={{ margin: 0, color: '#007AFF' }}>{stats.by_status?.contacted || 0}</Title>
                    </div>
                    <div className="p-4 rounded-xl text-center" style={{ background: 'var(--apple-surface-secondary)', border: '1px solid var(--apple-border-primary)' }}>
                        <Text type="tertiary" size="small" className="block mb-1">Chuyển đổi</Text>
                        <Title heading={3} style={{ margin: 0, color: '#34C759' }}>{stats.by_status?.converted || 0}</Title>
                    </div>
                </div>
            )}

            {/* Top Products */}
            {stats?.top_products && stats.top_products.length > 0 && (
                <Card size="small" title={<span className="flex items-center gap-2"><Sparkles size={14} /> Sản phẩm được hỏi nhiều nhất</span>}>
                    <div className="flex flex-wrap gap-2">
                        {stats.top_products.map((p, i) => (
                            <Tag key={i} color="blue" size="large">
                                {p.name} <span className="ml-1 font-bold">×{p.count}</span>
                            </Tag>
                        ))}
                    </div>
                </Card>
            )}

            {/* Toolbar */}
            <Card size="small">
                <div className="flex flex-wrap items-center gap-3">
                    <Input
                        prefix={<IconSearch />}
                        placeholder="Tìm theo tên, SĐT, sản phẩm..."
                        value={search}
                        onChange={setSearch}
                        onEnterPress={() => { setPage(1); loadLeads(); }}
                        style={{ width: 260 }}
                        showClear
                    />
                    <Select
                        placeholder="Trạng thái"
                        value={statusFilter}
                        onChange={(v) => { setStatusFilter(v as string); setPage(1); }}
                        style={{ width: 140 }}
                        showClear
                        optionList={Object.entries(STATUS_MAP).map(([k, v]) => ({ value: k, label: v.label }))}
                    />
                    <Select
                        placeholder="Nguồn"
                        value={sourceFilter}
                        onChange={(v) => { setSourceFilter(v as string); setPage(1); }}
                        style={{ width: 140 }}
                        showClear
                        optionList={Object.entries(SOURCE_MAP).map(([k, v]) => ({ value: k, label: v }))}
                    />
                    <div className="flex-1" />
                    <Button icon={<IconRefresh />} onClick={() => { loadLeads(); loadStats(); }} loading={loading} />
                    <Button icon={<IconPlus />} theme="solid" onClick={() => setShowCreateDlg(true)}>
                        Thêm thủ công
                    </Button>
                </div>
            </Card>

            {/* Table */}
            <Card size="small">
                {loading ? (
                    <div className="flex justify-center p-8"><Spin /></div>
                ) : leads.length === 0 ? (
                    <Empty
                        image={<Users className="mx-auto h-12 w-12 text-gray-300" />}
                        title="Chưa có khách hàng quan tâm"
                        description="Khi khách hỏi AI về sản phẩm, thông tin sẽ tự động được ghi lại tại đây."
                    />
                ) : (
                    <>
                        <Table
                            dataSource={leads}
                            columns={columns}
                            rowKey="id"
                            pagination={false}
                            size="small"
                            expandedRowRender={(r: Lead) => (
                                <div className="p-3 space-y-2" style={{ background: '#fafafa', borderRadius: 8 }}>
                                    {r.inquiry_text && (
                                        <div><Text strong size="small">Câu hỏi:</Text> <Text size="small">{r.inquiry_text}</Text></div>
                                    )}
                                    {r.ai_response && (
                                        <div><Text strong size="small">AI trả lời:</Text> <Text size="small" type="tertiary">{r.ai_response}</Text></div>
                                    )}
                                    <div className="flex gap-2 items-start">
                                        <Text strong size="small" style={{ whiteSpace: 'nowrap' }}>Ghi chú:</Text>
                                        <Input
                                            size="small"
                                            defaultValue={r.notes || ''}
                                            placeholder="Thêm ghi chú..."
                                            onBlur={(e) => handleUpdateNotes(r.id, (e.target as HTMLInputElement).value)}
                                            style={{ flex: 1 }}
                                        />
                                    </div>
                                </div>
                            )}
                        />
                        {total > 15 && (
                            <div className="flex justify-end mt-3">
                                <Pagination
                                    total={total}
                                    pageSize={15}
                                    currentPage={page}
                                    onPageChange={setPage}
                                    size="small"
                                />
                            </div>
                        )}
                    </>
                )}
            </Card>

            {/* Create Lead Dialog */}
            <Modal
                title="➕ Thêm Khách Hàng Quan Tâm"
                visible={showCreateDlg}
                onCancel={() => setShowCreateDlg(false)}
                footer={null}
                width={480}
            >
                <Form onSubmit={handleCreate} labelPosition="top">
                    <Form.Input field="product_name" label="Sản phẩm quan tâm" rules={[{ required: true }]} placeholder="VD: Xiaozhi ESP32" />
                    <div className="grid grid-cols-2 gap-3">
                        <Form.Input field="customer_name" label="Tên khách hàng" placeholder="Nguyễn Văn A" />
                        <Form.Input field="customer_phone" label="Số điện thoại" placeholder="0901234567" />
                    </div>
                    <Form.Input field="customer_email" label="Email" placeholder="email@example.com" />
                    <Form.TextArea field="inquiry_text" label="Nội dung quan tâm" placeholder="Khách muốn biết giá, tính năng..." />
                    <Form.TextArea field="notes" label="Ghi chú" placeholder="Ghi chú nội bộ..." />
                    <div className="flex justify-end gap-2 mt-4">
                        <Button onClick={() => setShowCreateDlg(false)}>Huỷ</Button>
                        <Button htmlType="submit" theme="solid">Thêm</Button>
                    </div>
                </Form>
            </Modal>
        </div>
    );
};

export default SalesLeadsTab;
