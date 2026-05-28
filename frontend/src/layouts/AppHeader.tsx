/**
 * AppHeader - Semi Design implementation
 */

import { useBreadcrumb } from "@/hooks";
import { SidebarTrigger } from "@/components/Sidebar";
import { UserDropdownMenu } from "@/components/UserDropdownMenu";
import { useNavigate, useLocation } from "react-router-dom";
import { Breadcrumb } from "@douyinfe/semi-ui";

export const AppHeader = () => {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  let agentName: string | undefined;
  let templateName: string | undefined;
  if (pathname.includes("/agents/")) {
    agentName = sessionStorage.getItem("currentAgentName") || undefined;
  }
  if (pathname.includes("/templates/")) {
    templateName = sessionStorage.getItem("currentTemplateName") || undefined;
  }

  const breadcrumbs = useBreadcrumb({ agentName, templateName });

  const routes = breadcrumbs.map((breadcrumb) => ({
    path: breadcrumb.href || "",
    name: breadcrumb.label,
    href: breadcrumb.href,
  }));

  return (
    <div className="flex items-center justify-between w-full">
      <div className="flex items-center gap-4 flex-1">
        <SidebarTrigger className="-ml-1" />

        <Breadcrumb
          routes={routes}
          onClick={(item) => item?.href && navigate(item.href)}
          renderItem={(item) => (
            <span className="cursor-pointer hover:text-blue-500">
              {item.name}
            </span>
          )}
        />
      </div>

      <div className="flex items-center flex-shrink-0">
        <UserDropdownMenu />
      </div>
    </div>
  );
};
