// @ts-nocheck
/**
 * Device Control Panel - Remote control device via MQTT
 * 
 * Features:
 * - Radio control (play/stop/switch stations)
 * - Agent template switching
 * - TTS speak command
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
    Card,
    Button,
    Select,
    Input,
    Toast,
    Typography,
    Space,
    Divider,
    Tag,
} from '@douyinfe/semi-ui';
import {
    IconPlay,
    IconPause,
    IconChevronRight,
    IconChevronLeft,
    IconVolume2,
    IconRefresh,
    IconSend,
    IconUser,
    IconPhone,
} from '@douyinfe/semi-icons';

// Custom microphone icon since Semi doesn't have one
const IconMicrophone = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
    </svg>
);

import { deviceControlApi } from '../services/deviceControlApi';

const { Title, Text } = Typography;

// Radio stations (can be fetched from OTA config later)
const RADIO_STATIONS = [
    { value: 'vov1', label: 'VOV1 - Thời sự' },
    { value: 'vov2', label: 'VOV2 - Văn hóa' },
    { value: 'vov3', label: 'VOV3 - Âm nhạc' },
    { value: 'vovgt', label: 'VOV Giao thông' },
    { value: 'vov5', label: 'VOV5 - Dân tộc' },
];

export interface DeviceControlPanelProps {
    deviceId: string;
    deviceName?: string;
    deviceStatus?: 'online' | 'offline';
    templates?: Array<{ id: string; name: string }>;
    currentTemplateId?: string;
    onTemplateChange?: (templateId: string) => void;
}

export function DeviceControlPanel({
    deviceId,
    deviceStatus = 'offline',
    templates = [],
    currentTemplateId,
    onTemplateChange,
}: DeviceControlPanelProps) {
    const { t } = useTranslation('devices');

    // Radio state
    const [selectedStation, setSelectedStation] = useState<string>('vov1');
    const [isRadioLoading, setIsRadioLoading] = useState(false);
    const [radioPlaying, setRadioPlaying] = useState(false);

    // Agent state
    const [selectedTemplate, setSelectedTemplate] = useState<string | undefined>(currentTemplateId);
    const [isAgentLoading, setIsAgentLoading] = useState(false);

    // TTS state
    const [ttsText, setTtsText] = useState('');
    const [isTtsLoading, setIsTtsLoading] = useState(false);

    // Intercom state
    const [intercomTargets, setIntercomTargets] = useState<Array<{
        id: string;
        name: string;
        mac_address: string;
        type: 'own' | 'friend';
        friend_name?: string;
    }>>([]);
    const [selectedTargetDevice, setSelectedTargetDevice] = useState<string | undefined>();
    const [intercomMessage, setIntercomMessage] = useState('');
    const [isIntercomLoading, setIsIntercomLoading] = useState(false);

    // Voice recording state
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const [isProcessingAudio, setIsProcessingAudio] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const audioChunksRef = useRef<Blob[]>([]);
    const recordingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Load intercom targets (own devices + friends' devices)
    useEffect(() => {
        const loadTargets = async () => {
            try {
                const targets = await deviceControlApi.getIntercomTargets();
                // Filter out current device
                setIntercomTargets(targets.filter(d => d.id !== deviceId));
            } catch (error) {
                console.error('Failed to load intercom targets:', error);
            }
        };
        loadTargets();
    }, [deviceId]);

    // Radio controls
    const handleRadioPlay = useCallback(async () => {
        if (!selectedStation) {
            Toast.warning(t('select_station', 'Chọn đài phát thanh'));
            return;
        }

        setIsRadioLoading(true);
        try {
            await deviceControlApi.controlRadio(deviceId, {
                action: 'play',
                station_id: selectedStation,
            });
            setRadioPlaying(true);
            Toast.success(t('radio_started', 'Đã bật radio'));
        } catch (error) {
            Toast.error((error as Error).message || t('radio_error', 'Lỗi điều khiển radio'));
        } finally {
            setIsRadioLoading(false);
        }
    }, [deviceId, selectedStation, t]);

    const handleRadioStop = useCallback(async () => {
        setIsRadioLoading(true);
        try {
            await deviceControlApi.controlRadio(deviceId, { action: 'stop' });
            setRadioPlaying(false);
            Toast.success(t('radio_stopped', 'Đã tắt radio'));
        } catch (error) {
            Toast.error((error as Error).message || t('radio_error', 'Lỗi điều khiển radio'));
        } finally {
            setIsRadioLoading(false);
        }
    }, [deviceId, t]);

    const handleRadioNext = useCallback(async () => {
        setIsRadioLoading(true);
        try {
            await deviceControlApi.controlRadio(deviceId, { action: 'next' });
            Toast.success(t('station_next', 'Đã chuyển đài'));
        } catch (error) {
            Toast.error((error as Error).message);
        } finally {
            setIsRadioLoading(false);
        }
    }, [deviceId, t]);

    const handleRadioPrev = useCallback(async () => {
        setIsRadioLoading(true);
        try {
            await deviceControlApi.controlRadio(deviceId, { action: 'prev' });
            Toast.success(t('station_prev', 'Đã chuyển đài'));
        } catch (error) {
            Toast.error((error as Error).message);
        } finally {
            setIsRadioLoading(false);
        }
    }, [deviceId, t]);

    // Agent switch
    const handleAgentSwitch = useCallback(async () => {
        if (!selectedTemplate) {
            Toast.warning(t('select_template', 'Chọn cấu hình AI'));
            return;
        }

        setIsAgentLoading(true);
        try {
            await deviceControlApi.switchAgent(deviceId, {
                action: 'switch',
                template_id: selectedTemplate,
            });
            onTemplateChange?.(selectedTemplate);
            Toast.success(t('agent_switched', 'Đã chuyển cấu hình AI'));
        } catch (error) {
            Toast.error((error as Error).message || t('agent_error', 'Lỗi chuyển cấu hình'));
        } finally {
            setIsAgentLoading(false);
        }
    }, [deviceId, selectedTemplate, onTemplateChange, t]);

    const handleAgentReload = useCallback(async () => {
        setIsAgentLoading(true);
        try {
            await deviceControlApi.switchAgent(deviceId, { action: 'reload' });
            Toast.success(t('config_reloaded', 'Đã tải lại cấu hình'));
        } catch (error) {
            Toast.error((error as Error).message);
        } finally {
            setIsAgentLoading(false);
        }
    }, [deviceId, t]);

    // TTS speak
    const handleTtsSpeak = useCallback(async () => {
        if (!ttsText.trim()) {
            Toast.warning(t('enter_text', 'Nhập nội dung cần nói'));
            return;
        }

        setIsTtsLoading(true);
        try {
            await deviceControlApi.speakText(deviceId, { text: ttsText });
            Toast.success(t('tts_sent', 'Đã gửi lệnh nói'));
            setTtsText('');
        } catch (error) {
            Toast.error((error as Error).message || t('tts_error', 'Lỗi TTS'));
        } finally {
            setIsTtsLoading(false);
        }
    }, [deviceId, ttsText, t]);

    // Intercom send
    const handleIntercomSend = useCallback(async () => {
        if (!selectedTargetDevice) {
            Toast.warning('Chọn thiết bị để gọi');
            return;
        }
        if (!intercomMessage.trim()) {
            Toast.warning('Nhập tin nhắn');
            return;
        }

        setIsIntercomLoading(true);
        try {
            await deviceControlApi.sendIntercom(deviceId, selectedTargetDevice, intercomMessage);
            Toast.success('Đã gửi tin nhắn Intercom!');
            setIntercomMessage('');
        } catch (error) {
            Toast.error((error as Error).message || 'Lỗi gửi Intercom');
        } finally {
            setIsIntercomLoading(false);
        }
    }, [deviceId, selectedTargetDevice, intercomMessage]);

    // Voice recording handlers
    const startRecording = useCallback(async () => {
        if (!selectedTargetDevice) {
            Toast.warning('Chọn thiết bị để gọi trước khi ghi âm');
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            mediaRecorderRef.current = mediaRecorder;
            audioChunksRef.current = [];

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                // Stop stream
                stream.getTracks().forEach(track => track.stop());

                // Process audio
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
                await processAudio(audioBlob);
            };

            mediaRecorder.start(100); // Collect data every 100ms
            setIsRecording(true);
            setRecordingTime(0);

            // Start timer
            recordingIntervalRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);

            Toast.info('🎙️ Đang ghi âm... Nhấn lại để dừng');
        } catch (error) {
            console.error('Microphone access error:', error);
            Toast.error('Không thể truy cập microphone. Vui lòng cấp quyền.');
        }
    }, [selectedTargetDevice]);

    const stopRecording = useCallback(() => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);

            if (recordingIntervalRef.current) {
                clearInterval(recordingIntervalRef.current);
                recordingIntervalRef.current = null;
            }
        }
    }, [isRecording]);

    const processAudio = useCallback(async (audioBlob: Blob) => {
        if (!selectedTargetDevice) return;

        setIsProcessingAudio(true);
        try {
            // Create FormData to send audio
            const formData = new FormData();
            formData.append('audio', audioBlob, 'voice_message.webm');
            formData.append('target_device_id', selectedTargetDevice);

            // Send to backend for processing
            const result = await deviceControlApi.sendVoiceIntercom(deviceId, formData);

            Toast.success(`📢 Đã gửi: "${result.transcription || 'Voice message'}"`);
        } catch (error) {
            Toast.error((error as Error).message || 'Lỗi gửi voice intercom');
        } finally {
            setIsProcessingAudio(false);
        }
    }, [deviceId, selectedTargetDevice]);

    const handleRecordToggle = useCallback(() => {
        if (isRecording) {
            stopRecording();
        } else {
            startRecording();
        }
    }, [isRecording, startRecording, stopRecording]);

    const isOffline = deviceStatus === 'offline';

    return (
        <Card
            title={
                <div className="flex items-center gap-2">
                    <Title heading={5} className="!mb-0">
                        {t('remote_control', 'Điều khiển từ xa')}
                    </Title>
                    <Tag color={isOffline ? 'grey' : 'green'} size="small">
                        {isOffline ? 'Offline' : 'Online'}
                    </Tag>
                </div>
            }
            className="device-control-panel"
        >
            {isOffline && (
                <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                    <Text type="warning">
                        ⚠️ {t('device_offline_warning', 'Thiết bị đang offline. Lệnh sẽ được gửi khi thiết bị online.')}
                    </Text>
                </div>
            )}

            {/* Agent Switch Section */}
            <div className="mb-6">
                <Title heading={6} className="!mb-3 flex items-center gap-2">
                    <IconUser /> {t('agent_control', 'Chuyển cấu hình AI')}
                </Title>

                <div className="flex flex-wrap items-center gap-3">
                    <Select
                        value={selectedTemplate}
                        onChange={(value) => setSelectedTemplate(value as string)}
                        style={{ width: 250 }}
                        placeholder={t('select_template', 'Chọn cấu hình')}
                        optionList={templates.map(t => ({ value: t.id, label: t.name }))}
                        disabled={isAgentLoading || templates.length === 0}
                        showClear
                    />

                    <Space>
                        <Button
                            theme="solid"
                            type="primary"
                            onClick={handleAgentSwitch}
                            loading={isAgentLoading}
                            disabled={isAgentLoading || !selectedTemplate}
                        >
                            {t('switch', 'Chuyển')}
                        </Button>

                        <Button
                            icon={<IconRefresh />}
                            onClick={handleAgentReload}
                            loading={isAgentLoading}
                            disabled={isAgentLoading}
                        >
                            {t('reload', 'Tải lại')}
                        </Button>
                    </Space>
                </div>

                {templates.length === 0 && (
                    <Text type="tertiary" size="small" className="mt-2 block">
                        {t('no_templates', 'Chưa có cấu hình AI nào được tạo')}
                    </Text>
                )}
            </div>
        </Card>
    );
}

export default DeviceControlPanel;
