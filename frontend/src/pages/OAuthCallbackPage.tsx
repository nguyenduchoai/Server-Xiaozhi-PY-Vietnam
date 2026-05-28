/**
 * OAuth Callback Page
 * Handles redirect from Google/Zalo OAuth login.
 * Exchanges the refresh cookie for an access token.
 */
import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useSetAtom } from "jotai";
import axios from "axios";
import { Spin, Typography } from "@douyinfe/semi-ui";
import { accessTokenAtom } from "@/store/auth-atom";
import { saveAccessToken } from "@/lib/token-storage";

const { Title, Text } = Typography;

export const OAuthCallbackPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const setAccessToken = useSetAtom(accessTokenAtom);

  useEffect(() => {
    const finishOAuth = async () => {
      if (searchParams.get("oauth") !== "success") {
        navigate("/login?error=oauth_failed", { replace: true });
        return;
      }

      try {
        const response = await axios.post(
          "/api/v1/auth/refresh",
          {},
          { withCredentials: true }
        );
        const token = response.data?.access_token;
        if (!token) {
          throw new Error("OAuth refresh did not return access token");
        }
        setAccessToken(token);
        saveAccessToken(token);
        navigate("/dashboard", { replace: true });
      } catch {
        navigate("/login?error=oauth_failed", { replace: true });
      }
    };

    finishOAuth();
  }, [searchParams, setAccessToken, navigate]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-[var(--semi-color-bg-0)]">
      <div className="text-center">
        <Spin size="large" />
        <Title heading={4} style={{ marginTop: 24 }}>
          Đang đăng nhập...
        </Title>
        <Text type="tertiary">Vui lòng chờ trong giây lát</Text>
      </div>
    </div>
  );
};

export default OAuthCallbackPage;
