import { toast } from "sonner";
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Card,
  Empty,
  Input,
  Spin,
  Typography,
  Space,
  
  Popconfirm,
  Tag} from '@douyinfe/semi-ui';
import {
  IconPlus,
  IconSearch,
  IconDelete,
  IconStar,
  IconMusic,
} from '@douyinfe/semi-icons';
import apiClient from '@/config/axios-instance';
import VoiceUploadModal from '../components/voice/VoiceUploadModal';

const { Title, Text, Paragraph } = Typography;

interface Voice {
  id: string;
  name: string;
  description?: string;
  audio_duration: number;
  audio_size: number;
  sample_rate: number;
  is_default: boolean;
  created_at: string;
}

interface VoiceListResponse {
  items: Voice[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

const VoiceLibraryPage: React.FC = () => {
  const { t } = useTranslation('voice');
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [playingVoice, setPlayingVoice] = useState<string | null>(null);

  // Fetch voices
  const { data, isLoading, error } = useQuery<VoiceListResponse>({
    queryKey: ['voices', searchQuery],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append('page', '1');
      params.append('page_size', '100');
      if (searchQuery) {
        params.append('search', searchQuery);
      }
      const response = await apiClient.get(`/voices/?${params.toString()}`);
      return response.data;
    },
  });

  // Delete voice mutation
  const deleteMutation = useMutation({
    mutationFn: async (voiceId: string) => {
      await apiClient.delete(`/voices/${voiceId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voices'] });
      toast.success(t('deleteSuccess', { defaultValue: 'Voice deleted successfully' }));
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || t('deleteFailed', { defaultValue: 'Failed to delete voice' }));
    },
  });

  // Set default voice mutation
  const setDefaultMutation = useMutation({
    mutationFn: async (voiceId: string) => {
      await apiClient.patch(`/voices/${voiceId}/set-default`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['voices'] });
      toast.success(t('setDefaultSuccess', { defaultValue: 'Default voice set successfully' }));
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || t('setDefaultFailed', { defaultValue: 'Failed to set default voice' }));
    },
  });

  const handleDelete = (voiceId: string) => {
    deleteMutation.mutate(voiceId);
  };

  const handleSetDefault = (voiceId: string) => {
    setDefaultMutation.mutate(voiceId);
  };

  const handlePlayAudio = (voiceId: string) => {
    if (playingVoice === voiceId) {
      setPlayingVoice(null);
      return;
    }

    const audio = new Audio(`/api/v1/voices/${voiceId}/audio`);
    audio.play();
    setPlayingVoice(voiceId);

    audio.onended = () => {
      setPlayingVoice(null);
    };

    audio.onerror = () => {
      toast.error(t('playFailed', { defaultValue: 'Failed to play audio' }));
      setPlayingVoice(null);
    };
  };

  const formatDuration = (seconds: number) => {
    return `${seconds.toFixed(1)}s`;
  };

  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) {
      return `${mb.toFixed(2)} MB`;
    }
    const kb = bytes / 1024;
    return `${kb.toFixed(2)} KB`;
  };

  const voices = data?.items || [];
  const maxVoices = 10;
  const currentCount = data?.total || 0;

  return (
    <div style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title heading={2} style={{ marginBottom: '8px' }}>
            {t('title', { defaultValue: 'Voice Library' })}
          </Title>
          <Paragraph style={{ marginBottom: 0 }}>
            {t('description', { defaultValue: 'Manage your custom voices for AI agents' })}
          </Paragraph>
        </div>
        <Button
          icon={<IconPlus />}
          theme="solid"
          type="primary"
          onClick={() => setUploadModalVisible(true)}
          disabled={currentCount >= maxVoices}
        >
          {t('uploadVoice', { defaultValue: 'Upload Voice' })}
        </Button>
      </div>

      {/* Search and Stats */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Input
          prefix={<IconSearch />}
          placeholder={t('searchPlaceholder', { defaultValue: 'Search by voice name...' })}
          value={searchQuery}
          onChange={(value) => setSearchQuery(value)}
          style={{ width: '300px' }}
        />
        <Text type="tertiary">
          {t('voiceCount', { defaultValue: '{{current}} of {{max}} voices used', current: currentCount, max: maxVoices })}
        </Text>
      </div>

      {/* Voice Grid */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
        </div>
      ) : error ? (
        <Empty
          image={<IconMusic style={{ fontSize: 60 }} />}
          description={t('loadError', { defaultValue: 'Failed to load voices' })}
        />
      ) : voices.length === 0 ? (
        <Empty
          image={<IconMusic style={{ fontSize: 60 }} />}
          title={t('emptyTitle', { defaultValue: 'No voices yet' })}
          description={t('emptyDescription', { defaultValue: 'Upload your first voice to get started' })}
        >
          <Button
            icon={<IconPlus />}
            theme="solid"
            type="primary"
            onClick={() => setUploadModalVisible(true)}
          >
            {t('uploadFirstVoice', { defaultValue: 'Upload Your First Voice' })}
          </Button>
        </Empty>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
          {voices.map((voice) => (
            <Card
              key={voice.id}
              bodyStyle={{ padding: '16px' }}
              bordered
              style={{ position: 'relative', cursor: 'pointer' }}
            >
              {/* Default Badge */}
              {voice.is_default && (
                <div style={{ position: 'absolute', top: '12px', right: '12px' }}>
                  <Tag color="amber" size="small">
                    <IconStar style={{ marginRight: '4px' }} />
                    {t('default', { defaultValue: 'Default' })}
                  </Tag>
                </div>
              )}

              {/* Voice Icon */}
              <div style={{ textAlign: 'center', marginBottom: '12px', paddingTop: voice.is_default ? '20px' : '0' }}>
                <div
                  style={{
                    width: '60px',
                    height: '60px',
                    borderRadius: '50%',
                    background: 'var(--semi-color-primary-light-default)',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '28px',
                  }}
                >
                  🎤
                </div>
              </div>

              {/* Voice Info */}
              <div style={{ textAlign: 'center', marginBottom: '12px' }}>
                <Title heading={5} style={{ marginBottom: '4px', wordBreak: 'break-word' }}>
                  {voice.name}
                </Title>
                {voice.description && (
                  <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: '8px' }}>
                    {voice.description}
                  </Text>
                )}
                <Space spacing="tight">
                  <Text size="small" type="tertiary">
                    ⏱️ {formatDuration(voice.audio_duration)}
                  </Text>
                  <Text size="small" type="tertiary">
                    📦 {formatFileSize(voice.audio_size)}
                  </Text>
                </Space>
              </div>

              {/* Actions */}
              <Space style={{ width: '100%', marginTop: '12px' }} spacing="tight">
                <Button
                  size="small"
                  block
                  onClick={() => handlePlayAudio(voice.id)}
                  type={playingVoice === voice.id ? 'danger' : 'secondary'}
                >
                  {playingVoice === voice.id ? t('stop', { defaultValue: 'Stop' }) : t('play', { defaultValue: 'Play' })}
                </Button>
                {!voice.is_default && (
                  <Button
                    size="small"
                    icon={<IconStar />}
                    onClick={() => handleSetDefault(voice.id)}
                  />
                )}
                <Popconfirm
                  title={t('deleteConfirmTitle', { defaultValue: 'Delete voice?' })}
                  content={t('deleteConfirmContent', { defaultValue: 'This action cannot be undone.' })}
                  onConfirm={() => handleDelete(voice.id)}
                >
                  <Button
                    size="small"
                    icon={<IconDelete />}
                    type="danger"
                  />
                </Popconfirm>
              </Space>
            </Card>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      <VoiceUploadModal
        visible={uploadModalVisible}
        onClose={() => setUploadModalVisible(false)}
        onSuccess={() => {
          setUploadModalVisible(false);
          queryClient.invalidateQueries({ queryKey: ['voices'] });
        }}
      />
    </div>
  );
};

export default VoiceLibraryPage;
