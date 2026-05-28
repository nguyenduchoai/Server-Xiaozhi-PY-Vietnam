/**
 * Knowledge Base Selector for Agents
 * 
 * Multi-select component for linking knowledge bases to an agent.
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, Select, Typography, Toast, Tag, Empty } from '@douyinfe/semi-ui';
import { IconBox, IconLink } from '@douyinfe/semi-icons';
import { useKnowledgeBases, useAgentKnowledgeBases, useUpdateAgentKnowledgeBases } from '@/queries/knowledge-bases-queries';

const { Title, Text } = Typography;

interface AgentKnowledgeBaseSelectorProps {
    agentId: string;
}

export function AgentKnowledgeBaseSelector({ agentId }: AgentKnowledgeBaseSelectorProps) {
    const { t } = useTranslation();

    // Fetch all available knowledge bases
    const { data: allKbs, isLoading: kbsLoading } = useKnowledgeBases({});
    // Fetch currently linked KBs for this agent
    const { data: linkedKbs, isLoading: linkedLoading } = useAgentKnowledgeBases(agentId);
    // Mutation for updating links
    const updateMutation = useUpdateAgentKnowledgeBases(agentId);

    const [selectedIds, setSelectedIds] = useState<string[]>([]);

    // Initialize selected from linked KBs
    useEffect(() => {
        if (linkedKbs) {
            setSelectedIds(linkedKbs.map(kb => kb.id));
        }
    }, [linkedKbs]);

    const handleChange = async (values: string | number | (string | number)[] | Record<string, unknown> | undefined) => {
        const newIds = (values as string[]) || [];
        setSelectedIds(newIds);

        try {
            await updateMutation.mutateAsync(newIds);
            Toast.success(t('knowledge:kb_linked_success', 'Đã cập nhật kho tri thức'));
        } catch (error) {
            // Revert on error
            if (linkedKbs) {
                setSelectedIds(linkedKbs.map(kb => kb.id));
            }
            Toast.error(t('knowledge:kb_link_error', 'Không thể cập nhật kho tri thức'));
        }
    };

    const isLoading = kbsLoading || linkedLoading;
    const hasKbs = allKbs?.items && allKbs.items.length > 0;

    return (
        <Card
            title={
                <div className="flex items-center gap-2">
                    <IconBox size="large" />
                    <Title heading={5} style={{ margin: 0 }}>
                        {t('knowledge:linked_kbs', 'Kho Tri Thức Liên Kết')}
                    </Title>
                    <Tag color="blue">{selectedIds.length}</Tag>
                </div>
            }
        >
            {!hasKbs ? (
                <Empty
                    title={t('knowledge:no_kbs', 'Chưa có kho tri thức')}
                    description={t(
                        'knowledge:create_kb_first',
                        'Tạo kho tri thức từ menu "Kho Tri Thức" để liên kết với Agent'
                    )}
                />
            ) : (
                <>
                    <Text type="tertiary" className="block mb-3">
                        {t(
                            'knowledge:select_kbs_desc',
                            'Chọn các kho tri thức để Agent có thể truy vấn và sử dụng'
                        )}
                    </Text>

                    <Select
                        multiple
                        filter
                        style={{ width: '100%' }}
                        placeholder={t('knowledge:select_kbs_placeholder', 'Chọn kho tri thức...')}
                        loading={isLoading}
                        value={selectedIds}
                        onChange={handleChange}
                        prefix={<IconLink />}
                        showClear
                        maxTagCount={5}
                    >
                        {allKbs?.items.map((kb) => (
                            <Select.Option key={kb.id} value={kb.id}>
                                <div className="flex justify-between items-center w-full">
                                    <span>{kb.name}</span>
                                    <span className="text-gray-400 text-xs">
                                        {kb.entry_count} entries
                                    </span>
                                </div>
                            </Select.Option>
                        ))}
                    </Select>

                    {selectedIds.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                            {selectedIds.map((id) => {
                                const kb = allKbs?.items.find(k => k.id === id);
                                return kb ? (
                                    <Tag key={id} color="blue" size="large">
                                        {kb.name}
                                    </Tag>
                                ) : null;
                            })}
                        </div>
                    )}
                </>
            )}
        </Card>
    );
}

export default AgentKnowledgeBaseSelector;
