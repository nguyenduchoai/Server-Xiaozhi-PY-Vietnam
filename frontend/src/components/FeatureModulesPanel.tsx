/**
 * FeatureModulesPanel — Manage Agent Feature Modules
 * 
 * 2-column grid layout with toggle switches for ALL features.
 * Features gated by subscription plan show 🔒 lock icon.
 * Users must upgrade plan to enable locked features.
 */

import { useState, useEffect, useCallback } from 'react';
import { 
    Switch, Typography, Button, Empty,
    Tag, Spin, Toast, Modal, Form, Select, Banner,
} from '@douyinfe/semi-ui';
import { 
    IconPlus, IconDelete, IconRefresh, IconLock,
} from '@douyinfe/semi-icons';
import { Brain, BookOpen, ShoppingBag, Mic } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { featureModulesApi } from '@/api/featureModulesApi';

import type { AgentFeatures, SalesProgram, MeetingRoom, EducationCourse } from '@/api/featureModulesApi';

const { Text, Title } = Typography;

interface FeatureModulesPanelProps {
    agentId: string;
    agentName?: string;
    agent?: any;
    onRefresh?: () => void;
}

// Feature card item
interface FeatureItem {
    key: string;
    planKey: string; // key in plan_allowed (e.g. "education", "sales")
    icon: React.ReactNode;
    label: string;
    description: string;
    color: string;
    bgFrom: string;
    bgTo: string;
    type: 'toggle' | 'module';
}

const FEATURE_ITEMS: FeatureItem[] = [
    {
        key: 'enable_memory',
        planKey: 'memory',
        icon: <Brain size={20} />,
        label: 'Bộ Nhớ',
        description: 'Ghi nhớ ngữ cảnh hội thoại',
        color: '#10b981',
        bgFrom: 'rgba(16,185,129,0.08)',
        bgTo: 'rgba(16,185,129,0.15)',
        type: 'toggle',
    },
    {
        key: 'enable_knowledge_base',
        planKey: 'knowledge_base',
        icon: <BookOpen size={20} />,
        label: 'Knowledge Base',
        description: 'RAG từ tài liệu',
        color: '#06b6d4',
        bgFrom: 'rgba(6,182,212,0.08)',
        bgTo: 'rgba(6,182,212,0.15)',
        type: 'module',
    },
    {
        key: 'enable_education',
        planKey: 'education',
        icon: <BookOpen size={20} />,
        label: 'Học Tập',
        description: 'Đào tạo theo khóa học và lộ trình',
        color: '#f59e0b',
        bgFrom: 'rgba(245,158,11,0.08)',
        bgTo: 'rgba(245,158,11,0.15)',
        type: 'module',
    },
    {
        key: 'enable_sales',
        planKey: 'sales',
        icon: <ShoppingBag size={20} />,
        label: 'Bán Hàng',
        description: 'Tư vấn sản phẩm AI',
        color: '#ef4444',
        bgFrom: 'rgba(239,68,68,0.08)',
        bgTo: 'rgba(239,68,68,0.15)',
        type: 'module',
    },
    {
        key: 'enable_meeting',
        planKey: 'meeting',
        icon: <Mic size={20} />,
        label: 'Họp / Meeting',
        description: 'Ghi chú cuộc họp',
        color: '#6366f1',
        bgFrom: 'rgba(99,102,241,0.08)',
        bgTo: 'rgba(99,102,241,0.15)',
        type: 'module',
    },
];

export const FeatureModulesPanel = ({ agentId, onRefresh }: FeatureModulesPanelProps) => {
    const { t } = useTranslation('agents');
    const navigate = useNavigate();

    
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState<string | null>(null);
    const [features, setFeatures] = useState<AgentFeatures | null>(null);
    
    // Available items
    const [salesPrograms, setSalesPrograms] = useState<SalesProgram[]>([]);
    const [meetingRooms, setMeetingRooms] = useState<MeetingRoom[]>([]);
    const [educationCourses, setEducationCourses] = useState<EducationCourse[]>([]);

    const [knowledgeBases, setKnowledgeBases] = useState<any[]>([]);

    // Dialogs
    const [showSalesDlg, setShowSalesDlg] = useState(false);
    const [showMeetingDlg, setShowMeetingDlg] = useState(false);

    // Expanded module
    const [expandedModule, setExpandedModule] = useState<string | null>(null);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const { default: axiosInstance } = await import('../config/axios-instance');
            
            const [feat, progs, rooms, courses] = await Promise.all([
                featureModulesApi.getAgentFeatures(agentId),
                featureModulesApi.getSalesPrograms(),
                featureModulesApi.getMeetingRooms(),
                featureModulesApi.getEducationCourses(true),
            ]);
            setFeatures(feat);
            setSalesPrograms(progs);
            setMeetingRooms(rooms);
            setEducationCourses(courses);
            


            try {
                const res = await axiosInstance.get('/knowledge-bases');
                setKnowledgeBases(res.data?.items || []);
            } catch { setKnowledgeBases([]); }
        } catch (err: any) {
            Toast.error({ content: err?.message || 'Failed to load', duration: 3 });
        } finally {
            setLoading(false);
        }
    }, [agentId]);

    useEffect(() => { loadData(); }, [loadData]);

    // Check if a feature is allowed by the user's subscription plan
    const isPlanAllowed = (planKey: string): boolean => {
        if (!features?.plan_allowed || Object.keys(features.plan_allowed).length === 0) {
            return true; // No plan restriction (superadmin or fallback)
        }
        // If planKey not in plan_allowed, default to allowed
        return features.plan_allowed[planKey] !== false;
    };

    // Toggle feature on/off
    const handleToggle = async (key: string, planKey: string, value: boolean) => {
        // Check plan gating BEFORE trying to enable
        if (value && !isPlanAllowed(planKey)) {
            Toast.warning({
                content: `🔒 Tính năng "${planKey}" cần gói PRO trở lên. Vui lòng nâng cấp tại mục Thanh Toán.`,
                duration: 4,
            });
            return;
        }

        setSaving(key);
        try {
            const result = await featureModulesApi.updateAgentFeatures(agentId, { [key]: value });
            setFeatures(result);
            // Refresh parent for features that affect agent model directly
            if (['enable_knowledge_base', 'enable_memory'].includes(key)) {
                onRefresh?.();
            }
            Toast.success({ content: `${value ? '✅ Đã bật' : '⏸️ Đã tắt'} tính năng`, duration: 2 });
        } catch (err: any) {
            // Backend 403 = plan gating
            if (err?.response?.status === 403) {
                Toast.warning({
                    content: `🔒 ${err.response.data?.detail || 'Cần nâng cấp gói để sử dụng tính năng này.'}`,
                    duration: 4,
                });
            } else {
                Toast.error({ content: err?.message || 'Lỗi', duration: 3 });
            }
        } finally {
            setSaving(null);
        }
    };

    // Module-specific updates
    const updateModuleConfig = async (key: string, value: any) => {
        setSaving(key);
        try {
            const result = await featureModulesApi.updateAgentFeatures(agentId, { [key]: value });
            setFeatures(result);
        } catch (err: any) {
            Toast.error({ content: err?.message || 'Lỗi', duration: 3 });
        } finally {
            setSaving(null);
        }
    };

    const handleCreateSales = async (values: any) => {
        try {
            await featureModulesApi.createSalesProgram(values);
            Toast.success({ content: 'Đã tạo chương trình bán hàng', duration: 3 });
            setShowSalesDlg(false);
            loadData();
        } catch (err: any) {
            Toast.error({ content: err?.message || 'Lỗi tạo chương trình', duration: 3 });
        }
    };

    const handleCreateMeeting = async (values: any) => {
        try {
            await featureModulesApi.createMeetingRoom(values);
            Toast.success({ content: 'Đã tạo phòng họp', duration: 3 });
            setShowMeetingDlg(false);
            loadData();
        } catch (err: any) {
            Toast.error({ content: err?.message || 'Lỗi tạo phòng họp', duration: 3 });
        }
    };

    const handleDeleteSales = async (id: string) => {
        try {
            await featureModulesApi.deleteSalesProgram(id);
            Toast.success({ content: 'Đã xóa', duration: 2 });
            loadData();
        } catch (err: any) {
            Toast.error({ content: err?.message || 'Lỗi', duration: 3 });
        }
    };

    const handleDeleteMeeting = async (id: string) => {
        try {
            await featureModulesApi.deleteMeetingRoom(id);
            Toast.success({ content: 'Đã xóa', duration: 2 });
            loadData();
        } catch (err: any) {
            Toast.error({ content: err?.message || 'Lỗi', duration: 3 });
        }
    };

    // Get value for a feature key
    const getFeatureValue = (key: string): boolean => {
        return features?.[key as keyof AgentFeatures] as boolean ?? false;
    };

    if (loading) {
        return <div className="flex justify-center p-8"><Spin size="large" /></div>;
    }

    if (!features) {
        return <Empty description="Không thể tải cấu hình tính năng" />;
    }

    // Count locked features
    const lockedCount = FEATURE_ITEMS.filter(item => !isPlanAllowed(item.planKey)).length;

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                    <Title heading={5} style={{ margin: 0 }}>
                        ⚙️ {t('feature_modules', 'Tính Năng Mở Rộng')}
                    </Title>
                    <Tag color="blue" size="small">
                        Gói {features.plan_name || 'FREE'}
                    </Tag>
                </div>
                <Button 
                    icon={<IconRefresh />} 
                    theme="borderless" 
                    onClick={() => { loadData(); onRefresh?.(); }}
                    loading={loading}
                />
            </div>

            {/* Plan upgrade banner if any features are locked */}
            {lockedCount > 0 && (
                <Banner
                    type="warning"
                    description={
                        <span>
                            🔒 <strong>{lockedCount} tính năng</strong> bị khóa trong gói <strong>{features.plan_name || 'FREE'}</strong>.{' '}
                            <a href="/subscription" style={{ color: '#f59e0b', fontWeight: 600 }}>
                                Nâng cấp gói PRO →
                            </a>
                        </span>
                    }
                    closeIcon={null}
                    style={{ 
                        borderRadius: 12,
                        background: 'rgba(245,158,11,0.08)',
                        border: '1px solid rgba(245,158,11,0.2)',
                    }}
                />
            )}

            {/* 2-Column Feature Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {FEATURE_ITEMS.map((item) => {
                    const isEnabled = getFeatureValue(item.key);
                    const isSaving = saving === item.key;
                    const isExpanded = expandedModule === item.key && isEnabled && item.type === 'module';
                    const isLocked = !isPlanAllowed(item.planKey);

                    return (
                        <div
                            key={item.key}
                            className="rounded-2xl overflow-hidden transition-all duration-300"
                            style={{
                                background: isLocked
                                    ? 'var(--semi-color-fill-0)'
                                    : isEnabled 
                                        ? `linear-gradient(145deg, ${item.bgFrom}, ${item.bgTo})`
                                        : 'var(--semi-color-fill-0)',
                                border: isLocked
                                    ? '1px solid var(--semi-color-border)'
                                    : isEnabled 
                                        ? `1px solid ${item.color}25`
                                        : '1px solid var(--semi-color-border)',
                                opacity: isLocked ? 0.7 : 1,
                                position: 'relative',
                            }}
                        >
                            {/* Lock overlay badge */}
                            {isLocked && (
                                <div style={{
                                    position: 'absolute',
                                    top: 8,
                                    right: 8,
                                    background: 'rgba(245,158,11,0.15)',
                                    border: '1px solid rgba(245,158,11,0.3)',
                                    borderRadius: 8,
                                    padding: '2px 8px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 4,
                                    zIndex: 2,
                                }}>
                                    <IconLock size="small" style={{ color: '#f59e0b' }} />
                                    <Text size="small" style={{ color: '#f59e0b', fontWeight: 600, fontSize: 11 }}>
                                        PRO
                                    </Text>
                                </div>
                            )}

                            {/* Toggle Row */}
                            <div 
                                className="flex items-center gap-3 p-4 cursor-pointer select-none"
                                onClick={() => {
                                    if (isLocked) {
                                        Toast.warning({
                                            content: `🔒 Cần gói PRO để sử dụng ${item.label}`,
                                            duration: 3,
                                        });
                                        return;
                                    }
                                    if (item.type === 'module' && isEnabled) {
                                        setExpandedModule(prev => prev === item.key ? null : item.key);
                                    }
                                }}
                            >
                                <div 
                                    className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-300"
                                    style={{ 
                                        background: isEnabled && !isLocked ? `${item.color}15` : 'var(--semi-color-fill-1)',
                                        color: isEnabled && !isLocked ? item.color : 'var(--semi-color-text-2)',
                                    }}
                                >
                                    {item.icon}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <Text strong className="block text-sm">{item.label}</Text>
                                    <Text type="tertiary" size="small">{item.description}</Text>
                                </div>
                                <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                                    {item.type === 'module' && isEnabled && !isLocked && (
                                        <Text 
                                            type="tertiary" 
                                            size="small" 
                                            className="cursor-pointer hover:text-blue-500 transition-colors"
                                            onClick={() => setExpandedModule(prev => prev === item.key ? null : item.key)}
                                        >
                                            {isExpanded ? '▲' : '▼'}
                                        </Text>
                                    )}
                                    <Switch 
                                        checked={isEnabled}
                                        onChange={(v) => handleToggle(item.key, item.planKey, v)}
                                        loading={isSaving}
                                        size="default"
                                        disabled={isLocked}
                                    />
                                </div>
                            </div>

                            {/* Expanded Config Panel */}
                            {isExpanded && !isLocked && (
                                <div className="px-4 pb-4 pt-0 border-t" style={{ borderColor: `${item.color}15` }}>

                                    {/* Knowledge Base Selector */}
                                    {item.key === 'enable_knowledge_base' && (
                                        <div className="mt-3">
                                            <Text type="tertiary" size="small" className="mb-2 block">Chọn kho kiến thức sử dụng:</Text>
                                            <Select
                                                multiple
                                                style={{ width: '100%' }}
                                                placeholder="Chọn Knowledge Base..."
                                                value={features.knowledge_base_ids}
                                                onChange={(v) => updateModuleConfig('knowledge_base_ids', v)}
                                                optionList={knowledgeBases.map(kb => ({
                                                    value: kb.id,
                                                    label: kb.name || kb.id,
                                                }))}
                                                emptyContent={
                                                    <Text type="tertiary" size="small">
                                                        Chưa có kho kiến thức. Tạo tại mục Knowledge Base.
                                                    </Text>
                                                }
                                            />
                                            {features.knowledge_base_ids?.length > 0 && (
                                                <div className="flex gap-1 mt-2 flex-wrap">
                                                    {features.knowledge_base_ids.map(id => {
                                                        const kb = knowledgeBases.find(k => k.id === id);
                                                        return (
                                                            <Tag key={id} color="cyan" size="small">
                                                                📖 {kb?.name || id.slice(0, 8)}
                                                            </Tag>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Sales Selector */}
                                    {item.key === 'enable_education' && (
                                        <div className="mt-3">
                                            <div className="flex items-center justify-between mb-2">
                                                <Text type="tertiary" size="small">Chọn khóa học:</Text>
                                                <Button size="small" theme="light" onClick={() => navigate('/education')}>
                                                    Quản lý Education
                                                </Button>
                                            </div>
                                            <Select
                                                multiple
                                                style={{ width: '100%' }}
                                                placeholder="Chọn khóa học..."
                                                value={features.course_ids}
                                                onChange={(v) => updateModuleConfig('course_ids', v)}
                                                optionList={educationCourses.map(c => ({
                                                    value: c.id,
                                                    label: `${c.name}${c.is_published ? '' : ' (draft)'}`,
                                                }))}
                                                emptyContent={<Text type="tertiary" size="small">Chưa có khóa học.</Text>}
                                            />
                                            {educationCourses.filter(c => features.course_ids?.includes(c.id)).length > 0 && (
                                                <div className="mt-2 space-y-1">
                                                    {educationCourses.filter(c => features.course_ids?.includes(c.id)).map(c => (
                                                        <div key={c.id} className="flex items-center justify-between p-2 rounded-lg"
                                                             style={{ background: 'var(--semi-color-fill-0)' }}>
                                                            <div className="flex items-center gap-2">
                                                                <Text strong size="small">{c.name}</Text>
                                                                <Tag color={c.is_published ? "green" : "grey"} size="small">
                                                                    {c.is_published ? 'Published' : 'Draft'}
                                                                </Tag>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Sales Selector */}
                                    {item.key === 'enable_sales' && (
                                        <div className="mt-3">
                                            <div className="flex items-center justify-between mb-2">
                                                <Text type="tertiary" size="small">Chọn chương trình:</Text>
                                                <Button icon={<IconPlus />} size="small" theme="light" onClick={() => setShowSalesDlg(true)}>
                                                    Tạo mới
                                                </Button>
                                            </div>
                                            <Select
                                                multiple
                                                style={{ width: '100%' }}
                                                placeholder="Chọn chương trình..."
                                                value={features.sales_program_ids}
                                                onChange={(v) => updateModuleConfig('sales_program_ids', v)}
                                                optionList={salesPrograms.map(p => ({
                                                    value: p.id,
                                                    label: `${p.name} (${p.mode})`,
                                                }))}
                                                emptyContent={<Text type="tertiary" size="small">Chưa có.</Text>}
                                            />
                                            {salesPrograms.filter(p => features.sales_program_ids?.includes(p.id)).length > 0 && (
                                                <div className="mt-2 space-y-1">
                                                    {salesPrograms.filter(p => features.sales_program_ids?.includes(p.id)).map(p => (
                                                        <div key={p.id} className="flex items-center justify-between p-2 rounded-lg"
                                                             style={{ background: 'var(--semi-color-fill-0)' }}>
                                                            <div className="flex items-center gap-2">
                                                                <Text strong size="small">{p.name}</Text>
                                                                <Tag color="blue" size="small">{p.mode}</Tag>
                                                            </div>
                                                            <Button icon={<IconDelete />} type="danger" theme="borderless" size="small"
                                                                onClick={() => handleDeleteSales(p.id)} />
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {/* Meeting Selector */}
                                    {item.key === 'enable_meeting' && (
                                        <div className="mt-3">
                                            <div className="flex items-center justify-between mb-2">
                                                <Text type="tertiary" size="small">Chọn phòng họp:</Text>
                                                <Button icon={<IconPlus />} size="small" theme="light" onClick={() => setShowMeetingDlg(true)}>
                                                    Tạo mới
                                                </Button>
                                            </div>
                                            <Select
                                                multiple
                                                style={{ width: '100%' }}
                                                placeholder="Chọn phòng họp..."
                                                value={features.meeting_room_ids}
                                                onChange={(v) => updateModuleConfig('meeting_room_ids', v)}
                                                optionList={meetingRooms.map(r => ({
                                                    value: r.id,
                                                    label: `${r.name}${r.department ? ` (${r.department})` : ''}`,
                                                }))}
                                                emptyContent={<Text type="tertiary" size="small">Chưa có.</Text>}
                                            />
                                            {meetingRooms.filter(r => features.meeting_room_ids?.includes(r.id)).length > 0 && (
                                                <div className="mt-2 space-y-1">
                                                    {meetingRooms.filter(r => features.meeting_room_ids?.includes(r.id)).map(r => (
                                                        <div key={r.id} className="flex items-center justify-between p-2 rounded-lg"
                                                             style={{ background: 'var(--semi-color-fill-0)' }}>
                                                            <div className="flex items-center gap-2">
                                                                <Text strong size="small">{r.name}</Text>
                                                                {r.department && <Tag color="violet" size="small">{r.department}</Tag>}
                                                            </div>
                                                            <Button icon={<IconDelete />} type="danger" theme="borderless" size="small"
                                                                onClick={() => handleDeleteMeeting(r.id)} />
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* ========== CREATE SALES DIALOG ========== */}
            <Modal
                title="Tạo Chương Trình Bán Hàng"
                visible={showSalesDlg}
                onCancel={() => setShowSalesDlg(false)}
                footer={null}
                width={500}
            >
                <Form onSubmit={handleCreateSales} labelPosition="top">
                    <Form.Input field="name" label="Tên chương trình" rules={[{ required: true }]} />
                    <Form.TextArea field="description" label="Mô tả" />
                    <Form.Select field="mode" label="Chế độ" initValue="sales"
                        optionList={[
                            { value: 'sales', label: '🛍️ Sales (Bán hàng)' },
                        ]}
                    />
                    <Form.Input field="business_name" label="Tên cửa hàng" />
                    <Form.Input field="welcome_message" label="Lời chào" placeholder="Xin chào, em có thể giúp gì..." />
                    <Form.TextArea field="system_prompt" label="System Prompt (tuỳ chọn)" placeholder="Bạn là nhân viên bán hàng..." />
                    <div className="flex justify-end gap-2 mt-4">
                        <Button onClick={() => setShowSalesDlg(false)}>Huỷ</Button>
                        <Button htmlType="submit" theme="solid" type="primary">Tạo</Button>
                    </div>
                </Form>
            </Modal>

            {/* ========== CREATE MEETING ROOM DIALOG ========== */}
            <Modal
                title="Tạo Phòng Họp"
                visible={showMeetingDlg}
                onCancel={() => setShowMeetingDlg(false)}
                footer={null}
                width={500}
            >
                <Form onSubmit={handleCreateMeeting} labelPosition="top">
                    <Form.Input field="name" label="Tên phòng họp" rules={[{ required: true }]} />
                    <Form.Input field="department" label="Phòng ban" placeholder="IT, HR, Sales..." />
                    <Form.TextArea field="description" label="Mô tả" />
                    <Form.Select field="default_language" label="Ngôn ngữ" initValue="vi"
                        optionList={[
                            { value: 'vi', label: '🇻🇳 Tiếng Việt' },
                            { value: 'en', label: '🇺🇸 English' },
                            { value: 'multi', label: '🌐 Đa ngôn ngữ' },
                        ]}
                    />
                    <div className="flex justify-end gap-2 mt-4">
                        <Button onClick={() => setShowMeetingDlg(false)}>Huỷ</Button>
                        <Button htmlType="submit" theme="solid" type="primary">Tạo</Button>
                    </div>
                </Form>
            </Modal>
        </div>
    );
};

export default FeatureModulesPanel;
