import { useEffect } from "react";
import { useAtom, useAtomValue } from "jotai";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Form,
  Button,
  Typography,
  Banner
} from "@douyinfe/semi-ui";
import { useLogin } from "@/queries/auth-queries";
import { PageHead } from "@/components/PageHead";
import { authErrorAtom, isAuthenticatedAtom } from "@/store/auth-atom";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useSiteSettings } from "@/hooks/useSiteSettings";

const { Title, Text } = Typography;

interface LoginFormValues {
  username: string;
  password: string;
}

export const LoginPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation("auth");
  const { mutate: login, isPending } = useLogin();
  const [authError, setAuthError] = useAtom(authErrorAtom);
  const isAuthenticated = useAtomValue(isAuthenticatedAtom);
  const { data: siteSettings } = useSiteSettings();
  const siteLogo = siteSettings?.web?.site_logo || "/logo.jpg";
  const siteName = siteSettings?.web?.site_name || "AI Assistant";

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      setAuthError(null);
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate, setAuthError]);

  const handleSubmit = (values: LoginFormValues) => {
    setAuthError(null);

    login(
      { username: values.username, password: values.password },
      {
        onSuccess: () => {
          // Redirect is handled by useEffect watching isAuthenticated
        },
        onError: (error: any) => {
          const message =
            error.response?.data?.message ||
            t("login.error_invalid_credentials");
          setAuthError(message);
        },
      }
    );
  };

  return (
    <>
      <PageHead
        title="auth:login.page_title"
        description="auth:login.page_description"
        translateTitle
        translateDescription
      />
      <div
        className="relative flex min-h-screen overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, #0f0c29 0%, #1a1040 30%, #24243e 60%, #0f0c29 100%)',
        }}
      >
        {/* Animated Background Orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
          <div
            className="absolute rounded-full"
            style={{
              width: '600px',
              height: '600px',
              top: '-10%',
              right: '-10%',
              background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, transparent 70%)',
              filter: 'blur(80px)',
              animation: 'float 8s ease-in-out infinite',
            }}
          />
          <div
            className="absolute rounded-full"
            style={{
              width: '500px',
              height: '500px',
              bottom: '-5%',
              left: '-5%',
              background: 'radial-gradient(circle, rgba(236, 72, 153, 0.12) 0%, transparent 70%)',
              filter: 'blur(80px)',
              animation: 'float 10s ease-in-out infinite reverse',
            }}
          />
          <div
            className="absolute rounded-full"
            style={{
              width: '300px',
              height: '300px',
              top: '40%',
              left: '50%',
              transform: 'translateX(-50%)',
              background: 'radial-gradient(circle, rgba(6, 182, 212, 0.08) 0%, transparent 70%)',
              filter: 'blur(60px)',
              animation: 'float 12s ease-in-out infinite',
            }}
          />
          {/* Grid Pattern */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              backgroundImage: `
                linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)
              `,
              backgroundSize: '60px 60px',
            }}
          />
        </div>

        {/* Language Switcher */}
        <div className="absolute top-6 right-6 z-20">
          <LanguageSwitcher />
        </div>

        {/* Main Content */}
        <div className="relative z-10 flex w-full items-center justify-center px-4 py-12">
          <div
            className="w-full max-w-[420px]"
            style={{
              animation: 'loginCardEntry 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
            }}
          >
            {/* Glass Card */}
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.04)',
                backdropFilter: 'blur(24px)',
                WebkitBackdropFilter: 'blur(24px)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '24px',
                padding: '40px 36px',
                boxShadow: '0 32px 64px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255,255,255,0.05)',
              }}
            >
              {/* Logo + Header */}
              <div className="text-center" style={{ marginBottom: '32px' }}>
                <div className="flex justify-center" style={{ marginBottom: '20px' }}>
                  <div
                    style={{
                      position: 'relative',
                      width: '72px',
                      height: '72px',
                    }}
                  >
                    {/* Glow ring */}
                    <div
                      style={{
                        position: 'absolute',
                        inset: '-4px',
                        borderRadius: '20px',
                        background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.5), rgba(236, 72, 153, 0.5))',
                        filter: 'blur(12px)',
                        opacity: 0.6,
                        animation: 'pulse 3s ease-in-out infinite',
                      }}
                    />
                    <img
                      src={siteLogo}
                      alt={siteName}
                      style={{
                        position: 'relative',
                        width: '72px',
                        height: '72px',
                        borderRadius: '18px',
                        objectFit: 'cover',
                        border: '2px solid rgba(255, 255, 255, 0.1)',
                        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
                      }}
                      onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                    />
                  </div>
                </div>
                <Title
                  heading={3}
                  style={{
                    marginBottom: '8px',
                    color: '#F5F5F7',
                    letterSpacing: '-0.02em',
                    fontWeight: 700,
                  }}
                >
                  {t("login.welcome_back")}
                </Title>
                <Text style={{ color: 'rgba(255,255,255,0.5)', fontSize: '14px' }}>
                  {t("login.subtitle")}
                </Text>
              </div>

              {/* Error Banner */}
              {authError && (
                <Banner
                  type="danger"
                  description={authError}
                  style={{
                    marginBottom: '20px',
                    borderRadius: '12px',
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.2)',
                  }}
                  closeIcon={null}
                />
              )}

              {/* Login Form */}
              <Form
                onSubmit={handleSubmit}
                labelPosition="top"
                disabled={isPending}
                className="login-form-dark"
              >
                <Form.Input
                  field="username"
                  label={
                    <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: '13px', fontWeight: 500 }}>
                      {t("login.email_label")}
                    </span>
                  }
                  placeholder="m@example.com"
                  rules={[
                    { required: true, message: t("login.email_required", "Email is required") },
                    { type: 'email', message: t("login.email_invalid", "Invalid email format") },
                  ]}
                  showClear
                  style={{ marginBottom: '4px' }}
                />

                <Form.Input
                  field="password"
                  label={
                    <div className="flex items-center justify-between w-full">
                      <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: '13px', fontWeight: 500 }}>
                        {t("login.password_label")}
                      </span>
                      <span
                        onClick={() => navigate("/forgot-password")}
                        style={{
                          cursor: 'pointer',
                          color: 'rgba(129, 140, 248, 0.8)',
                          fontSize: '12px',
                          fontWeight: 500,
                          transition: 'color 0.2s',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.color = '#818CF8')}
                        onMouseLeave={(e) => (e.currentTarget.style.color = 'rgba(129, 140, 248, 0.8)')}
                      >
                        {t("login.forgot_password_question")}
                      </span>
                    </div>
                  }
                  placeholder={t("login.password_placeholder")}
                  mode="password"
                  rules={[
                    { required: true, message: t("login.password_required", "Password is required") },
                    { min: 6, message: t("login.password_min", "Password must be at least 6 characters") },
                  ]}
                />

                {/* Submit Button */}
                <Button
                  type="primary"
                  theme="solid"
                  htmlType="submit"
                  block
                  loading={isPending}
                  style={{
                    marginTop: '24px',
                    height: '48px',
                    borderRadius: '14px',
                    background: 'linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #A855F7 100%)',
                    border: 'none',
                    fontSize: '15px',
                    fontWeight: 600,
                    letterSpacing: '-0.01em',
                    boxShadow: '0 8px 24px rgba(99, 102, 241, 0.35), inset 0 1px 0 rgba(255,255,255,0.15)',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)';
                    (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 12px 32px rgba(99, 102, 241, 0.45), inset 0 1px 0 rgba(255,255,255,0.15)';
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)';
                    (e.currentTarget as HTMLButtonElement).style.boxShadow = '0 8px 24px rgba(99, 102, 241, 0.35), inset 0 1px 0 rgba(255,255,255,0.15)';
                  }}
                >
                  {isPending ? t("login.loading") : t("login.submit", "Login")}
                </Button>
              </Form>

              {/* Divider */}
              <div
                className="flex items-center gap-4"
                style={{ margin: '28px 0 20px' }}
              >
                <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.06)' }} />
                <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  hoặc
                </span>
                <div style={{ flex: 1, height: '1px', background: 'rgba(255,255,255,0.06)' }} />
              </div>

              {/* Footer */}
              <div className="text-center">
                <Text style={{ color: 'rgba(255,255,255,0.35)', fontSize: '13px' }}>
                  Cần tài khoản?{' '}
                  <span
                    onClick={() => navigate("/register")}
                    style={{
                      color: 'rgba(129, 140, 248, 0.8)',
                      cursor: 'pointer',
                      fontWeight: 500,
                      transition: 'color 0.2s',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.color = '#818CF8')}
                    onMouseLeave={(e) => (e.currentTarget.style.color = 'rgba(129, 140, 248, 0.8)')}
                  >
                    Liên hệ quản trị viên
                  </span>
                </Text>
              </div>
            </div>

            {/* Bottom branding */}
            <div className="text-center" style={{ marginTop: '24px' }}>
              <Text style={{ color: 'rgba(255,255,255,0.2)', fontSize: '12px' }}>
                {siteName} — AI & IoT Platform
              </Text>
            </div>
          </div>
        </div>
      </div>

      {/* Scoped Styles */}
      <style>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          33% { transform: translateY(-20px) rotate(1deg); }
          66% { transform: translateY(10px) rotate(-1deg); }
        }

        @keyframes loginCardEntry {
          0% { opacity: 0; transform: translateY(30px) scale(0.96); }
          100% { opacity: 1; transform: translateY(0) scale(1); }
        }

        @keyframes pulse {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 0.3; }
        }

        /* Dark Login Form Overrides */
        .login-form-dark .semi-input-wrapper {
          background: rgba(255, 255, 255, 0.04) !important;
          border: 1px solid rgba(255, 255, 255, 0.08) !important;
          border-radius: 12px !important;
          color: #F5F5F7 !important;
          transition: all 0.2s ease !important;
        }

        .login-form-dark .semi-input-wrapper:hover {
          border-color: rgba(255, 255, 255, 0.15) !important;
          background: rgba(255, 255, 255, 0.06) !important;
        }

        .login-form-dark .semi-input-wrapper-focus {
          border-color: rgba(99, 102, 241, 0.5) !important;
          box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.12) !important;
          background: rgba(255, 255, 255, 0.06) !important;
        }

        .login-form-dark .semi-input {
          color: #F5F5F7 !important;
        }

        .login-form-dark .semi-input::placeholder {
          color: rgba(255, 255, 255, 0.25) !important;
        }

        .login-form-dark .semi-input-clearbtn {
          color: rgba(255, 255, 255, 0.3) !important;
        }

        .login-form-dark .semi-input-suffix .semi-icon {
          color: rgba(255, 255, 255, 0.3) !important;
        }

        .login-form-dark .semi-form-field-label-text {
          color: rgba(255, 255, 255, 0.7) !important;
        }
      `}</style>
    </>
  );
};

export default LoginPage;
