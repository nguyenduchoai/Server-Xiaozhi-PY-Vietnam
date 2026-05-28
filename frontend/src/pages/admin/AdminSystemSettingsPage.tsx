/**
 * Admin System Settings Page
 * SuperAdmin only — configure Auto-Provision and OAuth settings
 * 
 * Auto-Provision: Select LLM/TTS from existing providers (không cần nhập thủ công)
 */
import { useEffect, useState } from "react";
import {
  Card,
  Typography,
  Form,
  Button,
  Switch,
  Select,
  Banner,
  Divider,
  Spin,
  Toast,
  Tag,
  Input,
  TextArea,
} from "@douyinfe/semi-ui";
import { IconSetting, IconLink, IconLock, IconMail, IconSend } from "@douyinfe/semi-icons";
import { apiClient } from "@/config/axios-instance";

const { Title, Text } = Typography;

interface ProviderOption {
  reference: string;
  name: string;
  type: string;
  source: string;
  owner?: string;
}

interface AutoProvisionConfig {
  enabled: boolean;
  llm_provider_ref: string | null;
  tts_provider_ref: string | null;
  tts_voice: string;
  system_prompt: string;
}

interface OAuthConfig {
  google_enabled: boolean;
  google_client_id: string | null;
  google_client_secret: string | null;
  zalo_enabled: boolean;
  zalo_app_id: string | null;
  zalo_app_secret: string | null;
}

interface SMTPConfig {
  host: string;
  port: number;
  username: string;
  password: string; // Returned masked from server (e.g. "********") — only sent back when user types a new one
  from_email: string;
  from_name: string;
  use_tls: boolean;
  enabled: boolean;
}

const defaultSMTP: SMTPConfig = {
  host: "smtp.gmail.com",
  port: 587,
  username: "",
  password: "",
  from_email: "",
  from_name: "Xiaozhi AI",
  use_tls: true,
  enabled: false,
};

const defaultAutoProvision: AutoProvisionConfig = {
  enabled: false,
  llm_provider_ref: null,
  tts_provider_ref: null,
  tts_voice: "vi-VN-HoaiMyNeural",
  system_prompt: "Bạn là trợ lý AI thân thiện, nói tiếng Việt, ngắn gọn và hữu ích.",
};

const defaultOAuth: OAuthConfig = {
  google_enabled: false,
  google_client_id: null,
  google_client_secret: null,
  zalo_enabled: false,
  zalo_app_id: null,
  zalo_app_secret: null,
};

export const AdminSystemSettingsPage = () => {
  const [autoProvision, setAutoProvision] = useState<AutoProvisionConfig>(defaultAutoProvision);
  const [oauth, setOAuth] = useState<OAuthConfig>(defaultOAuth);
  const [smtp, setSMTP] = useState<SMTPConfig>(defaultSMTP);
  // Server returns password masked (e.g. "********"). We keep that as-is in
  // state; the backend skips updating SMTP_PASSWORD when the field still
  // starts with "*", same pattern OAuth secrets use.
  const [smtpTestEmail, setSmtpTestEmail] = useState<string>("");
  const [llmProviders, setLlmProviders] = useState<ProviderOption[]>([]);
  const [ttsProviders, setTtsProviders] = useState<ProviderOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingAP, setSavingAP] = useState(false);
  const [savingOAuth, setSavingOAuth] = useState(false);
  const [savingSMTP, setSavingSMTP] = useState(false);
  const [testingSMTP, setTestingSMTP] = useState(false);

  // Load settings + available providers
  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [apResp, oauthResp, providersResp, smtpResp] = await Promise.all([
          apiClient.get("/system-settings/auto-provision"),
          apiClient.get("/system-settings/oauth"),
          apiClient.get("/system-settings/auto-provision/providers"),
          apiClient.get("/admin/smtp-settings"),
        ]);
        if (apResp.data?.config) setAutoProvision(apResp.data.config);
        if (oauthResp.data?.config) setOAuth(oauthResp.data.config);
        if (providersResp.data) {
          setLlmProviders(providersResp.data.LLM || []);
          setTtsProviders(providersResp.data.TTS || []);
        }
        if (smtpResp.data) {
          setSMTP(smtpResp.data);
        }
      } catch (e: unknown) {
        console.error("Failed to load settings:", e);
        Toast.error("Không thể tải cài đặt hệ thống");
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  // Save Auto-Provision
  const handleSaveAutoProvision = async () => {
    if (autoProvision.enabled && !autoProvision.llm_provider_ref) {
      Toast.warning("Vui lòng chọn LLM Provider trước khi bật Auto-Provision");
      return;
    }
    setSavingAP(true);
    try {
      await apiClient.post("/system-settings/auto-provision", autoProvision);
      Toast.success("Đã lưu cấu hình Auto-Provision ✅");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      Toast.error(err.response?.data?.detail || "Lỗi lưu cài đặt");
    } finally {
      setSavingAP(false);
    }
  };

  // Save SMTP
  const handleSaveSMTP = async () => {
    if (smtp.enabled && (!smtp.host || !smtp.username || !smtp.from_email)) {
      Toast.warning("Cần điền Host, Username và From Email trước khi bật SMTP");
      return;
    }
    setSavingSMTP(true);
    try {
      // Backend skips password update when the value still starts with "*"
      // (i.e. user did not retype it) — same pattern OAuth secrets use.
      // We just send the state as-is.
      await apiClient.post("/admin/smtp-settings", smtp);
      Toast.success("Đã lưu cấu hình SMTP. Cần restart backend để áp dụng. ✅");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      Toast.error(err.response?.data?.detail || "Lỗi lưu cấu hình SMTP");
    } finally {
      setSavingSMTP(false);
    }
  };

  // Send a test email through current (already-applied) SMTP settings
  const handleTestSMTP = async () => {
    if (!smtpTestEmail || !smtpTestEmail.includes("@")) {
      Toast.warning("Nhập email hợp lệ để gửi test");
      return;
    }
    setTestingSMTP(true);
    try {
      const resp = await apiClient.post(
        "/admin/smtp-settings/test",
        null,
        { params: { test_email: smtpTestEmail } },
      );
      Toast.success(resp.data?.message || `Đã gửi email test đến ${smtpTestEmail}`);
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      Toast.error(err.response?.data?.detail || "Gửi test email thất bại");
    } finally {
      setTestingSMTP(false);
    }
  };

  // Save OAuth
  const handleSaveOAuth = async () => {
    setSavingOAuth(true);
    try {
      await apiClient.post("/system-settings/oauth", oauth);
      Toast.success("Đã lưu cấu hình OAuth ✅");
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      Toast.error(err.response?.data?.detail || "Lỗi lưu cài đặt");
    } finally {
      setSavingOAuth(false);
    }
  };

  // Format provider label for dropdown
  const renderProviderLabel = (p: ProviderOption) => {
    const sourceColors: Record<string, "blue" | "green" | "grey"> = {
      user: "blue",
      public: "green",
      default: "grey",
    };
    const color = sourceColors[p.source] ?? ("grey" as const);
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span>{p.name}</span>
        <Tag size="small" color={color} type="light">
          {p.type}
        </Tag>
        <Tag size="small" color={color} type="ghost">
          {p.source === "default" ? "config" : p.source}
        </Tag>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: 400 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 800 }}>
      <Title heading={3} style={{ marginBottom: 24 }}>
        <IconSetting style={{ marginRight: 8 }} />
        Cài đặt hệ thống
      </Title>

      {/* ============ Auto-Provision ============ */}
      <Card
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <IconLink />
            <span>Auto-Provision (Tự động kích hoạt thiết bị)</span>
          </div>
        }
        style={{ marginBottom: 24 }}
      >
        <Banner
          type="info"
          description="Khi bật, thiết bị mới sẽ tự động được đăng ký và sẵn sàng sử dụng ngay khi cắm điện (không cần nhập mã kích hoạt). Chọn LLM và TTS provider từ danh sách đã cấu hình."
          style={{ marginBottom: 16 }}
          closeIcon={null}
        />

        <Form labelPosition="left" labelWidth={160}>
          <div style={{ marginBottom: 20, display: "flex", alignItems: "center", gap: 12 }}>
            <Text strong>Bật Auto-Provision:</Text>
            <Switch
              checked={autoProvision.enabled}
              onChange={(v) => setAutoProvision({ ...autoProvision, enabled: v })}
            />
            {autoProvision.enabled && (
              <Tag color="green" type="solid">Đang bật</Tag>
            )}
          </div>

          <Divider margin={16} />

          {/* LLM Provider — select from list */}
          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: "block", marginBottom: 8 }}>LLM Provider</Text>
            <Select
              style={{ width: "100%" }}
              placeholder="Chọn LLM provider cho thiết bị mới..."
              value={autoProvision.llm_provider_ref || undefined}
              onChange={(v) => setAutoProvision({ ...autoProvision, llm_provider_ref: v as string })}
              optionList={llmProviders.map((p) => ({
                label: renderProviderLabel(p),
                value: p.reference,
              }))}
              showClear
              filter
            />
            <Text type="tertiary" size="small" style={{ marginTop: 4 }}>
              Provider AI được gán cho agent mặc định của thiết bị mới
            </Text>
          </div>

          {/* TTS Provider — select from list */}
          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: "block", marginBottom: 8 }}>TTS Provider</Text>
            <Select
              style={{ width: "100%" }}
              placeholder="Chọn TTS provider cho thiết bị mới..."
              value={autoProvision.tts_provider_ref || undefined}
              onChange={(v) => setAutoProvision({ ...autoProvision, tts_provider_ref: v as string })}
              optionList={ttsProviders.map((p) => ({
                label: renderProviderLabel(p),
                value: p.reference,
              }))}
              showClear
              filter
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: "block", marginBottom: 8 }}>TTS Voice</Text>
            <Input
              value={autoProvision.tts_voice}
              onChange={(v) => setAutoProvision({ ...autoProvision, tts_voice: v })}
              placeholder="VD: vi-VN-HoaiMyNeural (Edge), vi-VN-Standard-A (Google)"
            />
            <Text type="tertiary" size="small" style={{ marginTop: 4, display: "block" }}>
              VD: vi-VN-HoaiMyNeural (Edge), vi-VN-Standard-A (Google)
            </Text>
          </div>

          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: "block", marginBottom: 8 }}>System Prompt</Text>
            <TextArea
              value={autoProvision.system_prompt}
              onChange={(v) => setAutoProvision({ ...autoProvision, system_prompt: v })}
              autosize={{ minRows: 3, maxRows: 8 }}
              placeholder="Prompt mặc định cho agent được tạo tự động"
            />
            <Text type="tertiary" size="small" style={{ marginTop: 4, display: "block" }}>
              Prompt mặc định cho agent được tạo tự động
            </Text>
          </div>

          <Button
            type="primary"
            theme="solid"
            onClick={handleSaveAutoProvision}
            loading={savingAP}
            style={{ marginTop: 16 }}
          >
            Lưu Auto-Provision
          </Button>
        </Form>
      </Card>

      {/* ============ OAuth ============ */}
      <Card
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <IconLock />
            <span>Đăng nhập OAuth (Google, Zalo)</span>
          </div>
        }
      >
        <Banner
          type="info"
          description="Cho phép người dùng đăng nhập bằng Google hoặc Zalo thay vì email/mật khẩu."
          style={{ marginBottom: 16 }}
          closeIcon={null}
        />

        <Form labelPosition="left" labelWidth={160}>
          {/* Google */}
          <Title heading={5} style={{ margin: "8px 0 12px" }}>🔵 Google</Title>

          <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
            <Text strong>Bật Google Login:</Text>
            <Switch
              checked={oauth.google_enabled}
              onChange={(v) => setOAuth({ ...oauth, google_enabled: v })}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: "block", marginBottom: 8 }}>Client ID</Text>
            <Input
              value={oauth.google_client_id || ""}
              onChange={(v) => setOAuth({ ...oauth, google_client_id: v })}
              placeholder="xxx.apps.googleusercontent.com"
            />
            <Text type="tertiary" size="small" style={{ marginTop: 4, display: "block" }}>
              Từ Google Cloud Console → APIs &amp; Services → Credentials
            </Text>
          </div>

          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: "block", marginBottom: 8 }}>Client Secret</Text>
            <Input
              mode="password"
              value={oauth.google_client_secret || ""}
              onChange={(v) => setOAuth({ ...oauth, google_client_secret: v })}
              placeholder="GOCSPX-..."
            />
          </div>

          <Divider margin={20} />

          {/* Zalo */}
          <Title heading={5} style={{ margin: "8px 0 12px" }}>🔵 Zalo</Title>

          <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
            <Text strong>Bật Zalo Login:</Text>
            <Switch
              checked={oauth.zalo_enabled}
              onChange={(v) => setOAuth({ ...oauth, zalo_enabled: v })}
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: "block", marginBottom: 8 }}>App ID</Text>
            <Input
              value={oauth.zalo_app_id || ""}
              onChange={(v) => setOAuth({ ...oauth, zalo_app_id: v })}
              placeholder="ID ứng dụng Zalo"
            />
            <Text type="tertiary" size="small" style={{ marginTop: 4, display: "block" }}>
              Từ developers.zalo.me → Quản lý ứng dụng
            </Text>
          </div>

          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: "block", marginBottom: 8 }}>App Secret</Text>
            <Input
              mode="password"
              value={oauth.zalo_app_secret || ""}
              onChange={(v) => setOAuth({ ...oauth, zalo_app_secret: v })}
              placeholder="Secret key"
            />
          </div>

          <Button
            type="primary"
            theme="solid"
            onClick={handleSaveOAuth}
            loading={savingOAuth}
            style={{ marginTop: 16 }}
          >
            Lưu OAuth
          </Button>
        </Form>
      </Card>

      {/* ============ SMTP ============ */}
      <Card
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <IconMail />
            <span>Cấu hình SMTP (Email server)</span>
          </div>
        }
        style={{ marginTop: 24 }}
      >
        <Banner
          type="warning"
          description="Cấu hình SMTP được ghi vào file .env. Sau khi lưu cần restart backend để áp dụng. Mật khẩu hiển thị dưới dạng ẩn (********); chỉ nhập mật khẩu mới khi muốn thay đổi, để nguyên thì server giữ giá trị hiện tại."
          style={{ marginBottom: 16 }}
          closeIcon={null}
        />

        <Form labelPosition="left" labelWidth={160}>
          <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
            <Text strong>Bật Email Service:</Text>
            <Switch
              checked={smtp.enabled}
              onChange={(v) => setSMTP({ ...smtp, enabled: v })}
            />
            {smtp.enabled && <Tag color="green" type="solid">Đang bật</Tag>}
          </div>

          <Divider margin={16} />

          <div style={{ marginBottom: 16, display: "grid", gridTemplateColumns: "2fr 1fr", gap: 12 }}>
            <div>
              <Text strong style={{ display: "block", marginBottom: 8 }}>SMTP Host</Text>
              <Input
                value={smtp.host}
                onChange={(v) => setSMTP({ ...smtp, host: v })}
                placeholder="smtp.gmail.com"
              />
            </div>
            <div>
              <Text strong style={{ display: "block", marginBottom: 8 }}>Port</Text>
              <Input
                value={String(smtp.port)}
                onChange={(v) => setSMTP({ ...smtp, port: parseInt(v) || 0 })}
                placeholder="587"
              />
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: "block", marginBottom: 8 }}>Username</Text>
            <Input
              value={smtp.username}
              onChange={(v) => setSMTP({ ...smtp, username: v })}
              placeholder="your-email@gmail.com"
            />
          </div>

          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: "block", marginBottom: 8 }}>Password / App Password</Text>
            <Input
              mode="password"
              value={smtp.password || ""}
              onChange={(v) => setSMTP({ ...smtp, password: v })}
              placeholder="App password (Gmail) hoặc mật khẩu SMTP"
            />
            <Text type="tertiary" size="small" style={{ marginTop: 4, display: "block" }}>
              Với Gmail, dùng App Password (cần bật 2-Step Verification trước).
            </Text>
          </div>

          <div style={{ marginBottom: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <Text strong style={{ display: "block", marginBottom: 8 }}>From Email</Text>
              <Input
                value={smtp.from_email}
                onChange={(v) => setSMTP({ ...smtp, from_email: v })}
                placeholder="noreply@xiaozhi.vn"
              />
            </div>
            <div>
              <Text strong style={{ display: "block", marginBottom: 8 }}>From Name</Text>
              <Input
                value={smtp.from_name}
                onChange={(v) => setSMTP({ ...smtp, from_name: v })}
                placeholder="Xiaozhi AI"
              />
            </div>
          </div>

          <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
            <Text strong>Dùng TLS:</Text>
            <Switch
              checked={smtp.use_tls}
              onChange={(v) => setSMTP({ ...smtp, use_tls: v })}
            />
          </div>

          <div style={{ display: "flex", gap: 12, marginTop: 16, flexWrap: "wrap" }}>
            <Button
              type="primary"
              theme="solid"
              onClick={handleSaveSMTP}
              loading={savingSMTP}
            >
              Lưu SMTP
            </Button>
          </div>

          <Divider margin={20} />

          <Title heading={5} style={{ margin: "0 0 12px" }}>
            <IconSend style={{ marginRight: 8 }} />
            Gửi email test
          </Title>
          <Text type="tertiary" size="small" style={{ marginBottom: 8, display: "block" }}>
            Test này gọi đến cấu hình SMTP đã được apply (cần restart sau khi Lưu).
          </Text>

          <div style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>
            <div style={{ flex: 1, minWidth: 240 }}>
              <Text strong style={{ display: "block", marginBottom: 8 }}>Email nhận</Text>
              <Input
                value={smtpTestEmail}
                onChange={(v) => setSmtpTestEmail(v)}
                placeholder="you@example.com"
              />
            </div>
            <Button
              theme="light"
              icon={<IconSend />}
              onClick={handleTestSMTP}
              loading={testingSMTP}
            >
              Gửi test
            </Button>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default AdminSystemSettingsPage;
