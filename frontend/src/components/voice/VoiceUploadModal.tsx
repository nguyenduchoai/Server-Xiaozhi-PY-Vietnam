import { toast } from "sonner";
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import {
  Modal,
  Form,
  Button,
  
  Upload,
  Typography} from '@douyinfe/semi-ui';
import { IconUpload } from '@douyinfe/semi-icons';
import apiClient from '@/config/axios-instance';

const { Text } = Typography;

interface VoiceUploadModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const VoiceUploadModal: React.FC<VoiceUploadModalProps> = ({
  visible,
  onClose,
  onSuccess,
}) => {
  const { t } = useTranslation('voice');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [setAsDefault, setSetAsDefault] = useState(false);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!audioFile || !name) {
        throw new Error('Missing required fields');
      }

      const formData = new FormData();
      formData.append('file', audioFile);
      formData.append('name', name);
      formData.append('description', description || '');
      formData.append('set_as_default', String(setAsDefault));

      const response = await apiClient.post('/voices/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    },
    onSuccess: () => {
      toast.success(t('uploadSuccess', { defaultValue: 'Voice cloned successfully!' }));
      handleReset();
      onSuccess();
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || t('uploadFailed', { defaultValue: 'Voice upload failed' });
      toast.error(message);
    },
  });

  const handleReset = () => {
    setName('');
    setDescription('');
    setSetAsDefault(false);
    setAudioFile(null);
    setUploading(false);
  };

  const handleClose = () => {
    if (!uploading) {
      handleReset();
      onClose();
    }
  };

  const handleUpload = async () => {
    if (!audioFile) {
      toast.warning(t('selectAudioFile', { defaultValue: 'Please select an audio file' }));
      return;
    }

    if (!name.trim()) {
      toast.warning(t('enterVoiceName', { defaultValue: 'Please enter a voice name' }));
      return;
    }

    setUploading(true);
    try {
      await uploadMutation.mutateAsync();
    } finally {
      setUploading(false);
    }
  };

  const validateFile = (file: File) => {
    // Check file type
    const allowedTypes = ['audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/x-m4a', 'audio/m4a'];
    if (!allowedTypes.includes(file.type) && !file.name.match(/\.(wav|mp3|m4a)$/i)) {
      toast.error(t('invalidFileType', { defaultValue: 'Invalid file type. Please upload WAV, MP3, or M4A file.' }));
      return false;
    }

    // Check file size (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      toast.error(t('fileTooLarge', { defaultValue: 'File too large. Maximum size is 10MB.' }));
      return false;
    }

    return true;
  };

  return (
    <Modal
      title={t('uploadVoiceTitle', { defaultValue: 'Upload & Clone Voice' })}
      visible={visible}
      onCancel={handleClose}
      footer={null}
      width={500}
      closable={!uploading}
      maskClosable={!uploading}
    >
      <Form layout="vertical">
        {/* Audio File Upload */}
        <Form.Section text={t('audioFileSection', { defaultValue: 'Audio Sample' })}>
          <Upload
            action=""
            accept=".wav,.mp3,.m4a"
            limit={1}
            maxSize={10 * 1024}
            beforeUpload={(file) => {
              const fileObj = (file as any).fileInstance || file;
              if (validateFile(fileObj as File)) {
                setAudioFile(fileObj as File);
              }
              return false; // Prevent auto upload
            }}
            onRemove={() => setAudioFile(null)}
            disabled={uploading}
          >
            <Button icon={<IconUpload />} theme="light" disabled={uploading}>
              {t('selectAudioFile', { defaultValue: 'Select Audio File' })}
            </Button>
          </Upload>
          <Text size="small" type="tertiary" style={{ display: 'block', marginTop: '8px' }}>
            {t('audioFileHint', { 
              defaultValue: 'WAV, MP3, or M4A format • 3-30 seconds • Max 10MB' 
            })}
          </Text>
          <Text size="small" type="warning" style={{ display: 'block', marginTop: '4px' }}>
            {t('audioQualityTip', { 
              defaultValue: '💡 Tip: Use 10-15 seconds of clear speech for best results' 
            })}
          </Text>
        </Form.Section>

        {/* Voice Name */}
        <Form.Input
          field="name"
          label={t('voiceName', { defaultValue: 'Voice Name' })}
          placeholder={t('voiceNamePlaceholder', { defaultValue: 'e.g., Mom\'s Voice, Professional Voice' })}
          onChange={(value) => setName(value)}
          required
          disabled={uploading}
          maxLength={255}
        />

        {/* Description */}
        <Form.TextArea
          field="description"
          label={t('description', { defaultValue: 'Description (Optional)' })}
          placeholder={t('descriptionPlaceholder', { defaultValue: 'Add notes about this voice...' })}
          onChange={(value) => setDescription(value)}
          disabled={uploading}
          maxLength={500}
          rows={3}
        />

        {/* Set as Default */}
        <Form.Checkbox
          field="setAsDefault"
          onChange={(e) => setSetAsDefault(e?.target?.checked || false)}
          disabled={uploading}
        >
          {t('setAsDefault', { defaultValue: 'Set as my default voice' })}
        </Form.Checkbox>

        {/* Actions */}
        <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
          <Button onClick={handleClose} disabled={uploading}>
            {t('cancel', { defaultValue: 'Cancel' })}
          </Button>
          <Button
            theme="solid"
            type="primary"
            onClick={handleUpload}
            loading={uploading}
            disabled={!audioFile || !name.trim()}
          >
            {t('uploadAndClone', { defaultValue: 'Upload & Clone Voice' })}
          </Button>
        </div>
      </Form>
    </Modal>
  );
};

export default VoiceUploadModal;
