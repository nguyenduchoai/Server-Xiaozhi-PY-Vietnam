
import { memo, useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { IconPlus, IconAlertTriangle } from "@douyinfe/semi-icons";
import { Button, Empty, Skeleton, Banner, Row, Col } from "@douyinfe/semi-ui";

import { useAgentList, useCreateAgent } from "@hooks/useAgent";
import type { Agent } from "@types";
import type { CreateAgentFormValues } from "@/components/AgentDialog";
import { AgentCard } from "@/components/AgentCard";
import { AgentDialog } from "@/components/AgentDialog";
import { PageHead } from "@/components/PageHead";
import { IllustrationNoContent } from '@douyinfe/semi-illustrations';

const AgentsPageComponent = () => {
  const { t } = useTranslation(["agents", "common"]);
  const navigate = useNavigate();
  const { data, isLoading, isError, error, refetch } = useAgentList();
  const { mutate: createAgent, isPending: isCreating } = useCreateAgent();

  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const handleRetry = useCallback(() => {
    refetch();
  }, [refetch]);

  const handleAgentCardClick = useCallback(
    (agent: Agent) => {
      navigate(`/agents/${agent.id}`);
    },
    [navigate]
  );

  const handleCreateAgent = useCallback(
    async (payload: CreateAgentFormValues) => {
      setCreateError(null);
      return new Promise<void>((resolve, reject) => {
        createAgent(
          {
            agent_name: payload.agent_name,
            description: payload.description,
            user_profile: payload.user_profile,
          },
          {
            onSuccess: () => {
              setIsDialogOpen(false);
              setCreateError(null);
              resolve();
            },
            onError: (err: unknown) => {
              const errorMessage =
                err instanceof Error
                  ? err.message
                  : t("agents:error_creating_agent");
              setCreateError(errorMessage);
              reject(err);
            },
          }
        );
      });
    },
    [createAgent, t]
  );

  const agents = data?.data ?? [];
  const hasAgents = agents.length > 0;

  return (
    <>
      <PageHead
        title="agents:page.title"
        description="agents:page.description"
        translateTitle
        translateDescription
      />
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-[var(--semi-color-text-0)]">
              {t("agents:agents")}
            </h1>
            <p className="text-[var(--semi-color-text-2)] mt-2">{t("common:common")}</p>
          </div>
          <Button
            onClick={() => setIsDialogOpen(true)}
            icon={<IconPlus />}
            theme="solid"
            type="primary"
            disabled={isLoading}
          >
            {t("agents:create_agent")}
          </Button>
        </div>

        {/* Loading State */}
        {isLoading && (
          <Row gutter={[16, 16]}>
            {Array.from({ length: 3 }).map((_, index) => (
              <Col xs={24} sm={12} lg={8} key={`skeleton-${index}`}>
                <Skeleton placeholder={<Skeleton.Image style={{ width: '100%', height: 200 }} />} loading={true} active>
                  <Skeleton.Paragraph rows={2} />
                </Skeleton>
              </Col>
            ))}
          </Row>
        )}

        {/* Error State */}
        {isError && !isLoading && (
          <Banner
            type="danger"
            icon={<IconAlertTriangle />}
            description={
              <div>
                <div>{t("agents:error_loading_agents")}</div>
                <div className="text-sm mt-1">{error?.message || t("common:something_went_wrong")}</div>
                <Button onClick={handleRetry} size="small" theme="borderless" className="mt-2">
                  {t("common:retry")}
                </Button>
              </div>
            }
          />
        )}

        {/* Empty State */}
        {!isLoading && !isError && !hasAgents && (
          <Empty
            image={<IllustrationNoContent style={{ width: 150, height: 150 }} />}
            title={t("agents:no_agents")}
            description={t("common:no_data")}
          >
            <Button onClick={() => setIsDialogOpen(true)} theme="solid" type="primary">
              {t("agents:create_agent")}
            </Button>
          </Empty>
        )}

        {/* Agents Grid */}
        {!isLoading && !isError && hasAgents && (
          <Row gutter={[16, 16]}>
            {agents.map((agent) => (
              <Col xs={24} sm={12} lg={8} key={agent.id}>
                <AgentCard
                  agent={agent}
                  onClick={handleAgentCardClick}
                />
              </Col>
            ))}
          </Row>
        )}

        {/* Create Agent Dialog */}
        <AgentDialog
          open={isDialogOpen}
          onOpenChange={setIsDialogOpen}
          mode="create"
          onSubmit={handleCreateAgent}
          isLoading={isCreating}
          error={createError}
          onErrorDismiss={() => setCreateError(null)}
        />
      </div>
    </>
  );
};

export const AgentsPage = memo(AgentsPageComponent);
