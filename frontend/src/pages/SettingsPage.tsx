import { useState, useEffect } from "react";
import { toast } from "sonner";
import { NotificationTester } from "@/components/settings/NotificationTester";
import { VoiceShortcutsHelp } from "@/components/settings/VoiceShortcutsHelp";
import { BrandingSettingsCard } from "@/components/settings/BrandingSettingsCard";
import { FAQSettingsCard } from "@/components/settings/FAQSettingsCard";
import { SolutionsSettingsCard } from "@/components/settings/SolutionsSettingsCard";

import { PageHead } from "@/components/PageHead";
import {
  Tabs,
  TabPane,
  Card,
  Button,
  Input,
  TextArea,
  Switch,
  Typography,
  Divider,
  Upload,
  Spin
} from "@douyinfe/semi-ui";
import {
  IconSave,
  IconGlobe,
  IconCreditCard,
  IconHome,
  IconFile,
  IconBell,
  IconPlus,
  IconDelete,
  IconCopy,
  IconTick,
  IconUpload,
  IconImage
} from "@douyinfe/semi-icons";
import { apiClient } from "@/config/axios-instance";
import {
  Settings,
  CreditCard,
  QrCode,
  Building2,
  Image as ImageIcon,
  MessageSquare,
  Star,
  Users,
  Menu as MenuIcon,
  Lightbulb,
  HelpCircle,
  Mail
} from "lucide-react";

const { Title, Text } = Typography;

interface FeatureItem {
  icon: string;
  title: string;
  description: string;
}

interface TestimonialItem {
  id: number;
  name: string;
  role: string;
  content: string;
  avatar: string;
  rating: number;
}

interface MenuItem {
  label: string;
  href: string;
  external: boolean;
}

interface SiteSettings {
  web: {
    site_name: string;
    site_description: string;
    site_logo: string;
    primary_color: string;
    contact_email: string;
    support_phone: string;
  };
  payment: {
    bank_name: string;
    bank_code: string;
    account_number: string;
    account_name: string;
    bank_branch: string;
    transfer_content_template: string;
    enable_qr_code: boolean;
  };
  home: {
    hero: {
      hero_title: string;
      hero_subtitle: string;
      hero_badge_text: string;
      hero_cta_primary: string;
      hero_cta_secondary: string;
    };
    features: {
      features_enabled: boolean;
      features_title: string;
      features_subtitle: string;
      features_list: FeatureItem[];
    };
    pricing: {
      pricing_enabled: boolean;
      pricing_title: string;
      pricing_subtitle: string;
    };
    cta: {
      cta_enabled: boolean;
      cta_title: string;
      cta_subtitle: string;
      cta_button_text: string;
    };
    testimonials: {
      testimonials_enabled: boolean;
      testimonials_title: string;
      testimonials_subtitle: string;
      testimonials_list: TestimonialItem[];
    };
    footer: {
      footer_brand_description: string;
      footer_copyright: string;
      footer_address: string;
      footer_social_facebook: string;
      footer_social_twitter: string;
      footer_social_linkedin: string;
    };
    menu: {
      menu_items: MenuItem[];
    };
    solutions?: {
      solutions_enabled: boolean;
      solutions_title: string;
      solutions_subtitle: string;
      solutions_list: any[];
    };
    faq?: {
      faq_enabled: boolean;
      faq_title: string;
      faq_subtitle: string;
      faq_list: any[];
    };
  };
  branding?: {
    parent_company_name: string;
    parent_company_url: string;
    company_badge_text: string;
  };
}

const defaultSettings: SiteSettings = {
  web: {
    site_name: "Xiaozhi AI",
    site_description: "Nền tảng AI Agent thông minh cho doanh nghiệp",
    site_logo: "/logo.png",
    primary_color: "#3b82f6",
    contact_email: "contact@xiaozhi-ai-iot.vn",
    support_phone: "1900-xxxx",
  },
  payment: {
    bank_name: "Vietcombank",
    bank_code: "VCB",
    account_number: "0011004295499",
    account_name: "NGUYEN VAN A",
    bank_branch: "Chi nhánh Hà Nội",
    transfer_content_template: "Thanh toan goi {plan_name} - {user_email}",
    enable_qr_code: true,
  },
  home: {
    hero: {
      hero_title: "Xây dựng AI Agents Thông minh & Mạnh mẽ",
      hero_subtitle: "Quản lý IoT, tự động hóa nhà thông minh, và bán các AI Agent của bạn.",
      hero_badge_text: "Nền tảng AI Agent thông minh",
      hero_cta_primary: "Bắt đầu miễn phí",
      hero_cta_secondary: "Đăng nhập",
    },
    features: {
      features_enabled: true,
      features_title: "Tại sao chọn chúng tôi?",
      features_subtitle: "Nền tảng toàn diện cho mọi nhu cầu AI Agent của bạn",
      features_list: [],
    },
    pricing: {
      pricing_enabled: true,
      pricing_title: "Bảng giá linh hoạt",
      pricing_subtitle: "Chọn gói phù hợp với nhu cầu của bạn",
    },
    cta: {
      cta_enabled: true,
      cta_title: "Sẵn sàng bắt đầu?",
      cta_subtitle: "Tham gia cùng hàng nghìn người dùng",
      cta_button_text: "Đăng ký miễn phí ngay",
    },
    testimonials: {
      testimonials_enabled: true,
      testimonials_title: "Khách hàng nói gì?",
      testimonials_subtitle: "Hàng nghìn người dùng đã tin tưởng sử dụng dịch vụ của chúng tôi",
      testimonials_list: [],
    },
    footer: {
      footer_brand_description: "Nền tảng AI Agent thông minh hàng đầu Việt Nam",
      footer_copyright: "© 2025 Xiaozhi AI. All rights reserved.",
      footer_address: "Hà Nội, Việt Nam",
      footer_social_facebook: "",
      footer_social_twitter: "",
      footer_social_linkedin: "",
    },
    menu: {
      menu_items: [],
    },
    solutions: {
      solutions_enabled: true,
      solutions_title: "Giải pháp",
      solutions_subtitle: "Các giải pháp AI của chúng tôi",
      solutions_list: [],
    },
    faq: {
      faq_enabled: true,
      faq_title: "Câu hỏi thường gặp",
      faq_subtitle: "",
      faq_list: [],
    },
  },
  branding: {
    parent_company_name: "Bizino.AI",
    parent_company_url: "https://bizino.ai",
    company_badge_text: "by Bizino.AI",
  },
};

interface SettingsPageProps {
  section?: string;
}

export const SettingsPage = ({ section }: SettingsPageProps) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [copied, setCopied] = useState(false);
  const [settings, setSettings] = useState<SiteSettings>(defaultSettings);
  const [uploadingLogo, setUploadingLogo] = useState(false);
  const [activeTab, setActiveTab] = useState("web");

  // Handle section prop
  useEffect(() => {
    if (section === "integrations") {
      setActiveTab("notifications");
    }
  }, [section]);

  // SMTP Settings state
  const [smtpSettings, setSmtpSettings] = useState({
    host: "smtp.gmail.com",
    port: 587,
    username: "",
    password: "",
    from_email: "",
    from_name: "Xiaozhi AI",
    use_tls: true,
    enabled: false,
  });
  const [smtpLoading, setSmtpLoading] = useState(false);
  const [smtpTesting, setSmtpTesting] = useState(false);
  const [testEmail, setTestEmail] = useState("");

  // Load settings from API
  useEffect(() => {
    loadSettings();
    loadSmtpSettings();
  }, []);

  const loadSmtpSettings = async () => {
    try {
      const response = await apiClient.get("/admin/smtp-settings");
      if (response.data) {
        setSmtpSettings(response.data);
      }
    } catch {
      // SMTP settings not available or not authorized - use defaults
    }
  };

  const saveSmtpSettings = async () => {
    setSmtpLoading(true);
    try {
      await apiClient.post("/admin/smtp-settings", smtpSettings);
      toast.success("Đã lưu cấu hình SMTP!");
      loadSmtpSettings(); // Reload to get masked password
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Không thể lưu cấu hình SMTP");
    } finally {
      setSmtpLoading(false);
    }
  };

  const testSmtpConnection = async () => {
    if (!testEmail) {
      toast.error("Vui lòng nhập email để test");
      return;
    }
    setSmtpTesting(true);
    try {
      const response = await apiClient.post(`/admin/smtp-settings/test?test_email=${encodeURIComponent(testEmail)}`);
      toast.success(response.data.message || "Email test đã được gửi!");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Test SMTP thất bại");
    } finally {
      setSmtpTesting(false);
    }
  };

  const loadSettings = async () => {
    setLoading(true);
    try {
      const response = await apiClient.get("/site-settings");
      if (response.data) {
        // Merge with default settings
        const merged = {
          web: { ...defaultSettings.web, ...response.data.web },
          payment: { ...defaultSettings.payment, ...response.data.payment },
          branding: response.data.branding || {
            parent_company_name: 'Bizino.AI',
            parent_company_url: 'https://bizino.ai',
            company_badge_text: 'by Bizino.AI',
          },
          home: {
            hero: { ...defaultSettings.home.hero, ...response.data.home?.hero },
            features: { ...defaultSettings.home.features, ...response.data.home?.features },
            solutions: response.data.home?.solutions || {
              solutions_enabled: true,
              solutions_title: 'Giải pháp',
              solutions_subtitle: '',
              solutions_list: [],
            },
            pricing: { ...defaultSettings.home.pricing, ...response.data.home?.pricing },
            cta: { ...defaultSettings.home.cta, ...response.data.home?.cta },
            testimonials: { ...defaultSettings.home.testimonials, ...response.data.home?.testimonials },
            faq: response.data.home?.faq || {
              faq_enabled: true,
              faq_title: 'Câu hỏi thường gặp',
              faq_subtitle: '',
              faq_list: [],
            },
            footer: { ...defaultSettings.home.footer, ...response.data.home?.footer },
            menu: { ...defaultSettings.home.menu, ...response.data.home?.menu },
          },
        };
        setSettings(merged as any);
      }
    } catch (error) {
      console.error("Failed to load settings:", error);
      toast.error("Failed to load settings");
    } finally {
      setLoading(false);
    }
  };

  const saveSettings = async (section?: string) => {
    setSaving(true);
    try {
      await apiClient.post("/site-settings/admin", settings);
      toast.success(section ? `Đã lưu cấu hình ${section}` : "Đã lưu tất cả cấu hình");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Không thể lưu cấu hình");
    } finally {
      setSaving(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success("Đã copy vào clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  const generateQrUrl = () => {
    return `https://img.vietqr.io/image/${settings.payment.bank_code}-${settings.payment.account_number}-compact.jpg?amount=0&accountName=${encodeURIComponent(settings.payment.account_name)}`;
  };

  // Logo upload handler
  const handleLogoUpload = (file: any) => {
    // Validate file type
    const allowedTypes = ["image/png", "image/jpeg", "image/jpg", "image/webp", "image/svg+xml"];
    if (!allowedTypes.includes(file.type)) {
      toast.error("Chỉ chấp nhận file PNG, JPG, WEBP hoặc SVG");
      return false;
    }

    // Validate file size (2MB max)
    if (file.size > 2 * 1024 * 1024) {
      toast.error("File quá lớn. Tối đa 2MB");
      return false;
    }

    setUploadingLogo(true);

    // Process upload asynchronously
    (async () => {
      try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await apiClient.post("/site-settings/upload-logo", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        if (response.data?.data?.logo_url) {
          setSettings(prev => ({
            ...prev,
            web: { ...prev.web, site_logo: response.data.data.logo_url }
          }));
          toast.success("Đã upload logo mới");
        }
      } catch (error: any) {
        console.error("Upload logo failed:", error);
        toast.error(error.response?.data?.detail || "Không thể upload logo");
      } finally {
        setUploadingLogo(false);
      }
    })();

    // Return false to prevent default upload behavior
    return false;
  };

  // Feature handlers
  const addFeature = () => {
    setSettings(prev => ({
      ...prev,
      home: {
        ...prev.home,
        features: {
          ...prev.home.features,
          features_list: [...prev.home.features.features_list, { icon: "Bot", title: "", description: "" }]
        }
      }
    }));
  };

  const removeFeature = (index: number) => {
    setSettings(prev => ({
      ...prev,
      home: {
        ...prev.home,
        features: {
          ...prev.home.features,
          features_list: prev.home.features.features_list.filter((_, i) => i !== index)
        }
      }
    }));
  };

  const updateFeature = (index: number, field: keyof FeatureItem, value: string) => {
    setSettings(prev => ({
      ...prev,
      home: {
        ...prev.home,
        features: {
          ...prev.home.features,
          features_list: prev.home.features.features_list.map((f, i) =>
            i === index ? { ...f, [field]: value } : f
          )
        }
      }
    }));
  };

  // Testimonial handlers
  const addTestimonial = () => {
    const newId = Math.max(0, ...settings.home.testimonials.testimonials_list.map(t => t.id)) + 1;
    setSettings(prev => ({
      ...prev,
      home: {
        ...prev.home,
        testimonials: {
          ...prev.home.testimonials,
          testimonials_list: [...prev.home.testimonials.testimonials_list, {
            id: newId, name: "", role: "", content: "", avatar: "", rating: 5
          }]
        }
      }
    }));
  };

  const removeTestimonial = (index: number) => {
    setSettings(prev => ({
      ...prev,
      home: {
        ...prev.home,
        testimonials: {
          ...prev.home.testimonials,
          testimonials_list: prev.home.testimonials.testimonials_list.filter((_, i) => i !== index)
        }
      }
    }));
  };

  const updateTestimonial = (index: number, field: keyof TestimonialItem, value: any) => {
    setSettings(prev => ({
      ...prev,
      home: {
        ...prev.home,
        testimonials: {
          ...prev.home.testimonials,
          testimonials_list: prev.home.testimonials.testimonials_list.map((t, i) =>
            i === index ? { ...t, [field]: value } : t
          )
        }
      }
    }));
  };

  // Menu handlers
  const addMenuItem = () => {
    setSettings(prev => ({
      ...prev,
      home: {
        ...prev.home,
        menu: {
          ...prev.home.menu,
          menu_items: [...prev.home.menu.menu_items, { label: "", href: "#", external: false }]
        }
      }
    }));
  };

  const removeMenuItem = (index: number) => {
    setSettings(prev => ({
      ...prev,
      home: {
        ...prev.home,
        menu: {
          ...prev.home.menu,
          menu_items: prev.home.menu.menu_items.filter((_, i) => i !== index)
        }
      }
    }));
  };

  const updateMenuItem = (index: number, field: keyof MenuItem, value: any) => {
    setSettings(prev => ({
      ...prev,
      home: {
        ...prev.home,
        menu: {
          ...prev.home.menu,
          menu_items: prev.home.menu.menu_items.map((m, i) =>
            i === index ? { ...m, [field]: value } : m
          )
        }
      }
    }));
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <>
      <PageHead title="Cài đặt" description="Quản lý cấu hình website, thanh toán và trang chủ" />

      <div className="container mx-auto space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <Title heading={2} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Settings className="h-8 w-8" />
              Cài đặt hệ thống
            </Title>
            <Text type="tertiary">
              Quản lý cấu hình website, thanh toán và trang chủ
            </Text>
          </div>
          <Button icon={<IconSave />} theme="solid" onClick={() => saveSettings()} loading={saving}>
            Lưu tất cả
          </Button>
        </div>

        <Tabs type="line" activeKey={activeTab} onChange={(key) => setActiveTab(key as string)}>
          {/* Web Config Tab */}
          <TabPane tab={<span><IconGlobe style={{ marginRight: 8 }} />Website</span>} itemKey="web">
            <Card
              title="Cấu hình Website"
              headerExtraContent={<Text type="tertiary">Thông tin cơ bản về website</Text>}
              style={{ marginTop: 16 }}
            >
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Text strong>Tên website</Text>
                  <Input
                    value={settings.web.site_name}
                    onChange={(val) => setSettings(prev => ({ ...prev, web: { ...prev.web, site_name: val } }))}
                  />
                </div>
                <div className="space-y-2">
                  <Text strong>Màu chủ đạo</Text>
                  <div className="flex gap-2">
                    <input
                      type="color"
                      value={settings.web.primary_color}
                      onChange={(e) => setSettings(prev => ({ ...prev, web: { ...prev.web, primary_color: e.target.value } }))}
                      className="w-16 h-8 p-1 border rounded"
                    />
                    <Input
                      value={settings.web.primary_color}
                      onChange={(val) => setSettings(prev => ({ ...prev, web: { ...prev.web, primary_color: val } }))}
                    />
                  </div>
                </div>
              </div>
              <div className="space-y-2 mt-4">
                <Text strong>Mô tả website</Text>
                <TextArea
                  value={settings.web.site_description}
                  onChange={(val) => setSettings(prev => ({ ...prev, web: { ...prev.web, site_description: val } }))}
                  rows={2}
                />
              </div>
              <Divider margin="24px" />
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Text strong>Email liên hệ</Text>
                  <Input
                    value={settings.web.contact_email}
                    onChange={(val) => setSettings(prev => ({ ...prev, web: { ...prev.web, contact_email: val } }))}
                  />
                </div>
                <div className="space-y-2">
                  <Text strong>Số điện thoại</Text>
                  <Input
                    value={settings.web.support_phone}
                    onChange={(val) => setSettings(prev => ({ ...prev, web: { ...prev.web, support_phone: val } }))}
                  />
                </div>
              </div>
              <div className="space-y-2 mt-4">
                <Text strong>URL Logo</Text>
                <Input
                  value={settings.web.site_logo}
                  onChange={(val) => setSettings(prev => ({ ...prev, web: { ...prev.web, site_logo: val } }))}
                />
              </div>

              {/* Logo Upload & Preview */}
              <div className="space-y-4 mt-6">
                <Divider />
                <Text strong style={{ fontSize: '16px' }}>Upload Logo</Text>
                <div className="flex items-start gap-6">
                  {/* Logo Preview */}
                  <div className="shrink-0">
                    <div className="w-24 h-24 border rounded-lg flex items-center justify-center bg-gray-50 overflow-hidden">
                      {settings.web.site_logo ? (
                        <img
                          src={settings.web.site_logo}
                          alt="Logo preview"
                          className="max-w-full max-h-full object-contain"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                          }}
                        />
                      ) : (
                        <IconImage style={{ fontSize: 32, color: 'var(--semi-color-text-2)' }} />
                      )}
                    </div>
                    <Text size="small" type="tertiary" style={{ display: 'block', textAlign: 'center', marginTop: 4 }}>Preview</Text>
                  </div>

                  {/* Upload Area */}
                  <div className="flex-1 space-y-2">
                    <Upload
                      action=""
                      beforeUpload={handleLogoUpload}
                      showUploadList={false}
                      accept="image/*"
                    >
                      <Button icon={<IconUpload />} theme="light" loading={uploadingLogo}>
                        Click để chọn file
                      </Button>
                    </Upload>
                    <Text type="tertiary" size="small" style={{ display: 'block' }}>
                      PNG, JPG, WEBP, SVG (tối đa 2MB)
                    </Text>
                  </div>
                </div>
              </div>
            </Card>
          </TabPane>

          {/* Payment Config Tab */}
          <TabPane tab={<span><IconCreditCard style={{ marginRight: 8 }} />Thanh toán</span>} itemKey="payment">
            <Card
              title={<span><Building2 className="h-5 w-5 inline mr-2" />Thông tin ngân hàng</span>}
              headerExtraContent={<Text type="tertiary">Cấu hình tài khoản nhận thanh toán</Text>}
              style={{ marginTop: 16 }}
            >
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Text strong>Tên ngân hàng</Text>
                  <Input
                    value={settings.payment.bank_name}
                    onChange={(val) => setSettings(prev => ({ ...prev, payment: { ...prev.payment, bank_name: val } }))}
                  />
                </div>
                <div className="space-y-2">
                  <Text strong>Mã ngân hàng (VietQR)</Text>
                  <Input
                    value={settings.payment.bank_code}
                    onChange={(val) => setSettings(prev => ({ ...prev, payment: { ...prev.payment, bank_code: val } }))}
                  />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2 mt-4">
                <div className="space-y-2">
                  <Text strong>Số tài khoản</Text>
                  <div className="flex gap-2">
                    <Input
                      value={settings.payment.account_number}
                      onChange={(val) => setSettings(prev => ({ ...prev, payment: { ...prev.payment, account_number: val } }))}
                    />
                    <Button icon={copied ? <IconTick /> : <IconCopy />} onClick={() => copyToClipboard(settings.payment.account_number)} />
                  </div>
                </div>
                <div className="space-y-2">
                  <Text strong>Chủ tài khoản</Text>
                  <Input
                    value={settings.payment.account_name}
                    onChange={(val) => setSettings(prev => ({ ...prev, payment: { ...prev.payment, account_name: val } }))}
                  />
                </div>
              </div>
              <div className="space-y-2 mt-4">
                <Text strong>Chi nhánh</Text>
                <Input
                  value={settings.payment.bank_branch}
                  onChange={(val) => setSettings(prev => ({ ...prev, payment: { ...prev.payment, bank_branch: val } }))}
                />
              </div>
              <div className="space-y-2 mt-4">
                <Text strong>Mẫu nội dung CK</Text>
                <Input
                  value={settings.payment.transfer_content_template}
                  onChange={(val) => setSettings(prev => ({ ...prev, payment: { ...prev.payment, transfer_content_template: val } }))}
                />
                <Text type="tertiary" size="small">Dùng {"{plan_name}"}, {"{user_email}"}, {"{amount}"}</Text>
              </div>
              <div className="flex items-center space-x-2 mt-4">
                <Switch
                  checked={settings.payment.enable_qr_code}
                  onChange={(checked) => setSettings(prev => ({ ...prev, payment: { ...prev.payment, enable_qr_code: checked } }))}
                />
                <Text>Hiển thị mã QR</Text>
              </div>
            </Card>

            {settings.payment.enable_qr_code && (
              <Card
                title={<span><QrCode className="h-5 w-5 inline mr-2" />Xem trước QR</span>}
                style={{ marginTop: 16 }}
              >
                <div className="flex flex-col items-center space-y-4">
                  <div className="border rounded-lg p-4 bg-white">
                    <img src={generateQrUrl()} alt="QR Code" className="w-64 h-64 object-contain" />
                  </div>
                  <div className="text-center">
                    <Text strong style={{ display: 'block' }}>{settings.payment.bank_name}</Text>
                    <Text size="normal" style={{ display: 'block', fontFamily: 'monospace', fontSize: '16px' }}>{settings.payment.account_number}</Text>
                    <Text type="tertiary">{settings.payment.account_name}</Text>
                  </div>
                </div>
              </Card>
            )}
          </TabPane>



          {/* Home Config Tab */}
          <TabPane tab={<span><IconHome style={{ marginRight: 8 }} />Trang chủ</span>} itemKey="home">
            {/* Hero Section */}
            <Card title="Hero Section" headerExtraContent={<Text type="tertiary">Phần đầu trang chủ</Text>} style={{ marginTop: 16 }}>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Text strong>Badge text</Text>
                  <Input
                    value={settings.home.hero.hero_badge_text}
                    onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, hero: { ...prev.home.hero, hero_badge_text: val } } }))}
                  />
                </div>
                <div className="space-y-2">
                  <Text strong>Tiêu đề chính</Text>
                  <TextArea
                    value={settings.home.hero.hero_title}
                    onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, hero: { ...prev.home.hero, hero_title: val } } }))}
                    rows={2}
                  />
                </div>
                <div className="space-y-2">
                  <Text strong>Phụ đề</Text>
                  <TextArea
                    value={settings.home.hero.hero_subtitle}
                    onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, hero: { ...prev.home.hero, hero_subtitle: val } } }))}
                    rows={2}
                  />
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Text strong>Nút CTA chính</Text>
                    <Input
                      value={settings.home.hero.hero_cta_primary}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, hero: { ...prev.home.hero, hero_cta_primary: val } } }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Text strong>Nút CTA phụ</Text>
                    <Input
                      value={settings.home.hero.hero_cta_secondary}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, hero: { ...prev.home.hero, hero_cta_secondary: val } } }))}
                    />
                  </div>
                </div>
              </div>
            </Card>

            {/* Section Toggles */}
            <Card title="Bật/Tắt các Section" style={{ marginTop: 16 }}>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Text>Section Tính năng</Text>
                  <Switch
                    checked={settings.home.features.features_enabled}
                    onChange={(checked) => setSettings(prev => ({ ...prev, home: { ...prev.home, features: { ...prev.home.features, features_enabled: checked } } }))}
                  />
                </div>
                <Divider />
                <div className="flex items-center justify-between">
                  <Text>Section Bảng giá</Text>
                  <Switch
                    checked={settings.home.pricing.pricing_enabled}
                    onChange={(checked) => setSettings(prev => ({ ...prev, home: { ...prev.home, pricing: { ...prev.home.pricing, pricing_enabled: checked } } }))}
                  />
                </div>
                <Divider />
                <div className="flex items-center justify-between">
                  <Text>Section CTA</Text>
                  <Switch
                    checked={settings.home.cta.cta_enabled}
                    onChange={(checked) => setSettings(prev => ({ ...prev, home: { ...prev.home, cta: { ...prev.home.cta, cta_enabled: checked } } }))}
                  />
                </div>
                <Divider />
                <div className="flex items-center justify-between">
                  <Text>Section Đánh giá</Text>
                  <Switch
                    checked={settings.home.testimonials.testimonials_enabled}
                    onChange={(checked) => setSettings(prev => ({ ...prev, home: { ...prev.home, testimonials: { ...prev.home.testimonials, testimonials_enabled: checked } } }))}
                  />
                </div>
              </div>
            </Card>

            {/* Menu Items */}
            <Card title={<span><MenuIcon className="h-5 w-5 inline mr-2" />Menu Navigation</span>} style={{ marginTop: 16 }}>
              <div className="space-y-4">
                {settings.home.menu.menu_items.map((item, index) => (
                  <div key={index} className="flex gap-2 items-end bg-gray-50 p-3 rounded">
                    <div className="flex-1 space-y-1">
                      <Text size="small">Label</Text>
                      <Input
                        value={item.label}
                        onChange={(val) => updateMenuItem(index, "label", val)}
                        placeholder="Tính năng"
                      />
                    </div>
                    <div className="flex-1 space-y-1">
                      <Text size="small">Link</Text>
                      <Input
                        value={item.href}
                        onChange={(val) => updateMenuItem(index, "href", val)}
                        placeholder="#features"
                      />
                    </div>
                    <Button type="danger" icon={<IconDelete />} onClick={() => removeMenuItem(index)} />
                  </div>
                ))}
                <Button icon={<IconPlus />} onClick={addMenuItem} block>Thêm menu</Button>
              </div>
            </Card>

            {/* Footer */}
            <Card title={<span><MessageSquare className="h-5 w-5 inline mr-2" />Footer</span>} style={{ marginTop: 16 }}>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Text strong>Mô tả thương hiệu</Text>
                  <TextArea
                    value={settings.home.footer.footer_brand_description}
                    onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, footer: { ...prev.home.footer, footer_brand_description: val } } }))}
                    rows={2}
                  />
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Text strong>Địa chỉ</Text>
                    <Input
                      value={settings.home.footer.footer_address}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, footer: { ...prev.home.footer, footer_address: val } } }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Text strong>Copyright</Text>
                    <Input
                      value={settings.home.footer.footer_copyright}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, footer: { ...prev.home.footer, footer_copyright: val } } }))}
                    />
                  </div>
                </div>
                <Divider />
                <Text strong>Social Links</Text>
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Text size="small">Facebook</Text>
                    <Input
                      value={settings.home.footer.footer_social_facebook}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, footer: { ...prev.home.footer, footer_social_facebook: val } } }))}
                      placeholder="https://facebook.com/..."
                    />
                  </div>
                  <div className="space-y-2">
                    <Text size="small">Twitter</Text>
                    <Input
                      value={settings.home.footer.footer_social_twitter}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, footer: { ...prev.home.footer, footer_social_twitter: val } } }))}
                      placeholder="https://twitter.com/..."
                    />
                  </div>
                  <div className="space-y-2">
                    <Text size="small">LinkedIn</Text>
                    <Input
                      value={settings.home.footer.footer_social_linkedin}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, footer: { ...prev.home.footer, footer_social_linkedin: val } } }))}
                      placeholder="https://linkedin.com/..."
                    />
                  </div>
                </div>
              </div>
            </Card>
          </TabPane>

          {/* Content Tab */}
          <TabPane tab={<span><IconFile style={{ marginRight: 8 }} />Nội dung</span>} itemKey="content">
            {/* Features List */}
            <Card title={<span><ImageIcon className="h-5 w-5 inline mr-2" />Danh sách Tính năng</span>} style={{ marginTop: 16 }}>
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Text strong>Tiêu đề section</Text>
                    <Input
                      value={settings.home.features.features_title}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, features: { ...prev.home.features, features_title: val } } }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Text strong>Phụ đề section</Text>
                    <Input
                      value={settings.home.features.features_subtitle}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, features: { ...prev.home.features, features_subtitle: val } } }))}
                    />
                  </div>
                </div>
                <Divider />
                {settings.home.features.features_list.map((feature, index) => (
                  <div key={index} className="p-4 border rounded bg-gray-50 mb-4">
                    <div className="flex gap-4">
                      <div className="flex-1 space-y-3">
                        <div className="grid gap-4 md:grid-cols-2">
                          <div className="space-y-1">
                            <Text size="small">Icon (Lucide)</Text>
                            <Input
                              value={feature.icon}
                              onChange={(val) => updateFeature(index, "icon", val)}
                              placeholder="Bot, Shield, TrendingUp"
                            />
                          </div>
                          <div className="space-y-1">
                            <Text size="small">Tiêu đề</Text>
                            <Input
                              value={feature.title}
                              onChange={(val) => updateFeature(index, "title", val)}
                            />
                          </div>
                        </div>
                        <div className="space-y-1">
                          <Text size="small">Mô tả</Text>
                          <TextArea
                            value={feature.description}
                            onChange={(val) => updateFeature(index, "description", val)}
                            rows={2}
                          />
                        </div>
                      </div>
                      <Button type="danger" icon={<IconDelete />} onClick={() => removeFeature(index)} />
                    </div>
                  </div>
                ))}
                <Button icon={<IconPlus />} onClick={addFeature} block>Thêm tính năng</Button>
              </div>
            </Card>

            {/* Testimonials */}
            <Card title={<span><Star className="h-5 w-5 inline mr-2" />Danh sách Đánh giá</span>} style={{ marginTop: 16 }}>
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Text strong>Tiêu đề section</Text>
                    <Input
                      value={settings.home.testimonials.testimonials_title}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, testimonials: { ...prev.home.testimonials, testimonials_title: val } } }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Text strong>Phụ đề section</Text>
                    <Input
                      value={settings.home.testimonials.testimonials_subtitle}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, testimonials: { ...prev.home.testimonials, testimonials_subtitle: val } } }))}
                    />
                  </div>
                </div>
                <Divider />
                {settings.home.testimonials.testimonials_list.map((testimonial, index) => (
                  <div key={index} className="p-4 border rounded bg-gray-50 mb-4">
                    <div className="flex gap-4">
                      <div className="flex-1 space-y-3">
                        <div className="grid gap-4 md:grid-cols-3">
                          <div className="space-y-1">
                            <Text size="small">Tên</Text>
                            <Input
                              value={testimonial.name}
                              onChange={(val) => updateTestimonial(index, "name", val)}
                            />
                          </div>
                          <div className="space-y-1">
                            <Text size="small">Chức vụ</Text>
                            <Input
                              value={testimonial.role}
                              onChange={(val) => updateTestimonial(index, "role", val)}
                            />
                          </div>
                          <div className="space-y-1">
                            <Text size="small">Rating (1-5)</Text>
                            <Input
                              type="number"
                              min={1}
                              max={5}
                              value={testimonial.rating}
                              onChange={(val) => updateTestimonial(index, "rating", parseInt(val))}
                            />
                          </div>
                        </div>
                        <div className="space-y-1">
                          <Text size="small">Avatar URL</Text>
                          <Input
                            value={testimonial.avatar}
                            onChange={(val) => updateTestimonial(index, "avatar", val)}
                            placeholder="https://ui-avatars.com/api/?name=..."
                          />
                        </div>
                        <div className="space-y-1">
                          <Text size="small">Nội dung đánh giá</Text>
                          <TextArea
                            value={testimonial.content}
                            onChange={(val) => updateTestimonial(index, "content", val)}
                            rows={2}
                          />
                        </div>
                      </div>
                      <Button type="danger" icon={<IconDelete />} onClick={() => removeTestimonial(index)} />
                    </div>
                  </div>
                ))}
                <Button icon={<IconPlus />} onClick={addTestimonial} block>Thêm đánh giá</Button>
              </div>
            </Card>

            {/* CTA Section */}
            <Card title={<span><Users className="h-5 w-5 inline mr-2" />CTA Section</span>} style={{ marginTop: 16 }}>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Text strong>Tiêu đề</Text>
                  <Input
                    value={settings.home.cta.cta_title}
                    onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, cta: { ...prev.home.cta, cta_title: val } } }))}
                  />
                </div>
                <div className="space-y-2">
                  <Text strong>Phụ đề</Text>
                  <TextArea
                    value={settings.home.cta.cta_subtitle}
                    onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, cta: { ...prev.home.cta, cta_subtitle: val } } }))}
                    rows={2}
                  />
                </div>
                <div className="space-y-2">
                  <Text strong>Nút CTA</Text>
                  <Input
                    value={settings.home.cta.cta_button_text}
                    onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, cta: { ...prev.home.cta, cta_button_text: val } } }))}
                  />
                </div>
              </div>
            </Card>

            {/* Pricing */}
            <Card title={<span><CreditCard className="h-5 w-5 inline mr-2" />Pricing Section</span>} style={{ marginTop: 16 }}>
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Text strong>Tiêu đề</Text>
                    <Input
                      value={settings.home.pricing.pricing_title}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, pricing: { ...prev.home.pricing, pricing_title: val } } }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Text strong>Phụ đề</Text>
                    <Input
                      value={settings.home.pricing.pricing_subtitle}
                      onChange={(val) => setSettings(prev => ({ ...prev, home: { ...prev.home, pricing: { ...prev.home.pricing, pricing_subtitle: val } } }))}
                    />
                  </div>
                </div>
              </div>
            </Card>

          </TabPane>

          <TabPane tab={<span><IconBell style={{ marginRight: 8 }} />Thông báo</span>} itemKey="notifications">
            <div className="grid gap-6 md:grid-cols-2" style={{ marginTop: 16 }}>
              <NotificationTester />
              <VoiceShortcutsHelp />
            </div>
          </TabPane>

          {/* Branding Tab */}
          <TabPane tab={<span><Building2 className="h-4 w-4 inline mr-2" />Branding</span>} itemKey="branding">
            <div style={{ marginTop: 16 }}>
              <BrandingSettingsCard
                settings={{
                  parent_company_name: (settings as any).branding?.parent_company_name || 'Bizino.AI',
                  parent_company_url: (settings as any).branding?.parent_company_url || 'https://bizino.ai',
                  company_badge_text: (settings as any).branding?.company_badge_text || 'by Bizino.AI',
                }}
                onChange={(branding) => setSettings(prev => ({ ...prev, branding } as any))}
              />
            </div>
          </TabPane>

          {/* Solutions Tab */}
          <TabPane tab={<span><Lightbulb className="h-4 w-4 inline mr-2" />Solutions</span>} itemKey="solutions">
            <div style={{ marginTop: 16 }}>
              <SolutionsSettingsCard
                settings={{
                  solutions_enabled: settings.home?.solutions?.solutions_enabled ?? true,
                  solutions_title: settings.home?.solutions?.solutions_title || 'Giải pháp',
                  solutions_subtitle: settings.home?.solutions?.solutions_subtitle || '',
                  solutions_list: settings.home?.solutions?.solutions_list || [],
                }}
                onChange={(solutions) => setSettings(prev => ({
                  ...prev,
                  home: {
                    ...prev.home,
                    solutions
                  }
                } as any))}
              />
            </div>
          </TabPane>

          {/* FAQ Tab */}
          <TabPane tab={<span><HelpCircle className="h-4 w-4 inline mr-2" />FAQ</span>} itemKey="faq">
            <div style={{ marginTop: 16 }}>
              <FAQSettingsCard
                settings={{
                  faq_enabled: settings.home?.faq?.faq_enabled ?? true,
                  faq_title: settings.home?.faq?.faq_title || 'Câu hỏi thường gặp',
                  faq_subtitle: settings.home?.faq?.faq_subtitle || '',
                  faq_list: settings.home?.faq?.faq_list || [],
                }}
                onChange={(faq) => setSettings(prev => ({
                  ...prev,
                  home: {
                    ...prev.home,
                    faq
                  }
                } as any))}
              />
            </div>
          </TabPane>

          {/* Email/SMTP Tab */}
          <TabPane tab={<span><Mail className="h-4 w-4 inline mr-2" />Email</span>} itemKey="email">
            <Card
              title={<span><Mail className="h-5 w-5 inline mr-2" />Cấu hình SMTP (Gửi Email)</span>}
              headerExtraContent={<Text type="tertiary">Gmail, SendGrid, hoặc SMTP server khác</Text>}
              style={{ marginTop: 16 }}
            >
              <div className="space-y-4">
                {/* Enable Switch */}
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <Text strong>Bật gửi Email</Text>
                    <Text type="tertiary" size="small" style={{ display: 'block' }}>
                      Cho phép hệ thống gửi email (quên mật khẩu, thông báo, etc.)
                    </Text>
                  </div>
                  <Switch
                    checked={smtpSettings.enabled}
                    onChange={(checked) => setSmtpSettings(prev => ({ ...prev, enabled: checked }))}
                  />
                </div>

                <Divider />

                {/* SMTP Server Settings */}
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Text strong>SMTP Host</Text>
                    <Input
                      value={smtpSettings.host}
                      onChange={(val) => setSmtpSettings(prev => ({ ...prev, host: val }))}
                      placeholder="smtp.gmail.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Text strong>SMTP Port</Text>
                    <Input
                      type="number"
                      value={String(smtpSettings.port)}
                      onChange={(val) => setSmtpSettings(prev => ({ ...prev, port: parseInt(val) || 587 }))}
                      placeholder="587"
                    />
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Text strong>Username (Email)</Text>
                    <Input
                      value={smtpSettings.username}
                      onChange={(val) => setSmtpSettings(prev => ({ ...prev, username: val }))}
                      placeholder="your-email@gmail.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Text strong>Password (App Password)</Text>
                    <Input
                      type="password"
                      value={smtpSettings.password}
                      onChange={(val) => setSmtpSettings(prev => ({ ...prev, password: val }))}
                      placeholder="xxxx xxxx xxxx xxxx"
                    />
                    <Text type="tertiary" size="small">
                      Với Gmail, dùng <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" style={{ color: '#667eea' }}>App Password</a>
                    </Text>
                  </div>
                </div>

                <Divider />

                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Text strong>From Email</Text>
                    <Input
                      value={smtpSettings.from_email}
                      onChange={(val) => setSmtpSettings(prev => ({ ...prev, from_email: val }))}
                      placeholder="noreply@your-domain.com"
                    />
                  </div>
                  <div className="space-y-2">
                    <Text strong>From Name</Text>
                    <Input
                      value={smtpSettings.from_name}
                      onChange={(val) => setSmtpSettings(prev => ({ ...prev, from_name: val }))}
                      placeholder="Xiaozhi AI"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <Switch
                    checked={smtpSettings.use_tls}
                    onChange={(checked) => setSmtpSettings(prev => ({ ...prev, use_tls: checked }))}
                  />
                  <Text>Sử dụng TLS (khuyến nghị)</Text>
                </div>

                {/* Save Button */}
                <div className="flex justify-end pt-4">
                  <Button
                    icon={<IconSave />}
                    theme="solid"
                    onClick={saveSmtpSettings}
                    loading={smtpLoading}
                  >
                    Lưu cấu hình SMTP
                  </Button>
                </div>
              </div>
            </Card>

            {/* Test Email */}
            <Card
              title="Test gửi Email"
              headerExtraContent={<Text type="tertiary">Gửi email thử để kiểm tra cấu hình</Text>}
              style={{ marginTop: 16 }}
            >
              <div className="flex gap-4 items-end">
                <div className="flex-1 space-y-2">
                  <Text strong>Email nhận test</Text>
                  <Input
                    value={testEmail}
                    onChange={(val) => setTestEmail(val)}
                    placeholder="your-email@example.com"
                  />
                </div>
                <Button
                  onClick={testSmtpConnection}
                  loading={smtpTesting}
                  disabled={!smtpSettings.enabled}
                >
                  Gửi Email Test
                </Button>
              </div>
              {!smtpSettings.enabled && (
                <Text type="warning" size="small" style={{ marginTop: 8, display: 'block' }}>
                  ⚠️ Bật "Gửi Email" trước khi test
                </Text>
              )}
            </Card>
          </TabPane>
        </Tabs>
      </div>
    </>
  );
};

export default SettingsPage;
