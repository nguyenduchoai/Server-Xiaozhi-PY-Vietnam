import { toast } from "sonner";
/**
 * News Page - Read latest news articles
 */
import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { PageHead } from "@/components";
import {
    Card,
    Select,
    Button,
    Typography,
    Empty,
    Spin,
    Row,
    Col} from "@douyinfe/semi-ui";
import {
    IconRefresh,
} from "@douyinfe/semi-icons";
import { Newspaper } from "lucide-react";

import newsService, { type NewsArticle, type TopicInfo } from "@/services/newsService";
import { ArticleCard, ArticleDetailDrawer } from "@/components/news";

const { Text } = Typography;

export function NewsPage() {
    const { t } = useTranslation("news");

    // State
    const [articles, setArticles] = useState<NewsArticle[]>([]);
    const [topics, setTopics] = useState<TopicInfo[]>([]);
    const [selectedSource, setSelectedSource] = useState<string>("vnexpress");
    const [selectedTopic, setSelectedTopic] = useState<string>("");
    const [loading, setLoading] = useState(false);

    // Detail drawer
    const [drawerVisible, setDrawerVisible] = useState(false);
    const [selectedArticle, setSelectedArticle] = useState<NewsArticle | null>(null);

    // Fetch topics on mount
    useEffect(() => {
        fetchTopics();
    }, [selectedSource]);

    const fetchTopics = async () => {
        try {
            const data = await newsService.getTopics(selectedSource);
            setTopics(data.topics);
            // Auto-select first topic
            if (data.topics.length > 0 && !selectedTopic) {
                setSelectedTopic(data.topics[0].name);
            }
        } catch (error) {
            console.error("Failed to fetch topics:", error);
            toast.error(t('error.fetch_topics_failed', 'Không thể tải danh sách chủ đề'));
        }
    };

    const fetchNews = useCallback(async () => {
        if (!selectedTopic) {
            toast.warning(t('warning.select_topic', 'Vui lòng chọn chủ đề'));
            return;
        }

        setLoading(true);
        try {
            const data = await newsService.getNewsList({
                source: selectedSource,
                topic: selectedTopic,
                max_articles: 10,
            });
            setArticles(data.articles);

            if (data.articles.length === 0) {
                toast.info(t('info.no_articles', 'Không tìm thấy tin tức'));
            }
        } catch (error) {
            console.error("Failed to fetch news:", error);
            toast.error(t('error.fetch_news_failed', 'Không thể tải tin tức'));
        } finally {
            setLoading(false);
        }
    }, [selectedSource, selectedTopic, t]);

    // Auto-fetch when topic changes
    useEffect(() => {
        if (selectedTopic) {
            fetchNews();
        }
    }, [selectedTopic, fetchNews]);

    const handleReadArticle = (article: NewsArticle) => {
        setSelectedArticle(article);
        setDrawerVisible(true);
    };

    const handleSummarizeArticle = async (article: NewsArticle) => {
        try {
            toast.info(t('info.generating_summary', 'Đang tạo tóm tắt...'));
            const data = await newsService.summarizeArticle({
                url: article.link,
                source: selectedSource,
            });

            // Show summary in toast or modal
            toast.success(
                <div>
                    <Text strong>Tóm tắt: {article.title}</Text>
                    <Text style={{ display: 'block', marginTop: 8 }}>
                        {data.summary}
                    </Text>
                </div>,
                { duration: 10000 }
            );
        } catch (error) {
            console.error("Failed to summarize:", error);
            toast.error(t('error.summarize_failed', 'Không thể tóm tắt bài viết'));
        }
    };

    return (
        <>
            <PageHead
                title={t('page.title', 'Tin tức')}
                description={t('page.description', 'Đọc tin tức mới nhất từ nhiều nguồn')}
            />

            <Card style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                    {/* Filters */}
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', flex: 1 }}>
                        <div style={{ minWidth: 150 }}>
                            <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>
                                {t('filter.source', 'Nguồn tin')}
                            </Text>
                            <Select
                                value={selectedSource}
                                onChange={(value) => setSelectedSource(value as string)}
                                style={{ width: '100%' }}
                            >
                                <Select.Option value="vnexpress">VnExpress</Select.Option>
                            </Select>
                        </div>

                        <div style={{ minWidth: 200, flex: 1 }}>
                            <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>
                                {t('filter.topic', 'Chủ đề')}
                            </Text>
                            <Select
                                value={selectedTopic}
                                onChange={(value) => setSelectedTopic(value as string)}
                                style={{ width: '100%' }}
                                filter
                                placeholder={t('filter.select_topic', 'Chọn chủ đề')}
                            >
                                {topics.map(topic => (
                                    <Select.Option key={topic.name} value={topic.name}>
                                        {topic.name}
                                    </Select.Option>
                                ))}
                            </Select>
                        </div>
                    </div>

                    {/* Actions */}
                    <div style={{ display: 'flex', gap: 8 }}>
                        <Button
                            icon={<IconRefresh />}
                            onClick={fetchNews}
                            loading={loading}
                        >
                            {t('action.refresh', 'Làm mới')}
                        </Button>
                    </div>
                </div>

                {selectedTopic && (
                    <div style={{
                        marginTop: 16,
                        padding: 12,
                        background: 'var(--semi-color-fill-0)',
                        borderRadius: 8,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8
                    }}>
                        <Newspaper size={18} />
                        <Text>
                            {t('info.viewing', 'Đang xem')}: <Text strong>{selectedTopic}</Text> • <Text type="tertiary">{articles.length} {t('info.articles', 'bài viết')}</Text>
                        </Text>
                    </div>
                )}
            </Card>

            {/* Articles Grid */}
            <Spin spinning={loading} tip={t('loading.fetching', 'Đang tải tin tức...')}>
                {articles.length === 0 && !loading ? (
                    <Card>
                        <Empty
                            title={t('empty.title', 'Chưa có tin tức')}
                            description={t('empty.description', 'Chọn chủ đề để xem tin tức')}
                            image={<Newspaper size={64} />}
                        />
                    </Card>
                ) : (
                    <Row gutter={[16, 16]}>
                        {articles.map((article) => (
                            <Col key={article.link} xs={24} sm={24} md={12} lg={8}>
                                <ArticleCard
                                    article={article}
                                    onRead={() => handleReadArticle(article)}
                                    onSummarize={() => handleSummarizeArticle(article)}
                                />
                            </Col>
                        ))}
                    </Row>
                )}
            </Spin>

            {/* Article Detail Drawer */}
            <ArticleDetailDrawer
                visible={drawerVisible}
                articleUrl={selectedArticle?.link || null}
                articleTitle={selectedArticle?.title || ''}
                source={selectedSource}
                onClose={() => setDrawerVisible(false)}
            />
        </>
    );
}

export default NewsPage;
