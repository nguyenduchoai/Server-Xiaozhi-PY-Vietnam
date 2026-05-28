/**
 * ProviderConfigForm - Semi Design implementation
 */

import { useTranslation } from "react-i18next";

import type { ProviderField } from "@types";
import { useProviderSheetStore } from "@/store/provider-sheet.store";
import { ProviderTestInput } from "@/components/ProviderTestInput";
import { ProviderToolSelector } from "./ProviderToolSelector";
import { ProviderRefSelector } from "./ProviderRefSelector";
import { ProviderTestResults } from "./ProviderTestResults";
import { AudioFileUpload } from "./AudioFileUpload";
import { DynamicSelectField } from "./DynamicSelectField";
import { Input, TextArea, Select, Checkbox, Typography } from "@douyinfe/semi-ui";

const { Text } = Typography;

interface ProviderConfigFormProps {
  selectedFields: ProviderField[];
  isEditDisabled?: boolean;
}

export function ProviderConfigForm({
  selectedFields,
  isEditDisabled = false,
}: ProviderConfigFormProps) {
  const { t } = useTranslation(["providers", "common"]);
  const {
    selectedCategory,
    formValues,
    errors,
    setFieldValue,
    setTestInputData,
  } = useProviderSheetStore();

  const hasFunctionsField =
    selectedCategory === "Intent" &&
    selectedFields.some((field) => field.name === "functions");

  const llmProviderField =
    selectedCategory === "Intent"
      ? selectedFields.find(
        (field) =>
          field.name === "llm_provider" ||
          field.name.toLowerCase().includes("llm") ||
          field.label?.toLowerCase().includes("llm provider")
      )
      : undefined;

  const memoryLlmField =
    selectedCategory === "Memory"
      ? selectedFields.find((field) => field.name === "llm")
      : undefined;

  const filteredFields = selectedFields.filter((field) => {
    if (hasFunctionsField && field.name === "functions") return false;
    if (llmProviderField && field.name === llmProviderField.name) return false;
    if (memoryLlmField && field.name === memoryLlmField.name) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      {/* Provider Name */}
      <div className="space-y-2">
        <Text strong size="small">{t("providers:name")}</Text>
        <Input
          placeholder={t("providers:name_placeholder")}
          disabled={isEditDisabled}
          value={String(formValues.name ?? "")}
          onChange={(value) => setFieldValue("name", value)}
        />
        {errors.name && <Text type="danger" size="small">{errors.name}</Text>}
      </div>

      {/* Dynamic Fields */}
      {filteredFields.map((field) => renderField(field, isEditDisabled))}

      {/* Tool Selector for Intent category with functions field */}
      {hasFunctionsField && <ProviderToolSelector disabled={isEditDisabled} />}

      {/* LLM Provider Selector for Intent category with llm_provider field */}
      {llmProviderField && (
        <ProviderRefSelector
          field={llmProviderField}
          providerCategory="LLM"
          disabled={isEditDisabled}
        />
      )}

      {/* LLM Provider Selector for Memory category with llm field (mem_local_short) */}
      {memoryLlmField && (
        <ProviderRefSelector
          field={memoryLlmField}
          providerCategory="LLM"
          disabled={isEditDisabled}
        />
      )}

      {/* Advanced Test Options */}
      <ProviderTestInput
        category={selectedCategory}
        onInputChange={setTestInputData}
        disabled={isEditDisabled}
      />

      {/* Test Results */}
      <ProviderTestResults />
    </div>
  );
}

function ProviderFieldRenderer({
  field,
  isEditDisabled,
}: {
  field: ProviderField;
  isEditDisabled: boolean;
}) {
  const { formValues, errors, setFieldValue } = useProviderSheetStore();
  const value = formValues[field.name];
  const error = errors[field.name];

  if (field.type === "audio_file") {
    return (
      <AudioFileUpload
        key={field.name}
        fieldName={field.name}
        label={field.label}
        description={field.description}
        value={value as string | undefined}
        onChange={(base64Value) => setFieldValue(field.name, base64Value ?? "")}
        disabled={isEditDisabled}
        accept={field.accept}
        error={error}
        required={field.required}
      />
    );
  }

  // Dynamic select - load options from API
  if (field.type === "dynamic_select") {
    return (
      <DynamicSelectField
        key={field.name}
        field={field}
        isEditDisabled={isEditDisabled}
      />
    );
  }

  if (field.type === "textarea") {
    return (
      <div key={field.name} className="space-y-2">
        <Text strong size="small">
          {field.label}
          {field.required && <span className="ml-1 text-red-500">*</span>}
        </Text>
        <TextArea
          placeholder={field.placeholder}
          disabled={isEditDisabled}
          value={String(value ?? "")}
          onChange={(value) => setFieldValue(field.name, value)}
          rows={4}
        />
        {field.description && (
          <Text type="tertiary" size="small">{field.description}</Text>
        )}
        {error && <Text type="danger" size="small">{error}</Text>}
      </div>
    );
  }

  if (field.type === "select" && field.options) {
    const optionList = field.options.map((opt) => {
      const optValue = typeof opt === "string" ? opt : opt.value;
      const optLabel = typeof opt === "string" ? opt : opt.label;
      return { value: optValue, label: optLabel };
    });

    return (
      <div key={field.name} className="space-y-2">
        <Text strong size="small">
          {field.label}
          {field.required && <span className="ml-1 text-red-500">*</span>}
        </Text>
        <Select
          style={{ width: "100%" }}
          value={String(value ?? "")}
          onChange={(v) => setFieldValue(field.name, v)}
          disabled={isEditDisabled}
          optionList={optionList}
          placeholder="Select..."
        />
        {field.description && (
          <Text type="tertiary" size="small">{field.description}</Text>
        )}
        {error && <Text type="danger" size="small">{error}</Text>}
      </div>
    );
  }

  if (field.type === "boolean") {
    return (
      <div key={field.name} className="space-y-2">
        <Checkbox
          checked={Boolean(value)}
          onChange={(e) => setFieldValue(field.name, e.target.checked)}
          disabled={isEditDisabled}
        >
          {field.label}
        </Checkbox>
        {field.description && (
          <Text type="tertiary" size="small" className="block">{field.description}</Text>
        )}
        {error && <Text type="danger" size="small">{error}</Text>}
      </div>
    );
  }

  return (
    <div key={field.name} className="space-y-2">
      <Text strong size="small">
        {field.label}
        {field.required && <span className="ml-1 text-red-500">*</span>}
      </Text>

      <Input
        type={
          field.type === "secret"
            ? "password"
            : field.type === "number" || field.type === "integer"
              ? "number"
              : "text"
        }
        placeholder={field.placeholder}
        disabled={isEditDisabled}
        value={String(value ?? "")}
        onChange={(v) => {
          const newValue =
            field.type === "number" || field.type === "integer"
              ? v === ""
                ? ""
                : Number(v)
              : v;
          setFieldValue(field.name, newValue);
        }}
      />

      {field.description && (
        <Text type="tertiary" size="small">{field.description}</Text>
      )}

      {(field.min !== undefined || field.max !== undefined) && (
        <Text type="tertiary" size="small">
          {field.min !== undefined && `Min: ${field.min}`}
          {field.min !== undefined && field.max !== undefined && " | "}
          {field.max !== undefined && `Max: ${field.max}`}
        </Text>
      )}

      {error && <Text type="danger" size="small">{error}</Text>}
    </div>
  );
}

function renderField(
  field: ProviderField,
  isEditDisabled: boolean
): React.ReactNode {
  return (
    <ProviderFieldRenderer field={field} isEditDisabled={isEditDisabled} />
  );
}
