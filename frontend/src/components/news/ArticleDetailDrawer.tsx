import { toast } from "sonner";
/**
 * Article Detail Drawer - Full content view with AI summary
 */
import { useState } from "react";
import { SideSheet, Typography, Button, Divider, Spin,  Empty } from "@douyinfe/semi-ui";
import { IconExternalOpen, IconStar } from "@douyinfe/semi-icons";
import ReactMarkdown from "react-markdown";
import newsService, { type ArticleDetailResponse } from "@/services/newsService";

const { Text, Paragraph } = Typography;

interface ArticleDetailDrawerProps {
    visible: boolean;
    articleUrl: string | null;
    articleTitle: string;
    source: string;
    onClose: () => void;
}

export function ArticleDetailDrawer({
    visible,
    articleUrl,
    articleTitle,
    source,
    onClose,
}: ArticleDetailDrawerProps) {
    const [article, setArticle] = useState<ArticleDetailResponse | null>(null);
    const [summary, setSummary] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const [summarizing, setSummarizing] = useState(false);

    // Load article when visible changes
    useState(() => {
        if (visible && articleUrl && !article) {
            loadArticle();
        }
    });

    const loadArticle = async () => {
        if (!articleUrl) return;
        
        setLoading(true);
        try {
            const data = await newsService.getArticleDetail({
                url: articleUrl,
                source: source,
            });
            setArticle(data);
        } catch (error) {
            console.error("Failed to load article:", error);
            toast.error("Không thể tải nội dung bài viết");
        } finally {
            setLoading(false);
        }
    };

    const handleSummarize = async () => {
        if (!articleUrl) return;

        setSummarizing(true);
        try {
            const data = await newsService.summarizeArticle({
                url: articleUrl,
                source: source,
            });
            setSummary(data.summary);
            toast.success("Đã tóm tắt bài viết");
        } catch (error) {
            console.error("Failed to summarize:", error);
            toast.error("Không thể tóm tắt bài viết");
        } finally {
            setSummarizing(false);
        }
    };

    const handleAfterClose = () => {
        // Reset state
        setArticle(null);
        setSummary("");
    };

    return (
        <SideSheet
            title={articleTitle}
            visible={visible}
            onCancel={onClose}
            width={700}
            afterVisibleChange={(visible) => {
                if (!visible) handleAfterClose();
                if (visible && articleUrl && !article) loadArticle();
            }}
            headerStyle={{ borderBottom: '1px solid var(--semi-color-border)' }}
        >
            <div style={{ padding: '24px 0' }}>
                {loading ? (
                    <div style={{ textAlign: 'center', padding: '60px 0' }}>
                        <Spin size="large" tip="Đang tải nội dung..." />
                    </div>
                ) : article ? (
                    <>
                        {/* Article Meta */}
                        <div style={{ marginBottom: 24 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                                <Text type="tertiary">
                                    Nguồn: {article.source} {article.pub_date && `• ${new Date(article.pub_date).toLocaleDateString('vi-VN')}`}
                                </Text>
                                <Button
                                    icon={<IconExternalOpen />}
                                    theme="borderless"
                                    size="small"
                                    onClick={() => window.open(article.link, '_blank')}
                                >
                                    Mở bài gốc
                                </Button>
                            </div>
                            <Divider />
                        </div>

                        {/* AI Summary Section */}
                        {summary && (
                            <div
                                style={{
                                    background: 'var(--semi-color-fill-0)',
                                    padding: 16,
                                    borderRadius: 8,
                                    marginBottom: 24,
                                    border: '1px solid var(--semi-color-border)',
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                                    <IconStar style={{ color: 'var(--semi-color-warning)' }} />
                                    <Text strong>AI Tóm tắt</Text>
                                </div>
                                <Paragraph style={{ margin: 0 }}>{summary}</Paragraph>
                            </div>
                        )}

                        {!summary && (
                            <Button
                                icon={<IconStar />}
                                onClick={handleSummarize}
                                loading={summarizing}
                                block
                                style={{ marginBottom: 24 }}
                            >
                                {summarizing ? 'Đang tóm tắt...' : 'Tóm tắt bài viết bằng AI'}
                            </Button>
                        )}

                        {/* Article Content */}
                        <div style={{ lineHeight: '1.8' }}>
                            <ReactMarkdown>{article.content}</ReactMarkdown>
                        </div>
                    </>
                ) : (
                    <Empty
                        title="Không thể tải nội dung"
                        description="Vui lòng thử lại sau"
                    >
                        <Button onClick={loadArticle}>Thử lại</Button>
                    </Empty>
                )}
            </div>
        </SideSheet>
    );
}

export default ArticleDetailDrawer;
