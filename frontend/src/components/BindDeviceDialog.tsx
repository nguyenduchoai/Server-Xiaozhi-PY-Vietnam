
import { memo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Modal, Form, Typography, Tabs, TabPane, Select, Input } from '@douyinfe/semi-ui';
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useDeviceList } from "@/queries/device-queries";

/**
 * Bind Device Form Schema
 */
const BindDeviceSchema = z.object({
  code: z
    .string()
    .min(1, "Device code is required")
    .min(6, "Device code must be at least 6 characters")
    .max(50, "Device code must not exceed 50 characters"),
});

type BindDeviceFormValues = z.infer<typeof BindDeviceSchema>;

export type { BindDeviceFormValues };

export interface BindDeviceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: BindDeviceFormValues) => Promise<void>;
  onBindById?: (deviceId: string) => Promise<void>;
  isLoading?: boolean;
}

const BindDeviceDialogComponent = ({
  open,
  onOpenChange,
  onSubmit,
  onBindById,
  isLoading = false,
}: BindDeviceDialogProps) => {
  const [activeTab, setActiveTab] = useState("code");
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const { t } = useTranslation("agents");

  // Fetch user devices
  const { data: devicesData, isLoading: devicesLoading } = useDeviceList();


  const { control, handleSubmit, reset, formState: { errors } } = useForm<BindDeviceFormValues>({
    resolver: zodResolver(BindDeviceSchema),
    defaultValues: {
      code: "",
    },
  });

  const onCodeSubmit = async (data: BindDeviceFormValues) => {
    try {
      await onSubmit(data);
      reset();
      onOpenChange(false);
    } catch (e) {
      // Error handled by parent
    }
  };

  const onSelectSubmit = async () => {
    if (!selectedDeviceId || !onBindById) return;
    try {
      await onBindById(selectedDeviceId);
      setSelectedDeviceId("");
      onOpenChange(false);
    } catch (e) {
      // Error handled by parent
    }
  };

  const handleOk = () => {
    if (activeTab === 'select') {
      onSelectSubmit();
    } else {
      handleSubmit(onCodeSubmit)();
    }
  }

  const deviceOptions = (devicesData?.data || []).map(d => ({
    label: `${d.device_name || t("unnamed_device")} (${d.mac_address})`,
    value: d.id
  }));

  return (
    <Modal
      title={t("add_device_title", "Gán Thiết Bị")}
      visible={open}
      onCancel={() => onOpenChange(false)}
      onOk={handleOk}
      confirmLoading={isLoading}
      okText={activeTab === 'select' ? t("save", "Lưu") : t("bind_device_btn", "Gán Thiết Bị")}
      cancelText={t("cancel")}
      style={{ maxWidth: 450 }}
    >
      <Tabs activeKey={activeTab} onChange={(key) => setActiveTab(key as string)} type="line">
        <TabPane tab={t("select_device", "Chọn Thiết Bị")} itemKey="select">
          <div className="pt-4">
            <div className="mb-2 font-semibold text-sm">{t("available_devices", "Thiết bị có sẵn")}</div>
            <Select
              placeholder={t("select_device_help", "Chọn thiết bị đã kết nối vào tài khoản của bạn.")}
              style={{ width: '100%' }}
              optionList={deviceOptions}
              value={selectedDeviceId}
              onChange={(val) => setSelectedDeviceId(val as string)}
              loading={devicesLoading}
              disabled={isLoading}
              emptyContent={t("common:no_data")}
            />
          </div>
        </TabPane>
        <TabPane tab={t("enter_code", "Nhập Mã")} itemKey="code">
          <Form className="pt-4 w-full">
            <Controller
              control={control}
              name="code"
              render={({ field }) => (
                <div className="mb-4">
                  <Typography.Text className="block mb-1">{t("device_code", "Mã thiết bị / Địa chỉ MAC")}</Typography.Text>
                  <Input
                    placeholder={t("enter_device_code", "VD: 126821 hoặc AA:BB:CC:DD:EE:FF")}
                    value={field.value}
                    onChange={field.onChange}
                    disabled={isLoading}
                  />
                  {errors.code?.message && <Typography.Text type="danger">{errors.code.message}</Typography.Text>}
                </div>
              )}
            />
          </Form>
        </TabPane>
      </Tabs>
    </Modal>
  );
};

export const BindDeviceDialog = memo(BindDeviceDialogComponent);
