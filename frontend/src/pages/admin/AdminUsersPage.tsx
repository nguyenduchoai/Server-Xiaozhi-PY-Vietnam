import { useState, useEffect } from "react";
import { Crown, Shield } from "lucide-react";
import { toast } from "sonner";
import {
  Button,
  Card,
  Input,
  Modal,
  Table,
  Select,
  RadioGroup,
  Radio,
  Tag,
  Typography,
  Empty
} from "@douyinfe/semi-ui";
import { IconSearch, IconUserAdd, IconEdit, IconDelete, IconUndo, IconKey } from "@douyinfe/semi-icons";
import { adminApi, subscriptionApi } from "@/services/subscriptionService";
import { UserRole, UserRoleLabels, UserRoleDescriptions } from "@/types/user-role";


interface User {
  id: string;
  name: string;
  email: string;
  is_superuser: boolean;
  is_deleted: boolean;
  created_at: string;
  timezone?: string;
  role?: string;
}

interface SubscriptionPlan {
  id: number;
  name: string;
  display_name: string;
}

const { Text, Title } = Typography;

export function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [showDeleted, setShowDeleted] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Delete dialog
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deletingUser, setDeletingUser] = useState<User | null>(null);
  const [deleteError, setDeleteError] = useState("");

  // Password reset dialog
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [passwordUser, setPasswordUser] = useState<User | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");

  // Create user dialog
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: "",
    email: "",
    password: "",
    role: UserRole.USER as typeof UserRole.USER | typeof UserRole.ADMIN | typeof UserRole.SUPER_ADMIN
  });

  // Edit dialog
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editForm, setEditForm] = useState({ name: "", email: "", timezone: "", role: UserRole.USER as UserRole });

  // Assign subscription dialog
  const [showAssignDialog, setShowAssignDialog] = useState(false);
  const [assigningUser, setAssigningUser] = useState<User | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<string>("");
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("monthly");
  const [durationDays, setDurationDays] = useState<string>("30");

  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const usersRes = await adminApi.getUsers({ page_size: 100 });
      setUsers(usersRes.data || []);
      setPlans([]);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Không thể tải dữ liệu");
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDeleted = showDeleted ? true : !user.is_deleted;
    return matchesSearch && matchesDeleted;
  });



  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return "N/A";
    return date.toLocaleDateString('vi-VN');
  };

  // Handle create user
  const handleCreateClick = () => {
    setCreateForm({ name: "", email: "", password: "", role: UserRole.USER });
    setShowCreateDialog(true);
  };

  const handleSaveCreate = async () => {
    if (!createForm.name || !createForm.email || !createForm.password) {
      toast.error("Vui lòng điền đầy đủ thông tin");
      return;
    }

    setProcessing(true);
    try {
      await adminApi.createUser(createForm);
      toast.success(`Đã tạo người dùng ${createForm.name} với vai trò ${UserRoleLabels[createForm.role]}`);
      setShowCreateDialog(false);
      loadData();
    } catch (error: any) {
            const detail = error.response?.data?.detail;
      let errMsg = "Không thể tạo người dùng";
      if (typeof detail === 'string') {
        errMsg = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        errMsg = detail[0].msg;
      }
      toast.error(errMsg);
    } finally {
      setProcessing(false);
    }
  };

  // Handle edit user
  const handleEditClick = (user: User) => {
    setEditingUser(user);
    setEditForm({
      name: user.name,
      email: user.email,
      timezone: user.timezone || "",
      role: (user.role as UserRole) || UserRole.USER
    });
    setShowEditDialog(true);
  };

  const handleSaveEdit = async () => {
    if (!editingUser) return;

    setProcessing(true);
    try {
      const payload: any = {
        name: editForm.name,
        email: editForm.email,
        timezone: editForm.timezone || undefined,
        role: editForm.role
      };

      await adminApi.updateUser(editingUser.id, payload);
      toast.success(`Đã cập nhật thông tin người dùng ${editForm.name}`);
      setShowEditDialog(false);
      loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Không thể cập nhật người dùng");
    } finally {
      setProcessing(false);
    }
  };

  // Handle delete user
  const handleDelete = async (user: User) => {
    setDeleteError("");
    try {
      await adminApi.deleteUser(user.id, false);
      // Success: Close dialog and reload (User disappears)
      setShowDeleteDialog(false);
      loadData();
    } catch (error: any) {
      console.error("Delete error:", error);
      setDeleteError(error.response?.data?.detail || "Không thể xóa người dùng");
    }
  };

  // Handle restore user
  const handleRestore = async (user: User) => {
    try {
      await adminApi.restoreUser(user.id);
      toast.success(`Đã khôi phục người dùng ${user.name}`);
      loadData();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Không thể khôi phục người dùng");
    }
  };

  // Handle password reset click
  const handlePasswordClick = (user: User) => {
    setPasswordUser(user);
    setNewPassword("");
    setPasswordError("");
    setPasswordSuccess("");
    setShowPasswordDialog(true);
  };

  // Handle password reset submit
  const handlePasswordReset = async () => {
    if (!passwordUser) return;

    setPasswordError("");
    setPasswordSuccess("");

    if (!newPassword || newPassword.length < 8) {
      setPasswordError("Mật khẩu phải có ít nhất 8 ký tự");
      return;
    }

    setProcessing(true);
    try {
      const result = await adminApi.resetUserPassword(passwordUser.id, newPassword);
      setPasswordSuccess(result.message || "Đã đặt lại mật khẩu thành công!");
      // Don't close dialog immediately - show success message
    } catch (error: any) {
            const detail = error.response?.data?.detail;
      let errMsg = "Không thể đặt lại mật khẩu";
      if (typeof detail === 'string') {
        errMsg = detail;
      } else if (Array.isArray(detail) && detail.length > 0) {
        errMsg = detail[0].msg;
      }
      setPasswordError(errMsg);
    } finally {
      setProcessing(false);
    }
  };

  // Handle assign subscription
  const handleAssignClick = (user: User) => {
    setAssigningUser(user);
    setSelectedPlanId("");
    setBillingCycle("monthly");
    setDurationDays("30");
    setShowAssignDialog(true);
  };

  const handleAssignPlan = async () => {
    if (!assigningUser || !selectedPlanId) return;

    setProcessing(true);
    try {
      await adminApi.assignSubscription(assigningUser.id, {
        plan_id: parseInt(selectedPlanId),
        billing_cycle: billingCycle,
        duration_days: parseInt(durationDays)
      });
      toast.success(`Đã gán gói ${plans.find(p => p.id.toString() === selectedPlanId)?.display_name} cho ${assigningUser.name}`);
      setShowAssignDialog(false);
      setAssigningUser(null);
      setSelectedPlanId("");
    } catch (error: any) {
      const errorDetail = error.response?.data?.detail;
      const errorMessage = typeof errorDetail === 'string'
        ? errorDetail
        : typeof errorDetail === 'object'
          ? JSON.stringify(errorDetail)
          : "Không thể gán gói subscription";
      toast.error(errorMessage);
    } finally {
      setProcessing(false);
    }
  };

  // Helper to get role badge
  const getRoleBadge = (user: User) => {
    const role = user.role || (user.is_superuser ? "super_admin" : "user");

    if (role === "super_admin") {
      return (
        <Tag color="purple" style={{ marginLeft: 8 }} type="light">
          <div className="flex items-center gap-1">
            <Crown size={12} />
            {UserRoleLabels[UserRole.SUPER_ADMIN]}
          </div>
        </Tag>
      );
    }

    if (role === "admin") {
      return (
        <Tag color="blue" style={{ marginLeft: 8 }} type="light">
          <div className="flex items-center gap-1">
            <Shield size={12} />
            {UserRoleLabels[UserRole.ADMIN]}
          </div>
        </Tag>
      );
    }

    return null;
  };

  const columns = [
    {
      title: 'Người dùng',
      dataIndex: 'name',
      render: (text: string, record: User) => (
        <div>
          <div className="flex items-center">
            <Text strong>{text}</Text>
            {record.is_deleted && <Tag size="small" style={{ marginLeft: 8 }}>Deleted</Tag>}
            {getRoleBadge(record)}
          </div>
        </div>
      )
    },
    {
      title: 'Email',
      dataIndex: 'email',
      render: (text: string) => <Text type="secondary">{text}</Text>
    },
    {
      title: 'Timezone',
      dataIndex: 'timezone',
      render: (text: string) => text || "—"
    },
    {
      title: 'Ngày tạo',
      dataIndex: 'created_at',
      render: (text: string) => formatDate(text)
    },
    {
      title: 'Thao tác',
      key: 'actions',
      render: (_: any, record: User) => (
        <div className="flex justify-end gap-2">
          {record.is_deleted ? (
            <Button
              icon={<IconUndo />}
              theme="light"
              onClick={() => handleRestore(record)}
            >
              Khôi phục
            </Button>
          ) : (
            <>
              <Button
                icon={<IconEdit />}
                theme="borderless"
                onClick={() => handleEditClick(record)}
              />
              <Button
                icon={<IconKey />}
                theme="borderless"
                onClick={() => handlePasswordClick(record)}
                title="Đổi mật khẩu"
              />
              <Button
                icon={<IconDelete />}
                theme="borderless"
                type="danger"
                onClick={() => {
                  setDeletingUser(record);
                  setDeleteError("");
                  setShowDeleteDialog(true);
                }}
              />
            </>
          )}
        </div>
      )
    }
  ];

  return (
    <div className="space-y-6 p-6">
      <div className="flex justify-between items-center">
        <div>
          <Title heading={3} style={{ margin: 0 }}>Quản lý Người dùng</Title>
          <Text type="secondary">Quản lý thông tin và subscription của người dùng</Text>
        </div>
        <Button onClick={handleCreateClick} icon={<IconUserAdd />} theme="solid">
          Thêm người dùng
        </Button>
      </div>

      <Card bodyStyle={{ padding: 16 }}>
        <div className="flex justify-between items-center gap-4">
          <Input
            prefix={<IconSearch />}
            placeholder="Tìm kiếm theo email hoặc tên..."
            value={searchQuery}
            onChange={(v) => setSearchQuery(v)}
            showClear
            style={{ flex: 1 }}
          />
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="showDeleted"
              checked={showDeleted}
              onChange={(e) => setShowDeleted(e.target.checked)}
              style={{ cursor: 'pointer' }}
            />
            <label htmlFor="showDeleted" style={{ cursor: 'pointer', userSelect: 'none' }}>Hiển thị đã xóa</label>
          </div>
        </div>
      </Card>

      <Card bodyStyle={{ padding: 0 }}>
        <Table
          columns={columns}
          dataSource={filteredUsers}
          pagination={{ pageSize: 10 }}
          loading={loading}
          empty={<Empty title={loading ? "" : "Không tìm thấy người dùng"} />}
        />
      </Card>

      <Modal
        visible={showCreateDialog}
        onCancel={() => setShowCreateDialog(false)}
        title="Thêm Người dùng mới"
        onOk={handleSaveCreate}
        confirmLoading={processing}
        okText="Tạo"
        cancelText="Hủy"
        okButtonProps={{ disabled: !createForm.name || !createForm.email || !createForm.password }}
        centered
      >
        <div className="space-y-4">
          <Text size="small" type="secondary">
            Tạo tài khoản mới. Người dùng sẽ được gán gói FREE mặc định.
          </Text>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Tên *</Text>
            <Input
              value={createForm.name}
              onChange={(v) => setCreateForm({ ...createForm, name: v })}
              placeholder="Nguyễn Văn A"
            />
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Email *</Text>
            <Input
              value={createForm.email}
              onChange={(v) => setCreateForm({ ...createForm, email: v })}
              placeholder="user@example.com"
            />
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Mật khẩu *</Text>
            <Input
              type="password"
              value={createForm.password}
              onChange={(v) => setCreateForm({ ...createForm, password: v })}
              placeholder="Ít nhất 8 ký tự: hoa, thường, số, đặc biệt"
            />
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Vai trò *</Text>
            <Select
              value={createForm.role}
              onChange={(v) => setCreateForm({ ...createForm, role: v as any })}
              style={{ width: '100%' }}
              optionList={[
                { value: UserRole.USER, label: `👤 ${UserRoleLabels[UserRole.USER]}` },
                { value: UserRole.ADMIN, label: `🛡️ ${UserRoleLabels[UserRole.ADMIN]}` },
                { value: UserRole.SUPER_ADMIN, label: `👑 ${UserRoleLabels[UserRole.SUPER_ADMIN]}` },
              ]}
            />
            <Text size="small" type="secondary" style={{ marginTop: 4, display: 'block' }}>
              {UserRoleDescriptions[createForm.role as UserRole]}
            </Text>
          </div>
        </div>
      </Modal>

      <Modal
        visible={showEditDialog}
        onCancel={() => setShowEditDialog(false)}
        title="Chỉnh sửa Người dùng"
        onOk={handleSaveEdit}
        confirmLoading={processing}
        okText="Lưu"
        cancelText="Hủy"
        centered
      >
        <div className="space-y-4">
          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Tên</Text>
            <Input
              value={editForm.name}
              onChange={(v) => setEditForm({ ...editForm, name: v })}
            />
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Email</Text>
            <Input
              value={editForm.email}
              onChange={(v) => setEditForm({ ...editForm, email: v })}
            />
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Vai trò</Text>
            <Select
              value={editForm.role}
              onChange={(v) => setEditForm({ ...editForm, role: v as UserRole })}
              style={{ width: '100%' }}
              optionList={[
                { value: UserRole.USER, label: `👤 ${UserRoleLabels[UserRole.USER]}` },
                { value: UserRole.ADMIN, label: `🛡️ ${UserRoleLabels[UserRole.ADMIN]}` },
                { value: UserRole.SUPER_ADMIN, label: `👑 ${UserRoleLabels[UserRole.SUPER_ADMIN]}` },
              ]}
            />
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Timezone</Text>
            <Select
              value={editForm.timezone || "UTC"}
              onChange={(v) => setEditForm({ ...editForm, timezone: v as string })}
              style={{ width: '100%' }}
              optionList={[
                { value: "UTC", label: "UTC (Giờ quốc tế)" },
                { value: "Asia/Ho_Chi_Minh", label: "Asia/Ho_Chi_Minh (Việt Nam)" },
                { value: "Asia/Bangkok", label: "Asia/Bangkok (Thái Lan)" },
                { value: "Asia/Singapore", label: "Asia/Singapore" },
                { value: "Asia/Tokyo", label: "Asia/Tokyo (Nhật Bản)" },
                { value: "America/New_York", label: "America/New_York (US East)" },
                { value: "America/Los_Angeles", label: "America/Los_Angeles (US West)" },
                { value: "Europe/London", label: "Europe/London (UK)" },
                { value: "Europe/Paris", label: "Europe/Paris (EU)" },
              ]}
            />
          </div>
        </div>
      </Modal>

      <Modal
        visible={showAssignDialog}
        onCancel={() => setShowAssignDialog(false)}
        title="Gán Subscription Plan"
        onOk={handleAssignPlan}
        confirmLoading={processing}
        okText="Xác nhận"
        cancelText="Hủy"
        okButtonProps={{ disabled: !selectedPlanId }}
        centered
      >
        <div className="space-y-4">
          <div className="bg-gray-50 p-3 rounded">
            <Text strong style={{ display: 'block' }}>{assigningUser?.name}</Text>
            <Text type="secondary" size="small">{assigningUser?.email}</Text>
          </div>

          <div>
            <Text strong style={{ display: 'block', marginBottom: 4 }}>Chọn gói mới</Text>
            <Select
              value={selectedPlanId}
              onChange={(v) => setSelectedPlanId(v as string)}
              style={{ width: '100%' }}
              placeholder="Chọn gói..."
              optionList={plans.map(p => ({ value: p.id.toString(), label: p.display_name }))}
            />
          </div>

          {selectedPlanId && selectedPlanId !== "1" && (
            <>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>Chu kỳ thanh toán</Text>
                <RadioGroup
                  value={billingCycle}
                  onChange={(e) => setBillingCycle(e.target.value as any)}
                  direction="horizontal"
                >
                  <Radio value="monthly">Hàng tháng</Radio>
                  <Radio value="yearly">Hàng năm</Radio>
                </RadioGroup>
              </div>

              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Thời hạn (ngày)</Text>
                <Select
                  value={durationDays}
                  onChange={(v) => setDurationDays(v as string)}
                  style={{ width: '100%' }}
                  optionList={[
                    { value: "30", label: "30 ngày (1 tháng)" },
                    { value: "90", label: "90 ngày (3 tháng)" },
                    { value: "180", label: "180 ngày (6 tháng)" },
                    { value: "365", label: "365 ngày (1 năm)" },
                  ]}
                />
              </div>
            </>
          )}
        </div>
      </Modal>

      <Modal
        visible={showDeleteDialog}
        onCancel={() => setShowDeleteDialog(false)}
        title="Xác nhận xóa"
        onOk={() => { if (deletingUser) handleDelete(deletingUser); }}
        okText="Xóa"
        cancelText="Hủy"
        okType="danger"
        centered
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <Text>
            Bạn có chắc muốn xóa người dùng <Text strong>{deletingUser?.name}</Text>?
            (Soft delete)
          </Text>
          {deleteError && (
            <Text type="danger" style={{ fontWeight: 'bold' }}>Lỗi: {deleteError}</Text>
          )}
        </div>
      </Modal>

      {/* Password Reset Modal */}
      <Modal
        visible={showPasswordDialog}
        onCancel={() => {
          setShowPasswordDialog(false);
          setPasswordSuccess("");
          setPasswordError("");
        }}
        title="Đổi Mật Khẩu"
        onOk={handlePasswordReset}
        okText={passwordSuccess ? "Đóng" : "Đổi Mật Khẩu"}
        cancelText="Hủy"
        confirmLoading={processing}
        centered
        footer={
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            {!passwordSuccess ? (
              <>
                <Button onClick={() => setShowPasswordDialog(false)} disabled={processing}>Hủy</Button>
                <Button theme="solid" type="primary" onClick={handlePasswordReset} loading={processing}>Đổi Mật Khẩu</Button>
              </>
            ) : (
              <Button theme="solid" onClick={() => setShowPasswordDialog(false)}>Đóng</Button>
            )}
          </div>
        }
      >
        <div className="space-y-4">
          <div className="bg-gray-50 p-3 rounded">
            <Text strong style={{ display: 'block' }}>{passwordUser?.name}</Text>
            <Text type="secondary" size="small">{passwordUser?.email}</Text>
          </div>

          {!passwordSuccess ? (
            <>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>Mật khẩu mới</Text>
                <Input
                  type="password"
                  value={newPassword}
                  onChange={(v) => setNewPassword(v)}
                  placeholder="Tối thiểu 8 ký tự"
                  size="large"
                />
              </div>

              {passwordError && (
                <div style={{
                  background: "#ffebee",
                  border: "1px solid #f44336",
                  borderRadius: 8,
                  padding: "10px 14px",
                  color: "#c62828",
                }}>
                  {passwordError}
                </div>
              )}

              <Text type="tertiary" size="small">
                Sau khi đổi mật khẩu, bạn cần gửi mật khẩu mới cho người dùng qua email hoặc tin nhắn.
              </Text>
            </>
          ) : (
            <div style={{
              background: "#e8f5e9",
              border: "1px solid #4caf50",
              borderRadius: 8,
              padding: "16px",
              textAlign: "center",
            }}>
              <Text style={{ color: "#2e7d32", fontWeight: 600 }}>
                ✅ {passwordSuccess}
              </Text>
              <div style={{ marginTop: 8 }}>
                <Text type="secondary" size="small">
                  Mật khẩu mới: <Text code copyable>{newPassword}</Text>
                </Text>
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}

export default AdminUsersPage;
