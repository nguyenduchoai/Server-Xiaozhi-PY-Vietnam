/**
 * KnowledgePreviewCard - Semi Design implementation
 */

import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Brain, ChevronRight } from "lucide-react";
import { Card, Button, Typography } from "@douyinfe/semi-ui";

const { Title, Text } = Typography;

type KnowledgePreviewCardProps = {
  agentId: string;
};

export const KnowledgePreviewCard = ({
  agentId,
}: KnowledgePreviewCardProps) => {
  const navigate = useNavigate();
  const { t } = useTranslation("agents");

  const handleManageClick = () => {
    navigate(`/agents/${agentId}/knowledge`);
  };

  return (
    <div onClick={handleManageClick} className="cursor-pointer">
      <Card
        className="h-full transition-all hover:shadow-md"
        title={
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className="h-4 w-4 text-blue-500" />
              <Title heading={6} className="!mb-0">{t("knowledge_base")}</Title>
            </div>
            <Button
              size="small"
              theme="borderless"
              onClick={(e) => {
                e.stopPropagation();
                handleManageClick();
              }}
            >
              {t("view")} <ChevronRight className="h-3 w-3 ml-1" />
            </Button>
          </div>
        }
      >
        <div className="flex flex-col items-start justify-start py-2 text-left">
          <Brain className="h-8 w-8 text-gray-300 mb-2" />
          <Text type="tertiary">
            {t("knowledge_base_description")}
          </Text>
        </div>
      </Card>
    </div>
  );
};
