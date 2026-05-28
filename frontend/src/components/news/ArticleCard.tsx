/**
 * Article Card - Display news article in card format
 */
import { Card, Typography, Button, Image } from "@douyinfe/semi-ui";
import { IconEyeOpened, IconStar } from "@douyinfe/semi-icons";
import { Clock } from "lucide-react";
import type { NewsArticle } from "@/services/newsService";

const { Text, Paragraph } = Typography;

interface ArticleCardProps {
    article: NewsArticle;
    onRead: () => void;
    onSummarize: () => void;
    loading?: boolean;
}

export function ArticleCard({ article, onRead, onSummarize, loading }: ArticleCardProps) {
    return (
        <Card
            shadows="hover"
            style={{ cursor: 'pointer' }}
            bodyStyle={{ padding: 16 }}
            cover={
                article.image_url ? (
                    <Image
                        src={article.image_url}
                        alt={article.title}
                        height={200}
                        width="100%"
                        style={{ objectFit: 'cover' }}
                        placeholder={
                            <div style={{ width: '100%', height: 200, background: 'var(--semi-color-fill-0)' }} />
                        }
                    />
                ) : undefined
            }
        >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {/* Title */}
                <Text strong style={{ fontSize: 16, lineHeight: 1.4 }}>
                    {article.title}
                </Text>

                {/* Description */}
                {article.description && (
                    <Paragraph
                        ellipsis={{ rows: 2 }}
                        style={{ margin: 0, color: 'var(--semi-color-text-1)' }}
                    >
                        {article.description}
                    </Paragraph>
                )}

                {/* Meta */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                    {article.pub_date && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                            <Clock size={14} color="var(--semi-color-text-2)" />
                            <Text type="tertiary" size="small">
                                {new Date(article.pub_date).toLocaleString('vi-VN', {
                                    year: 'numeric',
                                    month: '2-digit',
                                    day: '2-digit',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                })}
                            </Text>
                        </div>
                    )}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <Button
                        icon={<IconEyeOpened />}
                        onClick={onRead}
                        loading={loading}
                        block
                    >
                        Đọc chi tiết
                    </Button>
                    <Button
                        icon={<IconStar />}
                        onClick={onSummarize}
                        loading={loading}
                        theme="borderless"
                    >
                        Tóm tắt
                    </Button>
                </div>
            </div>
        </Card>
    );
}

export default ArticleCard;