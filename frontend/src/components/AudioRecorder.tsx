/**
 * AudioRecorder - Semi Design implementation
 */

import { memo, useState, useRef, useCallback, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Mic, Square, RotateCcw } from "lucide-react";

import { Button, Banner, Progress, Typography } from "@douyinfe/semi-ui";
import { IconAlertCircle } from "@douyinfe/semi-icons";

const { Text } = Typography;

const MAX_RECORDING_DURATION = 20;

export interface AudioRecorderData {
  audioBase64: string;
  audioFormat: string;
}

export interface AudioRecorderProps {
  onRecordingComplete: (data: AudioRecorderData) => void;
  onRecordingClear?: () => void;
  disabled?: boolean;
  className?: string;
}

type RecordingState = "idle" | "recording" | "recorded" | "error";

const AudioRecorderComponent = ({
  onRecordingComplete,
  onRecordingClear,
  disabled = false,
  className,
}: AudioRecorderProps) => {
  const { t } = useTranslation(["providers", "common"]);

  const [recordingState, setRecordingState] = useState<RecordingState>("idle");
  const [elapsedTime, setElapsedTime] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
  }, [audioUrl]);

  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  const blobToBase64 = useCallback((blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result as string;
        const base64Data = base64.split(",")[1];
        resolve(base64Data);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }, []);

  const getAudioFormat = useCallback((mimeType: string): string => {
    if (mimeType.includes("webm")) return "webm";
    if (mimeType.includes("ogg")) return "ogg";
    if (mimeType.includes("mp4")) return "mp4";
    if (mimeType.includes("wav")) return "wav";
    return "webm";
  }, []);

  const startRecording = useCallback(async () => {
    try {
      setErrorMessage(null);
      audioChunksRef.current = [];

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setErrorMessage(t("providers:audio_not_supported"));
        setRecordingState("error");
        return;
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/ogg")
          ? "audio/ogg"
          : "audio/mp4";

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);

        try {
          const base64 = await blobToBase64(audioBlob);
          const format = getAudioFormat(mimeType);
          onRecordingComplete({ audioBase64: base64, audioFormat: format });
          setRecordingState("recorded");
        } catch {
          setErrorMessage(t("providers:audio_conversion_error"));
          setRecordingState("error");
        }
      };

      mediaRecorder.start(100);
      setRecordingState("recording");
      setElapsedTime(0);

      timerRef.current = setInterval(() => {
        setElapsedTime((prev) => {
          const next = prev + 1;
          if (next >= MAX_RECORDING_DURATION) {
            stopRecording();
          }
          return next;
        });
      }, 1000);
    } catch (error) {
      if (error instanceof DOMException && error.name === "NotAllowedError") {
        setErrorMessage(t("providers:microphone_permission_denied"));
      } else {
        setErrorMessage(t("providers:audio_recording_error"));
      }
      setRecordingState("error");
    }
  }, [t, blobToBase64, getAudioFormat, onRecordingComplete]);

  const stopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
  }, []);

  const resetRecording = useCallback(() => {
    cleanup();
    setRecordingState("idle");
    setElapsedTime(0);
    setAudioUrl(null);
    setErrorMessage(null);
    audioChunksRef.current = [];
    onRecordingClear?.();
  }, [cleanup, onRecordingClear]);

  const formatTime = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }, []);

  const progressPercent = (elapsedTime / MAX_RECORDING_DURATION) * 100;

  return (
    <div className={`space-y-3 ${className || ""}`}>
      {/* Error Alert */}
      {recordingState === "error" && errorMessage && (
        <Banner
          type="danger"
          icon={<IconAlertCircle />}
          description={errorMessage}
          closeIcon={null}
        />
      )}

      {/* Recording Controls */}
      <div className="flex items-center gap-3">
        {recordingState === "idle" || recordingState === "error" ? (
          <Button
            theme="light"
            icon={<Mic className="h-4 w-4" />}
            onClick={startRecording}
            disabled={disabled}
          >
            {t("providers:start_recording")}
          </Button>
        ) : recordingState === "recording" ? (
          <>
            <Button
              type="danger"
              theme="solid"
              icon={<Square className="h-4 w-4" />}
              onClick={stopRecording}
            >
              {t("providers:stop_recording")}
            </Button>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-red-500 animate-pulse" />
              <Text className="font-mono">{formatTime(elapsedTime)}</Text>
              <Text type="tertiary" size="small">
                / {formatTime(MAX_RECORDING_DURATION)}
              </Text>
            </div>
          </>
        ) : (
          <Button
            theme="light"
            icon={<RotateCcw className="h-4 w-4" />}
            onClick={resetRecording}
            disabled={disabled}
          >
            {t("providers:re_record")}
          </Button>
        )}
      </div>

      {/* Progress Bar */}
      {recordingState === "recording" && (
        <Progress
          percent={progressPercent}
          showInfo={false}
          stroke="var(--semi-color-danger)"
          size="small"
        />
      )}

      {/* Audio Preview */}
      {recordingState === "recorded" && audioUrl && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Text type="tertiary" size="small">
              {t("providers:audio_preview")}
            </Text>
            <Text type="tertiary" size="small" className="font-mono">
              {formatTime(elapsedTime)}
            </Text>
          </div>
          <audio src={audioUrl} controls className="w-full h-8" />
        </div>
      )}
    </div>
  );
};

export const AudioRecorder = memo(AudioRecorderComponent);
