/**
 * AgentDeviceManager - Component for managing agent-device assignments
 * 
 * Shows assigned agents with active indicator, allows switching, assigning, and unassigning.
 * Used inside DeviceDetailPage.
 */
import { useState } from "react";
import { toast } from "sonner";
import {
  Card,
  Button,
  Typography,
  Tag,
  Empty,
  Modal,
  Select,
  Spin,
  Popconfirm,
  Tooltip,
} from "@douyinfe/semi-ui";
import {
  Bot,
  Plus,
  Trash2,
  ArrowRightLeft,
  CheckCircle,
  Circle,
} from "lucide-react";
import {
  useDeviceAgents,
  useAssignAgentToDevice,
  useUnassignAgentFromDevice,
  useSwitchActiveAgent,
} from "@/queries/device-queries";
import { useQuery } from "@tanstack/react-query";
import apiClient from "@/config/axios-instance";
import { AGENT_ENDPOINTS } from "@/lib/api";

const { Title, Text } = Typography;

interface Agent {
  id: string;
  agent_name: string;
  description?: string;
}

interface AgentDeviceManagerProps {
  deviceId: string;
  deviceName?: string;
}

export default function AgentDeviceManager({ deviceId, deviceName }: AgentDeviceManagerProps) {
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string | undefined>(undefined);

  // Queries
  const { data: agentsData, isLoading, refetch } = useDeviceAgents(deviceId);
  const agents = agentsData?.data || [];

  // Available agents for assignment
  const { data: allAgents } = useQuery({
    queryKey: ["agents", "list"],
    queryFn: async () => {
      const { data } = await apiClient.get(AGENT_ENDPOINTS.LIST);
      return data?.data || data || [];
    },
    enabled: showAssignModal,
  });

  // Mutations
  const assignMutation = useAssignAgentToDevice();
  const unassignMutation = useUnassignAgentFromDevice();
  const switchMutation = useSwitchActiveAgent();

  // Filter out already assigned agents
  const availableAgents = (allAgents || []).filter(
    (a: Agent) => !agents.some((da: { agent_id: string }) => da.agent_id === a.id)
  );

  const handleAssign = async () => {
    if (!selectedAgentId) return;
    try {
      await assignMutation.mutateAsync({ deviceId, agentId: selectedAgentId });
      toast.success("Đã gán agent vào thiết bị");
      setShowAssignModal(false);
      setSelectedAgentId(undefined);
      refetch();
    } catch (err: unknown) {
      toast.error("Lỗi khi gán agent: " + (err instanceof Error ? err.message : "Unknown"));
    }
  };

  const handleUnassign = async (agentId: string) => {
    try {
      await unassignMutation.mutateAsync({ deviceId, agentId });
      toast.success("Đã gỡ agent khỏi thiết bị");
      refetch();
    } catch (err: unknown) {
      toast.error("Lỗi: " + (err instanceof Error ? err.message : "Unknown"));
    }
  };

  const handleSwitch = async (agentId: string) => {
    try {
      await switchMutation.mutateAsync({ deviceId, agentId });
      toast.success("Đã chuyển active agent");
      refetch();
    } catch (err: unknown) {
      toast.error("Lỗi: " + (err instanceof Error ? err.message : "Unknown"));
    }
  };

  if (isLoading) {
    return (
      <Card>
        <div className="flex justify-center p-8">
          <Spin size="large" />
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card
        title={
          <div className="flex items-center gap-2">
            <Bot size={20} />
            <Title heading={6} style={{ margin: 0 }}>
              Agents ({agents.length})
            </Title>
          </div>
        }
        headerExtraContent={
          <Button
            icon={<Plus size={16} />}
            theme="solid"
            size="small"
            onClick={() => setShowAssignModal(true)}
          >
            Gán Agent
          </Button>
        }
      >
        {agents.length === 0 ? (
          <Empty
            image={<Bot size={48} className="text-gray-300" />}
            description="Chưa có agent nào được gán cho thiết bị này"
          />
        ) : (
          <div className="space-y-3">
            {agents.map((agent: { assignment_id: string; agent_id: string; agent_name: string; is_active: boolean; assigned_at?: string; assigned_date?: string; agent_status?: string }) => (
              <div
                key={agent.assignment_id}
                className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                  agent.is_active
                    ? "border-blue-300 bg-blue-50"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
              >
                <div className="flex items-center gap-3">
                  {agent.is_active ? (
                    <CheckCircle size={20} className="text-blue-500" />
                  ) : (
                    <Circle size={20} className="text-gray-300" />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <Text strong>{agent.agent_name}</Text>
                      {agent.agent_status === "deleted" ? (
                        <Tag color="red" size="small">Đã xóa</Tag>
                      ) : agent.is_active ? (
                        <Tag color="blue" size="small">Active</Tag>
                      ) : (
                        <Tag color="grey" size="small">Inactive</Tag>
                      )}
                    </div>
                    <div className="flex flex-col">
                      <Text type="tertiary" size="small">
                        ID: {agent.agent_id.substring(0, 8)}...
                      </Text>
                      {agent.assigned_date && (
                        <Text type="tertiary" size="small">
                          Gán lúc: {new Date(agent.assigned_date).toLocaleString("vi-VN")}
                        </Text>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {!agent.is_active && (
                    <Tooltip content="Chuyển sang agent này">
                      <Button
                        icon={<ArrowRightLeft size={14} />}
                        size="small"
                        theme="borderless"
                        onClick={() => handleSwitch(agent.agent_id)}
                        loading={switchMutation.isPending}
                      />
                    </Tooltip>
                  )}
                  <Popconfirm
                    title="Gỡ agent"
                    content={`Bạn có chắc muốn gỡ "${agent.agent_name}" khỏi thiết bị?`}
                    onConfirm={() => handleUnassign(agent.agent_id)}
                  >
                    <Button
                      icon={<Trash2 size={14} />}
                      size="small"
                      theme="borderless"
                      type="danger"
                    />
                  </Popconfirm>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Assign Agent Modal */}
      <Modal
        title="Gán Agent vào thiết bị"
        visible={showAssignModal}
        onCancel={() => {
          setShowAssignModal(false);
          setSelectedAgentId(undefined);
        }}
        onOk={handleAssign}
        okText="Gán"
        cancelText="Hủy"
        confirmLoading={assignMutation.isPending}
        okButtonProps={{ disabled: !selectedAgentId }}
      >
        <div className="space-y-4">
          <Text>
            Chọn agent để gán vào thiết bị "{deviceName || deviceId}"
          </Text>
          <Select
            placeholder="Chọn agent..."
            style={{ width: "100%" }}
            value={selectedAgentId}
            onChange={(v) => setSelectedAgentId(v as string)}
            optionList={availableAgents.map((a: Agent) => ({
              value: a.id,
              label: a.agent_name || `Agent ${a.id.substring(0, 8)}`,
            }))}
            showClear
            filter
          />
          {availableAgents.length === 0 && (
            <Text type="tertiary" size="small">
              Tất cả agent đã được gán. Tạo agent mới để thêm.
            </Text>
          )}
        </div>
      </Modal>
    </>
  );
}
