import { toast } from "sonner";
import { useState, useEffect } from "react";
import {
  Button,
  Card,
  Table,
  Modal,
  Input,
  TextArea,
  Tag,
  Popconfirm,
  
  Typography,
  Row,
  Col
} from "@douyinfe/semi-ui";
import { IconPlus, IconEdit, IconDelete } from "@douyinfe/semi-icons";
import { subscriptionApi, type SubscriptionPlan } from "@/services/subscriptionService";
import { apiClient } from "@/config/axios-instance";

const { Text, Title } = Typography;

interface PlanFormData {
  name: string;
  display_name: string;
  description: string;
  price_monthly: number;
  price_yearly: number | null;
  max_agents: number;
  max_devices: number;
  sort_order: number;
}

export function AdminPlansPage() {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingPlan, setEditingPlan] = useState<SubscriptionPlan | null>(null);
  const [formData, setFormData] = useState<PlanFormData>({
    name: "",
    display_name: "",
    description: "",
    price_monthly: 0,
    price_yearly: null,
    max_agents: 1,
    max_devices: 1,
    sort_order: 99,
  });
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    loadPlans();
  }, []);

  const loadPlans = async () => {
    try {
      const data = await subscriptionApi.getPlans();
      setPlans(data);
    } catch (error) {
      console.error("Failed to load plans:", error);
      toast.error("Không thể tải danh sách gói");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingPlan(null);
    setFormData({
      name: "",
      display_name: "",
      description: "",
      price_monthly: 0,
      price_yearly: null,
      max_agents: 1,
      max_devices: 1,
      sort_order: plans.length + 1,
    });
    setShowDialog(true);
  };

  const handleEdit = (plan: SubscriptionPlan) => {
    setEditingPlan(plan);
    setFormData({
      name: plan.name,
      display_name: plan.display_name,
      description: plan.description || "",
      price_monthly: plan.price_monthly,
      price_yearly: plan.price_yearly,
      max_agents: plan.max_agents,
      max_devices: plan.max_devices,
      sort_order: plan.sort_order,
    });
    setShowDialog(true);
  };

  const handleSave = async () => {
    if (!formData.name || !formData.display_name) {
      toast.warning("Vui lòng điền đầy đủ thông tin");
      return;
    }

    setProcessing(true);
    try {
      // Prepare full data with BYO defaults for unused fields
      const fullData = {
        ...formData,
        // BYO model: Set all usage limits to unlimited (-1)
        max_monthly_tokens: -1,
        max_knowledge_base_size_mb: -1,
        max_tts_minutes_monthly: -1,
        max_mcps: -1,
        max_templates: -1,
        max_tools: -1,
        // Enable all features by default
        enable_api_access: true,
        enable_webhook: true,
        enable_custom_branding: true,
        enable_priority_support: formData.name === "ENTERPRISE",
        allow_custom_providers: true,
        allowed_provider_types: null,
        allowed_provider_categories: null,
      };

      if (editingPlan) {
        await apiClient.put(`/admin/plans/${editingPlan.id}`, fullData);
        toast.success("Cập nhật gói thành công");
      } else {
        await apiClient.post("/admin/plans", fullData);
        toast.success("Tạo gói mới thành công");
      }
      setShowDialog(false);
      loadPlans();
    } catch (error: any) {
      console.error("Failed to save plan:", error);
      toast.error(error.response?.data?.detail || "Không thể lưu gói");
    } finally {
      setProcessing(false);
    }
  };

  const handleDelete = async (plan: SubscriptionPlan) => {
    try {
      await apiClient.delete(`/admin/plans/${plan.id}`);
      toast.success("Xóa gói thành công");
      loadPlans();
    } catch (error: any) {
      console.error("Failed to delete plan:", error);
      toast.error(error.response?.data?.detail || "Không thể xóa gói");
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  };

  const columns = [
    {
      title: 'Tên gói',
      dataIndex: 'name',
      render: (_: any, record: SubscriptionPlan) => (
        <div>
          <Text strong>{record.display_name}</Text>
          <div className="text-gray-500 text-sm">{record.name}</div>
          {record.description && (
            <div className="text-gray-400 text-xs mt-1">{record.description}</div>
          )}
        </div>
      )
    },
    {
      title: 'Giá tháng',
      dataIndex: 'price_monthly',
      render: (price: number) => <Text strong>{formatPrice(price)}</Text>
    },
    {
      title: 'Giá năm',
      dataIndex: 'price_yearly',
      render: (price: number | null) => price ? formatPrice(price) : "-"
    },
    {
      title: 'Max Agents',
      dataIndex: 'max_agents',
      render: (val: number) => <Tag>{val === -1 ? "∞" : val}</Tag>
    },
    {
      title: 'Max Devices',
      dataIndex: 'max_devices',
      render: (val: number) => <Tag>{val === -1 ? "∞" : val}</Tag>
    },
    {
      title: 'Thao tác',
      key: 'actions',
      render: (_: any, record: SubscriptionPlan) => (
        <div className="flex justify-end gap-2">
          <Button
            icon={<IconEdit />}
            theme="borderless"
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="Xác nhận xóa"
            content={`Bạn có chắc muốn xóa gói "${record.display_name}"?`}
            onConfirm={() => handleDelete(record)}
          >
            <Button
              icon={<IconDelete />}
              theme="borderless"
              type="danger"
            />
          </Popconfirm>
        </div>
      )
    }
  ];

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <Title heading={3} style={{ margin: 0 }}>Quản lý Gói Subscription</Title>
          <Text type="secondary">Mô hình BYO: Chỉ giới hạn số Devices và Agents</Text>
        </div>
        <Button onClick={handleCreate} icon={<IconPlus />} theme="solid">
          Tạo gói mới
        </Button>
      </div>

      <Card bodyStyle={{ padding: 0 }}>
        <Table
          columns={columns}
          dataSource={plans}
          pagination={false}
          loading={loading}
        />
      </Card>

      {/* Create/Edit Dialog */}
      <Modal
        visible={showDialog}
        onCancel={() => setShowDialog(false)}
        title={editingPlan ? "Sửa gói" : "Tạo gói mới"}
        onOk={handleSave}
        confirmLoading={processing}
        width={700}
        okText="Lưu"
        cancelText="Hủy"
        centered
      >
        <div className="space-y-4">
          <Text type="secondary" size="small">
            Điền thông tin gói subscription. Mô hình BYO: Chỉ giới hạn Devices & Agents.
          </Text>

          <Row gutter={16}>
            <Col span={12}>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>Tên gói (code) *</Text>
              <Input
                value={formData.name}
                onChange={(v) => setFormData({ ...formData, name: v.toUpperCase() })}
                placeholder="VD: PREMIUM"
              />
            </Col>
            <Col span={12}>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>Tên hiển thị *</Text>
              <Input
                value={formData.display_name}
                onChange={(v) => setFormData({ ...formData, display_name: v })}
                placeholder="Gói Premium"
              />
            </Col>
          </Row>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Mô tả</Text>
            <TextArea
              value={formData.description}
              onChange={(v) => setFormData({ ...formData, description: v })}
              placeholder="Mô tả chi tiết về gói..."
              rows={2}
            />
          </div>

          <Row gutter={16}>
            <Col span={12}>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>Giá tháng (VND)</Text>
              <Input
                type="number"
                value={formData.price_monthly}
                onChange={(v) => setFormData({ ...formData, price_monthly: parseInt(v) || 0 })}
              />
            </Col>
            <Col span={12}>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>Giá năm (VND, tùy chọn)</Text>
              <Input
                type="number"
                value={formData.price_yearly || ""}
                onChange={(v) => setFormData({ ...formData, price_yearly: v ? parseInt(v) : null })}
                placeholder="Để trống nếu không có"
              />
            </Col>
          </Row>

          <div className="border-t border-gray-100 pt-4 mt-2">
            <Text strong style={{ display: 'block', marginBottom: 12 }}>Giới hạn (nhập -1 cho Unlimited)</Text>
            <Row gutter={16}>
              <Col span={12}>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Max Agents (-1 = ∞)</Text>
                <Input
                  type="number"
                  value={formData.max_agents}
                  onChange={(v) => setFormData({ ...formData, max_agents: parseInt(v) || 0 })}
                />
              </Col>
              <Col span={12}>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Max Devices (-1 = ∞)</Text>
                <Input
                  type="number"
                  value={formData.max_devices}
                  onChange={(v) => setFormData({ ...formData, max_devices: parseInt(v) || 0 })}
                />
              </Col>
            </Row>
            <div className="mt-2 text-xs text-gray-500">
              💡 Mô hình BYO: Tokens, TTS, ASR tự động unlimited (user tự quản với key riêng)
            </div>
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Thứ tự hiển thị</Text>
            <Input
              type="number"
              value={formData.sort_order}
              onChange={(v) => setFormData({ ...formData, sort_order: parseInt(v) || 1 })}
              style={{ width: 100 }}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default AdminPlansPage;
