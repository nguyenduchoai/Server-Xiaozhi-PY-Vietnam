import React from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Select, Spin } from '@douyinfe/semi-ui';
import { IconStar, IconMusic } from '@douyinfe/semi-icons';
import apiClient from '@/config/axios-instance';

interface Voice {
  id: string;
  name: string;
  is_default: boolean;
  audio_duration: number;
}

interface AgentVoiceSelectorProps {
  value?: string | null;
  onChange?: (value: string | null) => void;
  disabled?: boolean;
  placeholder?: string;
}

const AgentVoiceSelector: React.FC<AgentVoiceSelectorProps> = ({
  value,
  onChange,
  disabled = false,
  placeholder,
}) => {
  const { t } = useTranslation('voice');

  const { data: voices, isLoading } = useQuery<Voice[]>({
    queryKey: ['voices', 'selector'],
    queryFn: async () => {
      const response = await apiClient.get('/voices/?page=1&page_size=100');
      return response.data.items;
    },
  });

  const handleChange = (selectedValue: any) => {
    if (onChange && typeof selectedValue === 'string') {
      // Empty string means "None"
      onChange(selectedValue === '' ? null : selectedValue);
    }
  };

  if (isLoading) {
    return <Spin size="small" />;
  }

  return (
    <Select
      value={value || ''}
      onChange={handleChange}
      disabled={disabled}
      placeholder={placeholder || t('selectVoice', { defaultValue: 'Select custom voice (optional)' })}
      style={{ width: '100%' }}
      showClear
      filter
    >
      <Select.Option value="">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <IconMusic />
          <span>{t('noCustomVoice', { defaultValue: 'None (use default TTS)' })}</span>
        </div>
      </Select.Option>
      {voices?.map((voice) => (
        <Select.Option key={voice.id} value={voice.id}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {voice.is_default && <IconStar style={{ color: 'var(--semi-color-warning)' }} />}
            <span>{voice.name}</span>
            <span style={{ color: 'var(--semi-color-text-2)', fontSize: '12px' }}>
              ({voice.audio_duration.toFixed(1)}s)
            </span>
          </div>
        </Select.Option>
      ))}
    </Select>
  );
};

export default AgentVoiceSelector;
