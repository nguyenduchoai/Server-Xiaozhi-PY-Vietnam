import { toast } from "sonner";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Button, Card, Input, Typography} from "@douyinfe/semi-ui";
import { IconMail, IconArrowLeft } from "@douyinfe/semi-icons";
import { apiClient } from "@/config/axios-instance";

const { Title, Text } = Typography;

export function ForgotPasswordPage() {
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!email) {
            toast.error("Vui lòng nhập email");
            return;
        }

        setLoading(true);
        try {
            await apiClient.post("/auth/forgot-password", { email });
            setSubmitted(true);
        } catch (error: any) {
            // Still show success for security (don't reveal if email exists)
            setSubmitted(true);
        } finally {
            setLoading(false);
        }
    };

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
                {!submitted ? (
                    <>
                        {/* Header */}
                        <div className="text-center mb-8">
                            <div className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center"
                                style={{ background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)" }}>
                                <IconMail size="extra-large" style={{ color: "white" }} />
                            </div>
                            <Title heading={3} style={{ margin: 0 }}>Quên Mật Khẩu?</Title>
                            <Text type="tertiary" style={{ marginTop: 8, display: "block" }}>
                                Nhập email của bạn và chúng tôi sẽ gửi link đặt lại mật khẩu
                            </Text>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit}>
                            <div className="space-y-4">
                                <div>
                                    <Text strong style={{ marginBottom: 8, display: "block" }}>
                                        Email
                                    </Text>
                                    <Input
                                        prefix={<IconMail />}
                                        placeholder="your-email@example.com"
                                        value={email}
                                        onChange={(v) => setEmail(v)}
                                        size="large"
                                        type="email"
                                        autoFocus
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
                                    Gửi Link Đặt Lại Mật Khẩu
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
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#4caf50" strokeWidth="2">
                                <polyline points="20,6 9,17 4,12" />
                            </svg>
                        </div>
                        <Title heading={3} style={{ margin: 0 }}>Kiểm Tra Email!</Title>
                        <Text type="tertiary" style={{ marginTop: 12, display: "block", lineHeight: 1.6 }}>
                            Nếu email <strong>{email}</strong> tồn tại trong hệ thống,
                            chúng tôi đã gửi link đặt lại mật khẩu.
                        </Text>
                        <Text type="tertiary" style={{ marginTop: 8, display: "block" }}>
                            (Link sẽ hết hạn sau 30 phút)
                        </Text>

                        <div className="mt-8 space-y-3">
                            <Button
                                theme="solid"
                                size="large"
                                block
                                onClick={() => {
                                    setSubmitted(false);
                                    setEmail("");
                                }}
                                style={{
                                    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                                    border: "none",
                                }}
                            >
                                Thử Email Khác
                            </Button>
                            <Link to="/login" style={{ display: "block" }}>
                                <Button theme="borderless" size="large" block>
                                    Quay lại Đăng nhập
                                </Button>
                            </Link>
                        </div>
                    </div>
                )}
            </Card>
        </div>
    );
}

export default ForgotPasswordPage;
