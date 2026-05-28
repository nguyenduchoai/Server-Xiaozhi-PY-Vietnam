import { toast } from "sonner";
import { useState, useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Package,
  Upload,
  Clock,
  Rocket,
  Pause,
  X,
  CheckCircle,
  AlertCircle,
  Loader2
} from "lucide-react";

import { PageHead } from "@/components";
import {
  Button,
  Card,
  Table,
  Tabs,
  TabPane,
  Tag,
  Modal,
  Form,
  
  Empty,
  Skeleton,
  Popconfirm,
  Typography
} from "@douyinfe/semi-ui";
import {
  IconUpload,
  IconDelete,
  IconPlay,
  IconPause,
  IconClose,
  IconDownload,
  IconHistory
} from "@douyinfe/semi-icons";

import {
  useFirmwareList,
  useUploadFirmware,
  useDeleteFirmware,
  useDeploymentList,
  useCreateDeployment,
  useUpdateDeployment,
} from "@/queries/firmware-queries";
import type {
  Firmware,
  Deployment,
  BoardType,
  DeploymentStatus,
  DeploymentTargetType,
} from "@/services/firmwareService";
import { firmwareService } from "@/services/firmwareService";

const { Text, Title } = Typography;

const DEFAULT_PAGE_SIZE = 10;

// ============ Helper Functions ============

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("vi-VN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getStatusBadge(status: DeploymentStatus) {
  const statusConfig: Record<DeploymentStatus, { color: "grey" | "blue" | "green" | "orange" | "red"; icon: React.ReactNode; label: string }> = {
    pending: { color: "grey", icon: <Clock className="h-3 w-3" />, label: "Chờ xử lý" },
    rolling_out: { color: "blue", icon: <Loader2 className="h-3 w-3 animate-spin" />, label: "Đang triển khai" },
    completed: { color: "green", icon: <CheckCircle className="h-3 w-3" />, label: "Hoàn thành" },
    paused: { color: "orange", icon: <Pause className="h-3 w-3" />, label: "Tạm dừng" },
    cancelled: { color: "grey", icon: <X className="h-3 w-3" />, label: "Đã hủy" },
    failed: { color: "red", icon: <AlertCircle className="h-3 w-3" />, label: "Thất bại" },
  };

  const config = statusConfig[status];
  return (
    <Tag color={config.color} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      {config.icon}
      {config.label}
    </Tag>
  );
}

function getBoardTypeLabel(boardType: BoardType): string {
  const labels: Record<BoardType, string> = {
    esp32: "ESP32",
    esp32s3: "ESP32-S3",
    esp32c3: "ESP32-C3",
    all: "Tất cả",
  };
  return labels[boardType] || boardType;
}

// ============ Upload Dialog Component ============

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

function UploadFirmwareDialog({ open, onOpenChange, onSuccess }: UploadDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const { mutateAsync: uploadFirmware, isPending } = useUploadFirmware();


  const handleSubmit = async (values: any) => {
    if (!file) {
      toast.error("Vui lòng chọn file firmware");
      return;
    }

    try {
      await uploadFirmware({
        file,
        version: values.version,
        board_type: values.boardType,
        release_notes: values.releaseNotes,
        is_active: true,
      });

      toast.success("Upload thành công!");
      setFile(null);
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      console.error("Upload failed:", error);
      toast.error(error instanceof Error ? error.message : "Upload thất bại");
    }
  };

  return (
    <Modal
      visible={open}
      onCancel={() => onOpenChange(false)}
      title={
        <div className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload Firmware
        </div>
      }
      footer={null}
      width={500}
    >
      <Form onSubmit={handleSubmit} labelPosition="top">
        <div className="mb-4">
          <Text strong style={{ display: 'block', marginBottom: 4 }}>File firmware (.bin, .elf)</Text>
          <input
            type="file"
            accept=".bin,.elf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-500
                        file:mr-4 file:py-2 file:px-4
                        file:rounded-full file:border-0
                        file:text-sm file:font-semibold
                        file:bg-blue-50 file:text-blue-700
                        hover:file:bg-blue-100"
          />
          {file && (
            <Text size="small" type="secondary" style={{ marginTop: 4, display: 'block' }}>
              {file.name} ({formatFileSize(file.size)})
            </Text>
          )}
        </div>

        <Form.Input
          field="version"
          label="Version"
          placeholder="Ví dụ: 1.2.0"
          rules={[{ required: true, message: 'Vui lòng nhập version' }]}
        />

        <Form.Select
          field="boardType"
          label="Board Type"
          initValue="all"
          style={{ width: '100%' }}
        >
          <Form.Select.Option value="all">Tất cả</Form.Select.Option>
          <Form.Select.Option value="esp32">ESP32</Form.Select.Option>
          <Form.Select.Option value="esp32s3">ESP32-S3</Form.Select.Option>
          <Form.Select.Option value="esp32c3">ESP32-C3</Form.Select.Option>
        </Form.Select>

        <Form.TextArea
          field="releaseNotes"
          label="Release Notes (tùy chọn)"
          placeholder="Mô tả các thay đổi trong phiên bản này..."
          rows={3}
        />

        <div className="flex justify-end gap-2 mt-4">
          <Button type="tertiary" onClick={() => onOpenChange(false)}>Hủy</Button>
          <Button theme="solid" htmlType="submit" loading={isPending}>Upload</Button>
        </div>
      </Form>
    </Modal>
  );
}

// ============ Deploy Dialog Component ============

interface DeployDialogProps {
  firmware: Firmware | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

function DeployFirmwareDialog({ firmware, open, onOpenChange, onSuccess }: DeployDialogProps) {
  const { mutateAsync: createDeployment, isPending } = useCreateDeployment();
  const [targetType, setTargetType] = useState<DeploymentTargetType>("all");

  const handleSubmit = async (values: any) => {
    if (!firmware) return;

    try {
      await createDeployment({
        firmware_id: firmware.id,
        target_type: values.targetType,
        target_value: values.targetType !== "all" ? values.targetValue : undefined,
        rollout_percentage: values.rolloutPercentage,
      });

      toast.success("Triển khai thành công!");
      onOpenChange(false);
      onSuccess?.();
    } catch (error) {
      console.error("Deploy failed:", error);
      toast.error(error instanceof Error ? error.message : "Triển khai thất bại");
    }
  };

  return (
    <Modal
      visible={open}
      onCancel={() => onOpenChange(false)}
      title={
        <div className="flex items-center gap-2">
          <Rocket className="h-5 w-5" />
          Triển khai Firmware {firmware?.version}
        </div>
      }
      footer={null}
      width={500}
    >
      <Form onSubmit={handleSubmit} labelPosition="top">
        <Form.Select
          field="targetType"
          label="Đối tượng triển khai"
          initValue="all"
          style={{ width: '100%' }}
          onChange={(v) => setTargetType(v as DeploymentTargetType)}
        >
          <Form.Select.Option value="all">Tất cả thiết bị</Form.Select.Option>
          <Form.Select.Option value="board">Theo loại board</Form.Select.Option>
          <Form.Select.Option value="user">Theo user</Form.Select.Option>
          <Form.Select.Option value="device">Thiết bị cụ thể</Form.Select.Option>
        </Form.Select>

        {targetType !== "all" && (
          <Form.Input
            field="targetValue"
            label={
              targetType === "board" ? "Board type (esp32, esp32s3, esp32c3)" :
                targetType === "user" ? "User ID" :
                  "MAC addresses (phân cách bằng dấu phẩy)"
            }
            placeholder={
              targetType === "board" ? "esp32s3" :
                targetType === "user" ? "user-uuid" :
                  "aa:bb:cc:dd:ee:ff, 11:22:33:44:55:66"
            }
            rules={[{ required: true, message: 'Vui lòng nhập' }]}
          />
        )}

        <Form.Slider
          field="rolloutPercentage"
          label="Tỷ lệ triển khai (%)"
          initValue={100}
          min={1}
          max={100}
          showBoundary={false}
        />
        <Text size="small" type="tertiary" style={{ display: 'block', marginTop: -10, marginBottom: 20 }}>
          Điều chỉnh % thiết bị sẽ nhận bản cập nhật này
        </Text>

        <div className="flex justify-end gap-2 mt-4">
          <Button type="tertiary" onClick={() => onOpenChange(false)}>Hủy</Button>
          <Button theme="solid" htmlType="submit" loading={isPending}>Triển khai</Button>
        </div>
      </Form>
    </Modal>
  );
}

// ============ Firmware Table Component ============

interface FirmwareTableProps {
  firmwares: Firmware[];
  onDeploy: (firmware: Firmware) => void;
  onDelete: (firmware: Firmware) => void;
}

function FirmwareTable({ firmwares, onDeploy, onDelete }: FirmwareTableProps) {
  const columns = [
    {
      title: 'Version',
      dataIndex: 'version',
      render: (text: string, record: Firmware) => (
        <div className="flex items-center gap-2">
          <Text strong>{text}</Text>
          {record.is_latest && <Tag color="green" size="small">Latest</Tag>}
        </div>
      )
    },
    {
      title: 'Board',
      dataIndex: 'board_type',
      render: (text: BoardType) => getBoardTypeLabel(text)
    },
    {
      title: 'Size',
      dataIndex: 'size',
      render: (size: number) => formatFileSize(size)
    },
    {
      title: 'Downloads',
      dataIndex: 'download_count'
    },
    {
      title: 'Ngày tạo',
      dataIndex: 'created_at',
      render: (date: string) => formatDate(date)
    },
    {
      title: 'Trạng thái',
      dataIndex: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? "green" : "grey"}>{isActive ? "Active" : "Inactive"}</Tag>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Firmware) => (
        <div className="flex gap-2 justify-end">
          <Button
            icon={<IconDownload />}
            theme="borderless"
            onClick={() => window.open(firmwareService.getDownloadUrl(record.id), "_blank")}
          />
          <Button
            icon={<Rocket className="h-4 w-4" />}
            theme="light"
            disabled={!record.is_active}
            onClick={() => onDeploy(record)}
            title="Deploy"
          />
          <Popconfirm
            title="Bạn có chắc muốn xóa firmware này?"
            content="Hành động này không thể hoàn tác"
            onConfirm={() => onDelete(record)}
          >
            <Button icon={<IconDelete />} theme="borderless" type="danger" />
          </Popconfirm>
        </div>
      )
    }
  ];

  return (
    <Table
      columns={columns}
      dataSource={firmwares}
      pagination={false}
      empty={<Empty title="Chưa có firmware nào" />}
    />
  );
}

// ============ Deployment Table Component ============

interface DeploymentTableProps {
  deployments: Deployment[];
  onPause: (deployment: Deployment) => void;
  onResume: (deployment: Deployment) => void;
  onCancel: (deployment: Deployment) => void;
}

function DeploymentTable({ deployments, onPause, onResume, onCancel }: DeploymentTableProps) {
  const getTargetLabel = (deployment: Deployment) => {
    if (deployment.target_type === "all") return "Tất cả thiết bị";
    return `${deployment.target_type}: ${deployment.target_value}`;
  };

  const columns = [
    {
      title: 'Firmware',
      dataIndex: 'firmware_version',
      render: (text: string, record: Deployment) => text || record.firmware_id
    },
    {
      title: 'Đối tượng',
      key: 'target',
      render: (_: any, record: Deployment) => getTargetLabel(record)
    },
    {
      title: 'Tiến độ',
      key: 'progress',
      render: (_: any, record: Deployment) => (
        <div className="flex items-center gap-2">
          <Text type="success" strong>{record.deployed_count}</Text>
          {record.failed_count > 0 && <Text type="danger">/ {record.failed_count} failed</Text>}
          <Text type="tertiary">({record.rollout_percentage}%)</Text>
        </div>
      )
    },
    {
      title: 'Trạng thái',
      dataIndex: 'status',
      render: (status: DeploymentStatus) => getStatusBadge(status)
    },
    {
      title: 'Bắt đầu',
      dataIndex: 'started_at',
      render: (date: string) => date ? formatDate(date) : "-"
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Deployment) => (
        <div className="flex gap-2 justify-end">
          {record.status === "rolling_out" && (
            <Button icon={<IconPause />} theme="light" onClick={() => onPause(record)} />
          )}
          {record.status === "paused" && (
            <Button icon={<IconPlay />} theme="light" onClick={() => onResume(record)} />
          )}
          {(record.status === "pending" || record.status === "rolling_out" || record.status === "paused") && (
            <Popconfirm
              title="Hủy deployment?"
              onConfirm={() => onCancel(record)}
            >
              <Button icon={<IconClose />} theme="light" type="danger" />
            </Popconfirm>
          )}
        </div>
      )
    }
  ];

  return (
    <Table
      columns={columns}
      dataSource={deployments}
      pagination={false}
      empty={<Empty title="Chưa có deployment nào" />}
    />
  );
}

// ============ Main Page Component ============

export function FirmwareManagementPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState<"firmware" | "deployments">("firmware");
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [deployDialogOpen, setDeployDialogOpen] = useState(false);
  const [selectedFirmware, setSelectedFirmware] = useState<Firmware | null>(null);

  // Pagination
  const page = useMemo(() => {
    const p = searchParams.get("page");
    return p ? parseInt(p, 10) : 1;
  }, [searchParams]);

  // Queries
  const { data: firmwareData, isLoading: firmwareLoading, refetch: refetchFirmware } = useFirmwareList({
    page,
    page_size: DEFAULT_PAGE_SIZE,
  });

  const { data: deploymentData, isLoading: deploymentLoading, refetch: refetchDeployments } = useDeploymentList({
    page: 1,
    page_size: 20,
  });

  // Mutations
  const { mutateAsync: deleteFirmware } = useDeleteFirmware();
  const { mutateAsync: updateDeployment } = useUpdateDeployment();

  // Handlers
  const handlePageChange = useCallback((newPage: number) => {
    setSearchParams({ page: String(newPage) });
  }, [setSearchParams]);

  const handleDeploy = useCallback((firmware: Firmware) => {
    setSelectedFirmware(firmware);
    setDeployDialogOpen(true);
  }, []);

  const handleDelete = useCallback(async (firmware: Firmware) => {
    try {
      await deleteFirmware(firmware.id);
      toast.success("Xóa firmware thành công");
      refetchFirmware();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Xóa thất bại");
    }
  }, [deleteFirmware, refetchFirmware]);

  const handlePauseDeployment = useCallback(async (deployment: Deployment) => {
    try {
      await updateDeployment({ id: deployment.id, params: { status: "paused" } });
      refetchDeployments();
    } catch (error) {
      toast.error("Tạm dừng thất bại");
    }
  }, [updateDeployment, refetchDeployments]);

  const handleResumeDeployment = useCallback(async (deployment: Deployment) => {
    try {
      await updateDeployment({ id: deployment.id, params: { status: "rolling_out" } });
      refetchDeployments();
    } catch (error) {
      toast.error("Tiếp tục thất bại");
    }
  }, [updateDeployment, refetchDeployments]);

  const handleCancelDeployment = useCallback(async (deployment: Deployment) => {
    try {
      await updateDeployment({ id: deployment.id, params: { status: "cancelled" } });
      toast.success("Đã hủy deployment");
      refetchDeployments();
    } catch (error) {
      toast.error("Hủy thất bại");
    }
  }, [updateDeployment, refetchDeployments]);

  return (
    <div className="space-y-6 p-6">
      <PageHead
        title="Quản lý Firmware"
        description="Upload, quản lý và triển khai firmware đến thiết bị"
      />

      {/* Tabs */}
      <Tabs
        type="line"
        activeKey={activeTab}
        onChange={(v) => setActiveTab(v as "firmware" | "deployments")}
        tabBarExtraContent={
          activeTab === "firmware" && (
            <Button onClick={() => setUploadDialogOpen(true)} icon={<IconUpload />} theme="solid">
              Upload Firmware
            </Button>
          )
        }
      >
        <TabPane
          tab={
            <span>
              <Package className="h-4 w-4 mr-2" />
              Firmware
            </span>
          }
          itemKey="firmware"
        >
          <div className="mt-4">
            <Card
              title={<Title heading={6}>Danh sách Firmware</Title>}
              bodyStyle={{ padding: 0 }}
            >
              {firmwareLoading ? (
                <div className="p-4"><Skeleton placeholder={<Skeleton.Paragraph rows={5} />} loading={true} active /></div>
              ) : (
                <>
                  <FirmwareTable
                    firmwares={firmwareData?.items || []}
                    onDeploy={handleDeploy}
                    onDelete={handleDelete}
                  />
                  {/* Pagination */}
                  {firmwareData && firmwareData.total > DEFAULT_PAGE_SIZE && (
                    <div className="flex justify-end p-4 border-t border-gray-100">
                      {/* Use basic pagination buttons as placeholder for now, or Semi Pagination */}
                      <div className="flex gap-2">
                        <Button
                          disabled={page <= 1}
                          onClick={() => handlePageChange(page - 1)}
                        >
                          Previous
                        </Button>
                        <span className="flex items-center text-sm text-gray-500">
                          Page {page} / {Math.ceil(firmwareData.total / DEFAULT_PAGE_SIZE)}
                        </span>
                        <Button
                          disabled={page >= Math.ceil(firmwareData.total / DEFAULT_PAGE_SIZE)}
                          onClick={() => handlePageChange(page + 1)}
                        >
                          Next
                        </Button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </Card>
          </div>
        </TabPane>

        <TabPane
          tab={
            <span>
              <IconHistory style={{ marginRight: 8 }} />
              Deployments
            </span>
          }
          itemKey="deployments"
        >
          <div className="mt-4">
            <Card
              title={<Title heading={6}>Tiến độ triển khai</Title>}
              bodyStyle={{ padding: 0 }}
            >
              {deploymentLoading ? (
                <div className="p-4"><Skeleton placeholder={<Skeleton.Paragraph rows={5} />} loading={true} active /></div>
              ) : (
                <DeploymentTable
                  deployments={deploymentData?.items || []}
                  onPause={handlePauseDeployment}
                  onResume={handleResumeDeployment}
                  onCancel={handleCancelDeployment}
                />
              )}
            </Card>
          </div>
        </TabPane>
      </Tabs>

      {/* Dialogs */}
      <UploadFirmwareDialog
        open={uploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
        onSuccess={() => refetchFirmware()}
      />

      <DeployFirmwareDialog
        firmware={selectedFirmware}
        open={deployDialogOpen}
        onOpenChange={setDeployDialogOpen}
        onSuccess={() => {
          refetchDeployments();
          setActiveTab("deployments");
        }}
      />
    </div>
  );
}

export default FirmwareManagementPage;
