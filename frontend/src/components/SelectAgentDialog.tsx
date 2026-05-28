/**
 * SelectAgentDialog - Semi Design implementation
 * Dialog for selecting an agent to assign template
 */

import { useState } from "react";
import { Bot } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useAgentList } from "@/queries/agent-queries";
import {
  Modal,
  Input,
  Button,
  Tag,
  Skeleton,
  Empty,
  Typography,
  Card,
  Checkbox,
} from "@douyinfe/semi-ui";
import { IconSearch, IconTick } from "@douyinfe/semi-icons";

const { Text, Title } = Typography;

export interface SelectAgentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (agentId: string, setActive: boolean) => Promise<void>;
  isLoading?: boolean;
  excludeAgentIds?: string[];
}

export function SelectAgentDialog({
  open,
  onOpenChange,
  onSelect,
  isLoading = false,
  excludeAgentIds = [],
}: SelectAgentDialogProps) {
  const { t } = useTranslation("templates");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [setAsActive, setSetAsActive] = useState(true);

  const { data, isLoading: isLoadingAgents } = useAgentList({
    page: 1,
    page_size: 50,
  });

  const agents = data?.data ?? [];

  const filteredAgents = agents.filter((agent) => {
    const isExcluded = excludeAgentIds.includes(agent.id);
    if (isExcluded) return false;

    if (!searchQuery) return true;

    const query = searchQuery.toLowerCase();
    return (
      agent.agent_name.toLowerCase().includes(query) ||
      agent.description?.toLowerCase().includes(query)
    );
  });

  const handleSelect = async () => {
    if (!selectedAgentId) return;

    try {
      await onSelect(selectedAgentId, setAsActive);
      handleClose();
    } catch (error) {
      console.error("Select agent error:", error);
    }
  };

  const handleClose = () => {
    setSearchQuery("");
    setSelectedAgentId(null);
    setSetAsActive(true);
    onOpenChange(false);
  };

  return (
    <Modal
      title={
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-green-500 to-teal-600">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <Title heading={5} className="!mb-0">{t("select_agent")}</Title>
            <Text type="tertiary" size="small">{t("select_agent_desc")}</Text>
          </div>
        </div>
      }
      visible={open}
      onCancel={handleClose}
      width={520}
      footer={
        <div className="flex justify-end gap-3">
          <Button onClick={handleClose} disabled={isLoading}>
            {t("common:cancel")}
          </Button>
          <Button
            theme="solid"
            type="primary"
            onClick={handleSelect}
            disabled={!selectedAgentId || isLoading}
            loading={isLoading}
          >
            {t("add_agent")}
          </Button>
        </div>
      }
      bodyStyle={{ padding: "16px 24px" }}
    >
      <div className="space-y-4">
        {/* Search Input */}
        <Input
          prefix={<IconSearch />}
          placeholder={t("search_agents")}
          value={searchQuery}
          onChange={(v) => setSearchQuery(v)}
          size="large"
          showClear
        />

        {/* Agents List */}
        <div className="max-h-[320px] overflow-y-auto pr-1 space-y-2">
          {isLoadingAgents ? (
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton.Paragraph key={i} rows={2} style={{ marginBottom: 12 }} />
              ))}
            </div>
          ) : filteredAgents.length === 0 ? (
            <div className="py-8">
              <Empty
                image={<Bot className="h-12 w-12 text-gray-300" />}
                title={searchQuery ? t("no_agents_found") : t("no_available_agents")}
              />
            </div>
          ) : (
            filteredAgents.map((agent) => {
              const isSelected = selectedAgentId === agent.id;

              return (
                <div key={agent.id} onClick={() => setSelectedAgentId(agent.id)}>
                  <Card
                    className={`cursor-pointer transition-all duration-200 ${isSelected
                      ? "!border-green-500 !bg-green-50 dark:!bg-green-900/20 shadow-md"
                      : "hover:!border-green-300 hover:shadow-sm"
                      }`}
                    bodyStyle={{ padding: 12 }}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-lg">🤖</span>
                          <Text strong ellipsis={{ showTooltip: true }} className="text-sm">
                            {agent.agent_name}
                          </Text>
                          <Tag
                            size="small"
                            color={agent.status === "enabled" ? "green" : "grey"}
                          >
                            {agent.status === "enabled" ? "Enabled" : "Disabled"}
                          </Tag>
                        </div>
                        {agent.description && (
                          <Text type="tertiary" size="small" ellipsis={{ rows: 1 }}>
                            {agent.description}
                          </Text>
                        )}
                      </div>
                      {isSelected && (
                        <div className="flex-shrink-0 p-1.5 rounded-full bg-green-500">
                          <IconTick className="text-white" />
                        </div>
                      )}
                    </div>
                  </Card>
                </div>
              );
            })
          )}
        </div>

        {/* Set as Active Checkbox */}
        {selectedAgentId && (
          <div className="pt-3 border-t border-gray-100 dark:border-gray-800">
            <Checkbox
              checked={setAsActive}
              onChange={(e) => setSetAsActive(e.target.checked ?? false)}
            >
              <Text type="tertiary" size="small">
                {t("set_as_active_for_agent")}
              </Text>
            </Checkbox>
          </div>
        )}
      </div>
    </Modal>
  );
}

export default SelectAgentDialog;
