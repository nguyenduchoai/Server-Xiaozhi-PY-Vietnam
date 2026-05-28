
import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Modal, Form, Upload, Button, Toast } from "@douyinfe/semi-ui";
import { IconUpload } from "@douyinfe/semi-icons";
import apiClient from "@config/axios-instance";
import type { Device } from "@types";

export interface EditDeviceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  device: Device | null;
  onSubmit: (data: { device_name?: string; board?: string; status?: string; background_image_url?: string; features?: Record<string, boolean> }) => Promise<void>;
  isLoading?: boolean;
}

export function EditDeviceDialog({
  open,
  onOpenChange,
  device,
  onSubmit,
  isLoading = false,
}: EditDeviceDialogProps) {
  const { t } = useTranslation("devices");
  const [formApi, setFormApi] = useState<any>();

  // Reset form when device changes
  useEffect(() => {
    if (device && formApi) {
      formApi.setValues({
        device_name: device.device_name || "",
        board: device.board || "",
        status: device.status || "",
        mac_address: device.mac_address || "",
        background_image_url: device.background_image_url || "",
        features: device.features || { sales: true, banner: true },
      });
    }
  }, [device, formApi]);

  const handleSubmit = async (values: any) => {
    try {
      await onSubmit({
        device_name: values.device_name || undefined,
        board: values.board || undefined,
        status: values.status || undefined,
        background_image_url: values.background_image_url || "",
        features: values.features,
      });
      onOpenChange(false);
    } catch {
      // Error handled by parent
    }
  };

  const boardOptions = [
    { value: "ESP32", label: "ESP32" },
    { value: "ESP32-S3", label: "ESP32-S3" },
    { value: "ESP32-C3", label: "ESP32-C3" },
    { value: "ESP8266", label: "ESP8266" },
    { value: "Raspberry Pi", label: "Raspberry Pi" },
    { value: "Arduino", label: "Arduino" },
    { value: "Other", label: t("other", "Khác") },
  ];

  const statusOptions = [
    { value: "active", label: t("status_active", "Hoạt động") },
    { value: "inactive", label: t("status_inactive", "Không hoạt động") },
    { value: "offline", label: t("status_offline", "Ngoại tuyến") },
    { value: "pending", label: t("status_pending", "Đang chờ") },
  ];

  return (
    <Modal
      title={t("edit_device", "Chỉnh sửa thiết bị")}
      visible={open}
      onCancel={() => onOpenChange(false)}
      onOk={() => formApi?.submitForm()}
      confirmLoading={isLoading}
      okText={t("save", "Lưu")}
      cancelText={t("cancel", "Hủy")}
    >
      <div style={{ marginBottom: 12 }}>
        {t("edit_device_description", "Cập nhật thông tin thiết bị của bạn")}
      </div>
      <Form getFormApi={setFormApi} onSubmit={handleSubmit} labelPosition="top">
        <Form.Input
          field="device_name"
          label={t("device_name", "Tên thiết bị")}
          placeholder={t("device_name_placeholder", "Nhập tên thiết bị")}
          disabled={isLoading}
        />
        <Form.Select
          field="board"
          label={t("board", "Loại board")}
          placeholder={t("select_board", "Chọn loại board")}
          optionList={boardOptions}
          disabled={isLoading}
        />
        <Form.Select
          field="status"
          label={t("device_status", "Trạng thái")}
          placeholder={t("select_status", "Chọn trạng thái")}
          optionList={statusOptions}
          disabled={isLoading}
        />
        <Form.Slot label={t("background_image_url", "Ảnh nền thiết bị (Nhập URL hoặc Upload)")} style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
            <Form.Input
              field="background_image_url"
              placeholder={t("bg_url_placeholder", "Nhập URL hình ảnh nền...")}
              disabled={isLoading}
              style={{ flex: 1 }}
              noLabel
            />
            {device && (
              <Upload
                action=""
                accept="image/*"
                showUploadList={false}
                customRequest={async ({ file, onProgress, onSuccess, onError }) => {
                  try {
                    const formData = new FormData();
                    formData.append("file", file.fileInstance);
                    formData.append("background_type", "idle");
                    // Most users using Meeting firmware have 800x480 displays
                    formData.append("screen_type", "800x480"); 

                    const res = await apiClient.post(`/devices/${device.id}/backgrounds/upload`, formData, {
                      headers: { "Content-Type": "multipart/form-data" },
                      onUploadProgress: (e) => {
                        if (e.total && onProgress) {
                          onProgress({ percent: Math.round((e.loaded * 100) / e.total) });
                        }
                      }
                    });

                    if (res.data?.success) {
                      formApi?.setValue("background_image_url", res.data.background.file_url);
                      Toast.success("Tải ảnh lên thành công");
                      if (onSuccess) onSuccess(res.data);
                    } else {
                      throw new Error("Upload failed");
                    }
                  } catch (err: any) {
                    Toast.error(err?.response?.data?.detail || "Lỗi upload ảnh");
                    if (onError) onError(err);
                  }
                  return { abort: () => {} };
                }}
              >
                <Button icon={<IconUpload />} theme="light">Upload</Button>
              </Upload>
            )}
          </div>
        </Form.Slot>
        <Form.Input
          field="mac_address"
          label={t("mac_address", "Địa chỉ MAC")}
          disabled
          style={{ fontFamily: 'monospace' }}
        />
        
        <div style={{ marginTop: 16, marginBottom: 8, fontWeight: 500 }}>
          Tính năng thiết bị
        </div>
        <div style={{ display: 'flex', gap: 24 }}>
          <Form.Switch
            field="features.sales"
            label="Hiển thị AI Sales"
          />
          <Form.Switch
            field="features.banner"
            label="Hiển thị Quảng Cáo"
          />
        </div>
      </Form>
    </Modal>
  );
}
