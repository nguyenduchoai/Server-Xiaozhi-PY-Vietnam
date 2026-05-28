
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button, Empty, Typography } from "@douyinfe/semi-ui";
import { PageHead } from "@/components/PageHead";
import { IllustrationNotFound, IllustrationNotFoundDark } from "@douyinfe/semi-illustrations";

export const NotFoundPage = () => {
  const navigate = useNavigate();
  const { t } = useTranslation("common");

  return (
    <>
      <PageHead
        title="404 - Page Not Found"
        description="The page you are looking for does not exist"
      />
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', backgroundColor: 'var(--semi-color-bg-0)' }}>
        <Empty
          image={<IllustrationNotFound style={{ width: 200, height: 200 }} />}
          darkModeImage={<IllustrationNotFoundDark style={{ width: 200, height: 200 }} />}
          title={<Typography.Title heading={2}>404</Typography.Title>}
          description={
            <div>
              <Typography.Title heading={4}>{t("page_not_found")}</Typography.Title>
              <Typography.Text type="secondary">{t("page_not_found_desc")}</Typography.Text>
            </div>
          }
        >
          <Button onClick={() => navigate("/")} theme="solid" type="primary">
            {t("go_home")}
          </Button>
        </Empty>
      </div>
    </>
  );
};

export default NotFoundPage;
