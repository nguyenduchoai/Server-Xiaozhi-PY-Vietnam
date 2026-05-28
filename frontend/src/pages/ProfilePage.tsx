import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Tabs,
  TabPane,
  Card,
  Form,
  Button,
  Avatar,
  Upload,
  Typography,
  Banner,
  Skeleton,
  Modal,
  Input
} from "@douyinfe/semi-ui";
import {
  IconUpload,
  IconAlertTriangle
} from "@douyinfe/semi-icons";
import { PageHead } from "@/components/PageHead";
import {
  useUserProfile,
  useUpdateProfile,
  useChangePassword,
  useUploadAvatar,
  useDeleteAccount,
} from "@/queries";

const { Title, Text } = Typography;

// Common timezone options
const TIMEZONE_OPTIONS = [
  { value: "UTC", label: "UTC (Coordinated Universal Time)" },
  { value: "America/New_York", label: "America/New York (EST/EDT)" },
  { value: "America/Chicago", label: "America/Chicago (CST/CDT)" },
  { value: "America/Denver", label: "America/Denver (MST/MDT)" },
  { value: "America/Los_Angeles", label: "America/Los Angeles (PST/PDT)" },
  { value: "Europe/London", label: "Europe/London (GMT/BST)" },
  { value: "Europe/Paris", label: "Europe/Paris (CET/CEST)" },
  { value: "Europe/Berlin", label: "Europe/Berlin (CET/CEST)" },
  { value: "Asia/Tokyo", label: "Asia/Tokyo (JST)" },
  { value: "Asia/Shanghai", label: "Asia/Shanghai (CST)" },
  { value: "Asia/Hong_Kong", label: "Asia/Hong Kong (HKT)" },
  { value: "Asia/Singapore", label: "Asia/Singapore (SGT)" },
  { value: "Asia/Bangkok", label: "Asia/Bangkok (ICT)" },
  { value: "Asia/Ho_Chi_Minh", label: "Asia/Ho Chi Minh (ICT)" },
  { value: "Asia/Seoul", label: "Asia/Seoul (KST)" },
  { value: "Asia/Dubai", label: "Asia/Dubai (GST)" },
  { value: "Australia/Sydney", label: "Australia/Sydney (AEST/AEDT)" },
  { value: "Pacific/Auckland", label: "Pacific/Auckland (NZST/NZDT)" },
];

export const ProfilePage = () => {
  const { t } = useTranslation("profile");
  const { data: user, isLoading } = useUserProfile();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const uploadAvatar = useUploadAvatar();
  const deleteAccount = useDeleteAccount();

  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [isDeleteModalVisible, setIsDeleteModalVisible] = useState(false);

  const handleProfileSubmit = (values: any) => {
    const updates: any = {};
    if (values.name && values.name !== user?.name) updates.name = values.name;
    if (values.timezone && values.timezone !== user?.timezone)
      updates.timezone = values.timezone;

    if (Object.keys(updates).length > 0) {
      updateProfile.mutate(updates);
    }
  };

  const handlePasswordSubmit = (values: any) => {
    changePassword.mutate({
      current_password: values.current_password,
      new_password: values.new_password,
    });
  };

  const beforeUpload = (file: any) => {
    if (file.size > 5 * 1024 * 1024) {
      Modal.error({ title: t("max_file_size"), content: t("max_file_size_desc") });
      return false;
    }
    if (!["image/jpeg", "image/jpg", "image/png", "image/webp"].includes(file.type)) {
      Modal.error({ title: t("invalid_file_type"), content: t("invalid_file_type_desc") });
      return false;
    }

    uploadAvatar.mutate(file);
    return false; // Prevent auto upload by component, handled manually via mutation
  };

  const handleDeleteAccount = () => {
    if (deleteConfirmText === "DELETE") {
      deleteAccount.mutate(undefined, {
        onSuccess: () => setIsDeleteModalVisible(false)
      });
    }
  };

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  if (isLoading) {
    return (
      <div className="container max-w-4xl mx-auto p-6 space-y-6">
        <Skeleton placeholder={<Skeleton.Title className="mb-4" />} loading={true}>
          <Skeleton.Paragraph rows={3} />
        </Skeleton>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container max-w-4xl mx-auto p-6">
        <Banner
          type="danger"
          icon={<IconAlertTriangle />}
          description={t("failed_to_load_profile")}
          title={t("error")}
        />
      </div>
    );
  }

  return (
    <>
      <PageHead
        title="profile:page.title"
        description="profile:page.description"
        translateTitle
        translateDescription
      />
      <div className="container max-w-4xl mx-auto p-6 space-y-6">
        <div>
          <Title heading={2}>{t("profile_settings")}</Title>
          <Text type="tertiary">
            {t("manage_account_settings")}
          </Text>
        </div>

        <Tabs type="line">
          {/* Profile Info Tab */}
          <TabPane tab={t("profile_info")} itemKey="info">
            <Card
              title={t("profile_information")}
              headerExtraContent={<Text type="tertiary">{t("update_personal_info")}</Text>}
              bodyStyle={{ padding: 24 }}
              style={{ marginTop: 16 }}
            >
              <div className="flex flex-col gap-6">
                {/* Avatar Section */}
                <div className="flex items-center gap-6">
                  <Avatar
                    src={user.profile_image_base64 || undefined}
                    size="extra-large"
                    color="indigo"
                  >
                    {getInitials(user.name)}
                  </Avatar>
                  <div className="space-y-2">
                    <Upload
                      action=""
                      beforeUpload={beforeUpload}
                      showUploadList={false}
                      accept="image/*"
                    >
                      <Button icon={<IconUpload />} theme="light" loading={uploadAvatar.isPending}>
                        {t("choose_image")}
                      </Button>
                    </Upload>
                    <Text type="tertiary" size="small" style={{ display: 'block' }}>
                      {t("max_file_size_hint", "Maximum 5MB, JPEG/PNG/WebP")}
                    </Text>
                  </div>
                </div>

                <Form
                  onSubmit={handleProfileSubmit}
                  initValues={{
                    name: user.name,
                    timezone: user.timezone || "UTC",
                    email: user.email
                  }}
                  labelPosition="top"
                >
                  <Form.Input
                    field="name"
                    label={t("name")}
                    placeholder={t("name_placeholder")}
                    rules={[{ required: true, message: t("name_required") }]}
                  />

                  <Form.Input
                    field="email"
                    label={t("email")}
                    disabled
                    extraText={t("email_cannot_change")}
                  />

                  <Form.Select
                    field="timezone"
                    label={t("timezone")}
                    optionList={TIMEZONE_OPTIONS}
                    style={{ width: '100%' }}
                    extraText={t("timezone_description")}
                  />

                  <Button
                    type="primary"
                    theme="solid"
                    htmlType="submit"
                    loading={updateProfile.isPending}
                    style={{ marginTop: 16 }}
                  >
                    {t("save_changes")}
                  </Button>
                </Form>
              </div>
            </Card>
          </TabPane>

          {/* Security Tab */}
          <TabPane tab={t("security")} itemKey="security">
            <Card
              title={t("change_password")}
              headerExtraContent={<Text type="tertiary">{t("change_password_description")}</Text>}
              bodyStyle={{ padding: 24 }}
              style={{ marginTop: 16 }}
            >
              <Form onSubmit={handlePasswordSubmit} labelPosition="top">
                <Form.Input
                  field="current_password"
                  label={t("current_password")}
                  mode="password"
                  rules={[{ required: true, message: t("required") }]}
                />
                <Form.Input
                  field="new_password"
                  label={t("new_password")}
                  mode="password"
                  rules={[{ required: true, message: t("required") }, { min: 6, message: t("password_min") }]}
                />
                <Form.Input
                  field="confirm_password"
                  label={t("confirm_new_password")}
                  mode="password"
                  rules={[
                    { required: true, message: t("required") },

                  ]}
                />

                <Banner
                  type="warning"
                  icon={<IconAlertTriangle />}
                  description={t("password_warning_description")}
                  title={t("password_warning")}
                  style={{ margin: '16px 0' }}
                />

                <Button
                  type="primary"
                  theme="solid"
                  htmlType="submit"
                  loading={changePassword.isPending}
                >
                  {t("change_password")}
                </Button>
              </Form>
            </Card>
          </TabPane>

          {/* Danger Zone Tab */}
          <TabPane tab={t("danger_zone")} itemKey="danger">
            <Card
              title={<Text type="danger">{t("danger_zone_title")}</Text>}
              className="border-red-200"
              headerExtraContent={<Text type="tertiary">{t("danger_zone_description")}</Text>}
              bodyStyle={{ padding: 24 }}
              style={{ marginTop: 16, borderColor: 'var(--semi-color-danger)' }}
            >
              <Banner
                type="danger"
                description={t("delete_account_warning_description")}
                title={t("delete_account_warning")}
                style={{ marginBottom: 24 }}
              />

              <div className="space-y-2 mb-6">
                <Text strong>{t("what_happens_when_delete")}</Text>
                <ul className="list-disc list-inside text-sm text-gray-500 mt-2">
                  <li>{t("delete_account_point_1")}</li>
                  <li>{t("delete_account_point_2")}</li>
                  <li>{t("delete_account_point_3")}</li>
                  <li>{t("delete_account_point_4")}</li>
                </ul>
              </div>

              <Button
                type="danger"
                theme="solid"
                onClick={() => setIsDeleteModalVisible(true)}
              >
                {t("delete_my_account")}
              </Button>

              <Modal
                title={t("delete_account_confirm_title")}
                visible={isDeleteModalVisible}
                onCancel={() => setIsDeleteModalVisible(false)}
                footer={null}
              >
                <div className="space-y-4">
                  <Text>{t("delete_account_confirm_description")}</Text>
                  <div>
                    <div style={{ marginBottom: 8 }}>
                      <Text strong>
                        {t("type_delete_to_confirm").replace("<strong>", "").replace("</strong>", "")}
                      </Text>
                    </div>
                    <Input
                      value={deleteConfirmText}
                      onChange={(val) => setDeleteConfirmText(val)}
                      placeholder={t("delete_placeholder")}
                    />
                  </div>
                  <div className="flex justify-end gap-2 mt-4">
                    <Button onClick={() => setIsDeleteModalVisible(false)} disabled={deleteAccount.isPending}>
                      {t("common:cancel")}
                    </Button>
                    <Button
                      type="danger"
                      theme="solid"
                      onClick={handleDeleteAccount}
                      disabled={deleteConfirmText !== "DELETE"}
                      loading={deleteAccount.isPending}
                    >
                      {t("delete_my_account")}
                    </Button>
                  </div>
                </div>
              </Modal>

            </Card>
          </TabPane>
        </Tabs>
      </div>
    </>
  );
};

export default ProfilePage;
