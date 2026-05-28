/**
 * ProviderTestInput - Semi Design implementation
 */

import { memo, useState, useCallback, useRef, type ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { ChevronDown, ImagePlus, X, Info } from "lucide-react";

import type { ProviderCategory, ProviderTestInputData } from "@types";
import { AudioRecorder, type AudioRecorderData } from "./AudioRecorder";
import { Button, TextArea, Typography, Card } from "@douyinfe/semi-ui";

const { Text } = Typography;

export interface ProviderTestInputProps {
  category: ProviderCategory | null;
  onInputChange: (inputData: ProviderTestInputData | null) => void;
  disabled?: boolean;
  className?: string;
}

const CATEGORIES_WITH_INPUT: ProviderCategory[] = ["LLM", "TTS", "ASR", "VLLM"];

const ProviderTestInputComponent = ({
  category,
  onInputChange,
  disabled = false,
  className,
}: ProviderTestInputProps) => {
  const { t } = useTranslation(["providers", "common"]);

  const [isOpen, setIsOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [text, setText] = useState("");
  const [audioData, setAudioData] = useState<AudioRecorderData | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [question, setQuestion] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const buildInputData = useCallback((): ProviderTestInputData | null => {
    if (!category) return null;

    switch (category) {
      case "LLM":
        return prompt.trim() ? { prompt: prompt.trim() } : null;
      case "TTS":
        return text.trim() ? { text: text.trim() } : null;
      case "ASR":
        return audioData
          ? {
            audio_base64: audioData.audioBase64,
            audio_format: audioData.audioFormat,
          }
          : null;
      case "VLLM":
        if (imageBase64) {
          return {
            image_base64: imageBase64,
            question: question.trim() || undefined,
          };
        }
        return null;
      default:
        return null;
    }
  }, [category, prompt, text, audioData, imageBase64, question]);

  const handlePromptChange = useCallback(
    (value: string) => {
      setPrompt(value);
      onInputChange(value.trim() ? { prompt: value.trim() } : null);
    },
    [onInputChange]
  );

  const handleTextChange = useCallback(
    (value: string) => {
      setText(value);
      onInputChange(value.trim() ? { text: value.trim() } : null);
    },
    [onInputChange]
  );

  const handleRecordingComplete = useCallback(
    (data: AudioRecorderData) => {
      setAudioData(data);
      onInputChange({
        audio_base64: data.audioBase64,
        audio_format: data.audioFormat,
      });
    },
    [onInputChange]
  );

  const handleRecordingClear = useCallback(() => {
    setAudioData(null);
    onInputChange(null);
  }, [onInputChange]);

  const handleImageUpload = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (!file.type.startsWith("image/")) {
        return;
      }

      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result as string;
        const base64Data = base64.split(",")[1];
        setImageBase64(base64Data);
        setImagePreview(base64);
        onInputChange({
          image_base64: base64Data,
          question: question.trim() || undefined,
        });
      };
      reader.readAsDataURL(file);
    },
    [question, onInputChange]
  );

  const handleImageRemove = useCallback(() => {
    setImageBase64(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onInputChange(null);
  }, [onInputChange]);

  const handleQuestionChange = useCallback(
    (value: string) => {
      setQuestion(value);
      if (imageBase64) {
        onInputChange({
          image_base64: imageBase64,
          question: value.trim() || undefined,
        });
      }
    },
    [imageBase64, onInputChange]
  );

  const hasCustomInput = category && CATEGORIES_WITH_INPUT.includes(category);
  const currentInputData = buildInputData();
  const hasInputValue = currentInputData !== null;

  return (
    <div className={`space-y-2 ${className || ""}`}>
      <Button
        theme="borderless"
        type="tertiary"
        block
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="!justify-between"
      >
        <span className="flex items-center gap-2 text-sm font-medium">
          {t("providers:advanced_test_options")}
          {hasInputValue && (
            <span className="h-2 w-2 rounded-full bg-blue-500" />
          )}
        </span>
        <ChevronDown
          className={`h-4 w-4 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
        />
      </Button>

      {isOpen && (
        <div className="space-y-4 pt-2">
          {!hasCustomInput ? (
            <Card className="!bg-gray-50 dark:!bg-gray-800" bodyStyle={{ padding: 12 }}>
              <div className="flex items-center gap-2">
                <Info className="h-4 w-4 text-gray-400" />
                <Text type="tertiary">{t("providers:no_custom_input_needed")}</Text>
              </div>
            </Card>
          ) : (
            <>
              {/* LLM: Prompt Input */}
              {category === "LLM" && (
                <div className="space-y-2">
                  <Text strong size="small">{t("providers:test_prompt")}</Text>
                  <TextArea
                    placeholder={t("providers:test_prompt_placeholder")}
                    value={prompt}
                    onChange={handlePromptChange}
                    disabled={disabled}
                    rows={3}
                    autosize={false}
                  />
                </div>
              )}

              {/* TTS: Text Input */}
              {category === "TTS" && (
                <div className="space-y-2">
                  <Text strong size="small">{t("providers:test_text")}</Text>
                  <TextArea
                    placeholder={t("providers:test_text_placeholder")}
                    value={text}
                    onChange={handleTextChange}
                    disabled={disabled}
                    rows={3}
                    autosize={false}
                  />
                </div>
              )}

              {/* ASR: Audio Recording */}
              {category === "ASR" && (
                <div className="space-y-2">
                  <Text strong size="small">{t("providers:test_audio")}</Text>
                  <AudioRecorder
                    onRecordingComplete={handleRecordingComplete}
                    onRecordingClear={handleRecordingClear}
                    disabled={disabled}
                  />
                </div>
              )}

              {/* VLLM: Image + Question */}
              {category === "VLLM" && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Text strong size="small">{t("providers:test_image")}</Text>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleImageUpload}
                      disabled={disabled}
                      className="hidden"
                    />
                    {imagePreview ? (
                      <div className="relative inline-block">
                        <img
                          src={imagePreview}
                          alt="Preview"
                          className="max-h-32 rounded-md border"
                        />
                        <Button
                          type="danger"
                          theme="solid"
                          size="small"
                          icon={<X className="h-3 w-3" />}
                          className="absolute -top-2 -right-2 !rounded-full !p-1"
                          onClick={handleImageRemove}
                          disabled={disabled}
                        />
                      </div>
                    ) : (
                      <Button
                        icon={<ImagePlus className="h-4 w-4" />}
                        onClick={() => fileInputRef.current?.click()}
                        disabled={disabled}
                      >
                        {t("providers:upload_image")}
                      </Button>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Text strong size="small">{t("providers:test_question")}</Text>
                    <TextArea
                      placeholder={t("providers:test_question_placeholder")}
                      value={question}
                      onChange={handleQuestionChange}
                      disabled={disabled}
                      rows={2}
                      autosize={false}
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export const ProviderTestInput = memo(ProviderTestInputComponent);
