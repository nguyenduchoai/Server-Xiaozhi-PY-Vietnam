import { toast } from "sonner";

import { useMemo, useCallback, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { IconPlus, IconInfoCircle, IconCopy, IconServer } from "@douyinfe/semi-icons";
import { Button, Card, Typography, Banner, Empty, Row, Col, Pagination, Skeleton, Space, Tag, Modal } from "@douyinfe/semi-ui";

import { useDeviceList } from "@/hooks";
import { DeviceDetailCard, PageHead, BindDeviceDialog, EditDeviceDialog } from "@/components";
import { useActivateDevice, useDeleteDevice, useUpdateDevice } from "@/queries/device-queries";
import type { Device } from "@types";

const { Text, Title, Paragraph } = Typography;

const DEFAULT_PAGE_SIZE = 10;

export function DevicesPage() {
  const { t } = useTranslation(["devices", "common"]);
  const [searchParams, setSearchParams] = useSearchParams();
  const [isBindDialogOpen, setIsBindDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);

  // Get pagination from URL params
  const page = useMemo(() => {
    const p = searchParams.get("page");
    return p ? parseInt(p, 10) : 1;
  }, [searchParams]);

  const pageSize = useMemo(() => {
    const ps = searchParams.get("pageSize");
    return ps ? parseInt(ps, 10) : DEFAULT_PAGE_SIZE;
  }, [searchParams]);

  // Fetch devices with pagination
  const { data, isLoading, error, refetch } = useDeviceList({
    page,
    page_size: pageSize,
  });

  // Activate device mutation
  const { mutateAsync: activateDevice, isPending: isActivating } = useActivateDevice();

  // Delete device mutation
  const { mutateAsync: deleteDevice, isPending: isDeleting } = useDeleteDevice();

  // Update device mutation
  const { mutateAsync: updateDevice, isPending: isUpdating } = useUpdateDevice();

  // Navigation handlers
  const handlePageChange = useCallback((currentPage: number) => {
    setSearchParams({
      page: String(currentPage),
      pageSize: String(pageSize),
    });
  }, [pageSize, setSearchParams]);

  // Handle bind device submit
  const handleBindDeviceSubmit = async (formData: { code: string }) => {
    try {
      await activateDevice({ code: formData.code });
      refetch();
      toast.success(t("device_activated_desc", "Thiết bị đã được thêm vào hệ thống thành công"));
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : t("activation_error", "Có lỗi xảy ra khi kích hoạt thiết bị");
      toast.error(errorMsg);
      throw error;
    }
  };

  // Handle delete device
  const handleDeleteDevice = async (deviceId: string) => {
    Modal.confirm({
      title: t("confirm_delete_device", "Xác nhận xóa thiết bị"),
      content: t("confirm_delete_device_desc", "Thiết bị sẽ bị xóa vĩnh viễn khỏi hệ thống. Bạn có chắc chắn?"),
      okType: "danger",
      okText: t("common:delete", "Xóa"),
      cancelText: t("common:cancel", "Hủy"),
      centered: true,
      onOk: async () => {
        try {
          await deleteDevice(deviceId);
          refetch();
          toast.success(t("device_deleted", "Thiết bị đã được xóa thành công"));
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : t("delete_error", "Có lỗi xảy ra khi xóa thiết bị");
          toast.error(errorMsg);
        }
      },
    });
  };

  // Handle edit device
  const handleEditDevice = (device: Device) => {
    setEditingDevice(device);
    setIsEditDialogOpen(true);
  };

  // Handle edit device submit
  const handleEditDeviceSubmit = async (data: { device_name?: string; board?: string; status?: string; background_image_url?: string; features?: Record<string, boolean> }) => {
    if (!editingDevice) return;

    try {
      await updateDevice({ deviceId: editingDevice.id, payload: data });
      refetch();
      toast.success(t("device_updated", "Thiết bị đã được cập nhật thành công"));
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : t("update_error", "Có lỗi xảy ra khi cập nhật thiết bị");
      toast.error(errorMsg);
      throw error;
    }
  };

  // Calculate pagination info
  const total = data?.total ?? 0;

  // Render loading skeleton grid
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <Title heading={2}>{t("devices")}</Title>
          <Text type="secondary" className="mt-2">{t("devices_description")}</Text>
        </div>

        <Row gutter={[16, 16]}>
          {Array.from({ length: 3 }).map((_, i) => (
            <Col xs={24} sm={12} lg={8} key={i}>
              <Skeleton placeholder={<Skeleton.Image style={{ height: 200 }} />} active >
                <Skeleton.Paragraph rows={3} />
              </Skeleton>
            </Col>
          ))}
        </Row>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <Title heading={2}>{t("devices")}</Title>
          <Text type="secondary" className="mt-2 text-sm">{t("devices_description")}</Text>
        </div>

        <Banner
          type="danger"
          description={error instanceof Error ? error.message : t("error_loading_devices")}
        />
      </div>
    );
  }

  // Helper for OTA URL Copy
  const copyOtaUrl = () => {
    const url = `${window.location.origin}/api/ota`;
    navigator.clipboard.writeText(url);
    toast.success("Đã copy URL OTA vào clipboard!");
  }


  // Render content based on state
  const renderDialogs = () => (
    <>
      {/* Bind Device Dialog */}
      <BindDeviceDialog
        open={isBindDialogOpen}
        onOpenChange={setIsBindDialogOpen}
        onSubmit={handleBindDeviceSubmit}
        isLoading={isActivating}
      />

      {/* Edit Device Dialog */}
      <EditDeviceDialog
        open={isEditDialogOpen}
        onOpenChange={setIsEditDialogOpen}
        device={editingDevice}
        onSubmit={handleEditDeviceSubmit}
        isLoading={isUpdating}
      />
    </>
  );

  // Render empty state
  if (!data || data.data.length === 0) {
    return (
      <>
        <div className="space-y-6">
          <div>
            <Title heading={2}>{t("devices")}</Title>
            <Text type="secondary" className="mt-2 text-sm">{t("devices_description")}</Text>
          </div>

          {/* OTA Instruction Card */}
          <Card
            title={
              <div className="flex items-center gap-2">
                <IconInfoCircle style={{ color: 'var(--semi-color-primary)' }} />
                <Text strong>Hướng dẫn kết nối Firmware ESP32-S3</Text>
              </div>
            }
            headerLine={true}
            style={{ borderStyle: 'dashed', backgroundColor: 'var(--semi-color-bg-1)' }}
          >
            <div className="space-y-4">
              <div>
                <div style={{ marginBottom: 4 }}><Text strong>OTA URL (Firmware Update Endpoint):</Text></div>
                <Space>
                  <Text code>{typeof window !== "undefined" ? window.location.origin : ""}/api/ota</Text>
                  <Button icon={<IconCopy />} onClick={copyOtaUrl} theme="borderless" type="tertiary" />
                </Space>
              </div>
              <div>
                <Paragraph>Để thiết bị kết nối và quản lý được từ Dashboard này:</Paragraph>
                <ol className="list-decimal ml-5 space-y-1">
                  <li>Mở Source Code Firmware của thiết bị <strong>ESP32-S3</strong>.</li>
                  <li>Tìm biến cấu hình liên quan đến <strong>OTA URL</strong> (thường trong <code>config.h</code>, <code>main.cpp</code> hoặc <code>Kconfig.projbuild</code> đối với Xiaozhi).</li>
                  <li>Đổi giá trị URL thành đường dẫn ở trên.</li>
                  <li>Biên dịch và nạp (Upload) lại Firmware cho thiết bị.</li>
                </ol>
              </div>
            </div>
          </Card>

          {/* Empty State */}
          <Empty
            image={<IconServer style={{ fontSize: 48, color: 'var(--semi-color-text-2)' }} />}
            title={t("no_devices")}
            description={t("no_devices_description")}
            layout="vertical"
          >
            <Button theme="solid" type="primary" onClick={() => setIsBindDialogOpen(true)} icon={<IconPlus />}>
              {t("add_device", "Thêm thiết bị")}
            </Button>
          </Empty>
        </div>
        {renderDialogs()}
      </>
    );
  }

  // Render device grid
  return (
    <>
      <PageHead
        title="devices:page.title"
        description="devices:page.description"
        translateTitle
        translateDescription
      />
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <Title heading={2}>{t("devices")}</Title>
            <Text type="secondary" className="mt-2 text-sm">
              {t("devices_description")}
              {total > 0 && (
                <Tag color="blue" className="ml-2">
                  {total} {total === 1 ? t("device") : t("devices")}
                </Tag>
              )}
            </Text>
          </div>
          <Button onClick={() => setIsBindDialogOpen(true)} theme="solid" icon={<IconPlus />}>
            {t("add_device", "Thêm thiết bị")}
          </Button>
        </div>


        {/* OTA Instruction Card */}
        <Card
          title={
            <div className="flex items-center gap-2">
              <IconInfoCircle style={{ color: 'var(--semi-color-primary)' }} />
              <Text strong>Hướng dẫn kết nối Firmware ESP32-S3</Text>
            </div>
          }
          headerLine={true}
          style={{ borderStyle: 'dashed', backgroundColor: 'var(--semi-color-bg-1)' }}
        >
          <div className="space-y-4">
            <div>
              <div style={{ marginBottom: 4 }}><Text strong>OTA URL (Firmware Update Endpoint):</Text></div>
              <Space>
                <Text code>{typeof window !== "undefined" ? window.location.origin : ""}/api/ota</Text>
                <Button icon={<IconCopy />} onClick={copyOtaUrl} theme="borderless" type="tertiary" />
              </Space>
            </div>
            <div>
              <Paragraph>Để thiết bị kết nối và quản lý được từ Dashboard này:</Paragraph>
              <ol className="list-decimal ml-5 space-y-1">
                <li>Mở Source Code Firmware của thiết bị <strong>ESP32-S3</strong>.</li>
                <li>Tìm biến cấu hình liên quan đến <strong>OTA URL</strong> (thường trong <code>config.h</code>, <code>main.cpp</code> hoặc <code>Kconfig.projbuild</code> đối với Xiaozhi).</li>
                <li>Đổi giá trị URL thành đường dẫn ở trên.</li>
                <li>Biên dịch và nạp (Upload) lại Firmware cho thiết bị.</li>
              </ol>
            </div>
          </div>
        </Card>

        {/* Device Grid */}
        <Row gutter={[16, 16]}>
          {data.data.map((device) => (
            <Col xs={24} sm={12} lg={8} key={device.id}>
              <DeviceDetailCard
                device={device}
                isLoading={isDeleting || isUpdating}
                onEdit={() => handleEditDevice(device)}
                onDelete={handleDeleteDevice}
              />
            </Col>
          ))}
        </Row>

        {/* Pagination Controls */}
        {total > 0 && (
          <div className="flex justify-center mt-6">
            <Pagination
              total={total}
              currentPage={page}
              pageSize={pageSize}
              onPageChange={handlePageChange}
            />
          </div>
        )}
      </div>

      {renderDialogs()}
    </>
  );
}
