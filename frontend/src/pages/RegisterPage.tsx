"use client";

import { useEffect, useState } from "react";
import { useAtom, useAtomValue } from "jotai";
import { useNavigate, useSearchParams } from "react-router-dom";

import { useTranslation } from "react-i18next";
import {
  Form,
  Button,
  Card,
  Typography,
  Divider,
  Banner
} from "@douyinfe/semi-ui";
import { IconEyeOpened, IconEyeClosedSolid } from "@douyinfe/semi-icons";
import { useRegister } from "@/queries/auth-queries";
import { PageHead } from "@/components/PageHead";
import { authErrorAtom, isAuthenticatedAtom } from "@/store/auth-atom";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";


const { Title, Text } = Typography;

interface RegisterFormValues {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export const RegisterPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { t } = useTranslation("auth");
  const { mutate: register, isPending } = useRegister();
  const [authError, setAuthError] = useAtom(authErrorAtom);
  const isAuthenticated = useAtomValue(isAuthenticatedAtom);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Get invitation token from URL
  const inviteToken = searchParams.get("invite");



  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = (values: RegisterFormValues) => {
    if (isPending) return;
    setAuthError(null);

    register(
      {
        name: values.name,
        email: values.email,
        password: values.password,
        invitation_token: inviteToken || undefined,
      },
      {
        onSuccess: () => {
          setAuthError(null);
          navigate("/login", { replace: true });
        },
        onError: (error: any) => {
          const message =
            error.response?.data?.message || t("register.error_network");
          setAuthError(message);
        },
      }
    );
  };

  // Custom validator for password confirmation
  const validateConfirmPassword = (
    val: string,
    values: any
  ): string => {
    if (val !== values.password) {
      return t("register.password_mismatch", "Passwords must match");
    }
    return "";
  };

  return (
    <>
      <PageHead
        title="auth:register.page_title"
        description="auth:register.page_description"
        translateTitle
        translateDescription
      />
      <div className="flex items-center justify-center min-h-screen bg-[var(--semi-color-bg-0)] px-4 relative">
        {/* Language Switcher */}
        <div className="absolute top-4 right-4">
          <LanguageSwitcher />
        </div>

        {/* Register Card */}
        <Card
          className="w-full max-w-md"
          style={{
            backgroundColor: 'var(--semi-color-bg-1)',
            border: '1px solid var(--semi-color-border)',
          }}
          bodyStyle={{ padding: '32px' }}
        >
          {/* Header */}
          <div className="text-center mb-6">
            <Title heading={3} style={{ marginBottom: 8 }}>
              {t("register.title")}
            </Title>
            <Text type="tertiary">
              {t("register.subtitle", "Create your account to get started")}
            </Text>
          </div>

          {/* Google Sign Up Button */}
          <Button
            block
            type="secondary"
            icon={
              <svg
                className="mr-2 h-4 w-4"
                aria-hidden="true"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 488 512"
              >
                <path
                  fill="currentColor"
                  d="M488 261.8C488 403.3 391.1 504 248 504 110.8 504 0 393.2 0 256S110.8 8 248 8c66.8 0 123 24.5 166.3 64.9l-67.5 64.9C258.5 52.6 94.3 116.6 94.3 256c0 86.5 69.1 156.6 153.7 156.6 98.2 0 135-70.4 140.8-106.9H248v-85.3h236.1c2.3 12.7 3.9 24.9 3.9 41.4z"
                />
              </svg>
            }
            style={{ marginBottom: 24 }}
          >
            {t("register.google_signup", "Sign up with Google")}
          </Button>

          {/* Divider */}
          <Divider margin="24px">
            <Text type="tertiary" size="small" style={{ textTransform: 'uppercase' }}>
              {t("register.or_continue", "Or continue with email")}
            </Text>
          </Divider>



          {/* Error Banner */}
          {authError && (
            <Banner
              type="danger"
              description={authError}
              style={{ marginBottom: 16 }}
              closeIcon={null}
            />
          )}

          {/* Registration Form */}
          <Form
            onSubmit={handleSubmit}
            labelPosition="top"
            disabled={isPending}
          >
            {/* Name Field */}
            <Form.Input
              field="name"
              label={t("register.name_label")}
              placeholder={t("register.name_placeholder")}
              rules={[
                { required: true, message: t("register.name_required", "Name is required") },
                { min: 2, message: t("register.name_min", "Name must be at least 2 characters") },
              ]}
              showClear
            />

            {/* Email Field */}
            <Form.Input
              field="email"
              label={t("register.email_label")}
              placeholder={t("register.email_placeholder")}
              rules={[
                { required: true, message: t("register.email_required", "Email is required") },
                { type: 'email', message: t("register.email_invalid", "Invalid email format") },
              ]}
              showClear
            />

            {/* Password Field */}
            <Form.Input
              field="password"
              label={t("register.password_label")}
              placeholder={t("register.password_placeholder")}
              mode="password"
              rules={[
                { required: true, message: t("register.password_required", "Password is required") },
                { min: 6, message: t("register.password_min", "Password must be at least 6 characters") },
              ]}
              suffix={
                <Button
                  type="tertiary"
                  theme="borderless"
                  icon={showPassword ? <IconEyeClosedSolid /> : <IconEyeOpened />}
                  onClick={() => setShowPassword(!showPassword)}
                  size="small"
                />
              }
            />

            {/* Confirm Password Field */}
            <Form.Input
              field="confirmPassword"
              label={t("register.confirm_password_label")}
              placeholder={t("register.confirm_password_placeholder")}
              mode="password"
              rules={[
                { required: true, message: t("register.confirm_required", "Please confirm your password") },
              ]}
              validate={validateConfirmPassword}
              suffix={
                <Button
                  type="tertiary"
                  theme="borderless"
                  icon={showConfirmPassword ? <IconEyeClosedSolid /> : <IconEyeOpened />}
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  size="small"
                />
              }
            />

            {/* Submit Button */}
            <Button
              type="primary"
              theme="solid"
              htmlType="submit"
              block
              loading={isPending}
              style={{ marginTop: 16, height: 40 }}
            >
              {isPending ? t("register.loading") : t("register.submit_button")}
            </Button>
          </Form>

          {/* Login Link */}
          <div className="text-center mt-6">
            <Text type="tertiary">
              {t("register.already_account", "Already have an account?")}{" "}
              <Text
                link
                onClick={() => navigate("/login")}
                style={{ cursor: 'pointer' }}
              >
                {t("register.login_link", "Sign in")}
              </Text>
            </Text>
          </div>
        </Card>
      </div>
    </>
  );
};

export default RegisterPage;
