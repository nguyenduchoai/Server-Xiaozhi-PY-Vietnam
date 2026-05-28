import { toast } from "sonner";
import { useState, useEffect } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { Button, Card, Input, Typography} from "@douyinfe/semi-ui";
import { IconLock, IconArrowLeft, IconTick } from "@douyinfe/semi-icons";
import { apiClient } from "@/config/axios-instance";

const { Title, Text } = Typography;

export function ResetPasswordPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    const [token] = useState(searchParams.get("token") || "");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState("");

    useEffect(() => {
        if (!token) {
            setError("Token không hợp lệ. Vui lòng yêu cầu link đặt lại mật khẩu mới.");
        }
    }, [token]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        // Validate
        if (!newPassword || !confirmPassword) {
            setError("Vui lòng nhập đầy đủ thông tin");
            return;
        }

        if (newPassword.length < 8) {
            setError("Mật khẩu phải có ít nhất 8 ký tự");
            return;
        }

        if (newPassword !== confirmPassword) {
            setError("Mật khẩu xác nhận không khớp");
            return;
        }

        setLoading(true);
        try {
            const response = await apiClient.post("/auth/reset-password", {
                token,
                new_password: newPassword,
            });

            setSuccess(true);
            toast.success(response.data.message || "Đặt lại mật khẩu thành công!");

            // Redirect to login after 2s
            setTimeout(() => {
                navigate("/login");
            }, 2000);

        } catch (err: any) {
            const detail = err.response?.data?.detail || "Đặt lại mật khẩu thất bại";
            setError(detail);
        } finally {
            setLoading(false);
        }
    };

    // No token - show error
    if (!token && !success) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4" style={{
                background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
            }}>
                <Card
                    style={{
                        width: "100%",
                        maxWidth: 420,
                        boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                        borderRadius: 16,
                    }}
                    bodyStyle={{ padding: 40 }}
                >
                    <div className="text-center">
                        <div className="w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center"
                            style={{ background: "#ffebee" }}>
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#f44336" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" />
                                <line x1="15" y1="9" x2="9" y2="15" />
                                <line x1="9" y1="9" x2="15" y2="15" />
                            </svg>
                        </div>
                        <Title heading={3} style={{ margin: 0 }}>Link Không Hợp Lệ</Title>
                        <Text type="tertiary" style={{ marginTop: 12, display: "block" }}>
                            Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.
                        </Text>

                        <div className="mt-8">
                            <Link to="/forgot-password">
                                <Button
                                    theme="solid"
                                    size="large"
                                    block
                                    style={{
                                        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                                        border: "none",
                                    }}
                                >
                                    Yêu Cầu Link Mới
                                </Button>
                            </Link>
                        </div>
                    </div>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4" style={{
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
        }}>
            <Card
                style={{
                    width: "100%",
                    maxWidth: 420,
                    boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
                    borderRadius: 16,
                }}
                bodyStyle={{ padding: 40 }}
            >
                {!success ? (
                    <>
                        {/* Header */}
                        <div className="text-center mb-8">
                            <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center"
                                style={{ background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" }}>
                                <IconLock size="extra-large" style={{ color: "white" }} />
                            </div>
                            <Title heading={3} style={{ margin: 0 }}>Đặt Mật Khẩu Mới</Title>
                            <Text type="tertiary" style={{ marginTop: 8, display: "block" }}>
                                Nhập mật khẩu mới cho tài khoản của bạn
                            </Text>
                        </div>

                        {/* Error message */}
                        {error && (
                            <div style={{
                                background: "#ffebee",
                                border: "1px solid #f44336",
                                borderRadius: 8,
                                padding: "12px 16px",
                                marginBottom: 16,
                                color: "#c62828",
                            }}>
                                {error}
                            </div>
                        )}

                        {/* Form */}
                        <form onSubmit={handleSubmit}>
                            <div className="space-y-4">
                                <div>
                                    <Text strong style={{ marginBottom: 8, display: "block" }}>
                                        Mật khẩu mới
                                    </Text>
                                    <Input
                                        prefix={<IconLock />}
                                        placeholder="Tối thiểu 8 ký tự"
                                        value={newPassword}
                                        onChange={(v) => setNewPassword(v)}
                                        size="large"
                                        type="password"
                                        autoFocus
                                    />
                                </div>

                                <div>
                                    <Text strong style={{ marginBottom: 8, display: "block" }}>
                                        Xác nhận mật khẩu
                                    </Text>
                                    <Input
                                        prefix={<IconLock />}
                                        placeholder="Nhập lại mật khẩu"
                                        value={confirmPassword}
                                        onChange={(v) => setConfirmPassword(v)}
                                        size="large"
                                        type="password"
                                    />
                                </div>

                                <Button
                                    htmlType="submit"
                                    theme="solid"
                                    size="large"
                                    block
                                    loading={loading}
                                    style={{
                                        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                                        border: "none",
                                        height: 48,
                                        fontSize: 16,
                                        fontWeight: 600,
                                    }}
                                >
                                    Đặt Lại Mật Khẩu
                                </Button>
                            </div>
                        </form>

                        {/* Back to login */}
                        <div className="text-center mt-6">
                            <Link to="/login" style={{
                                color: "#667eea",
                                textDecoration: "none",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4
                            }}>
                                <IconArrowLeft size="small" />
                                Quay lại Đăng nhập
                            </Link>
                        </div>
                    </>
                ) : (
                    /* Success State */
                    <div className="text-center">
                        <div className="w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center"
                            style={{ background: "#e8f5e9" }}>
                            <IconTick size="extra-large" style={{ color: "#4caf50" }} />
                        </div>
                        <Title heading={3} style={{ margin: 0 }}>Thành Công!</Title>
                        <Text type="tertiary" style={{ marginTop: 12, display: "block" }}>
                            Mật khẩu của bạn đã được đặt lại thành công.
                        </Text>
                        <Text type="tertiary" style={{ marginTop: 8, display: "block" }}>
                            Đang chuyển hướng đến trang đăng nhập...
                        </Text>

                        <div className="mt-8">
                            <Link to="/login">
                                <Button
                                    theme="solid"
                                    size="large"
                                    block
                                    style={{
                                        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                                        border: "none",
                                    }}
                                >
                                    Đăng Nhập Ngay
                                </Button>
                            </Link>
                        </div>
                    </div>
                )}
            </Card>
        </div>
    );
}

export default ResetPasswordPage;
