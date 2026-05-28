/**
 * UserDropdownMenu - Semi Design implementation
 */

import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAtom } from "jotai";
import { ChevronDown } from "lucide-react";
import { Dropdown, Avatar, Typography } from "@douyinfe/semi-ui";
import { IconUser, IconSetting, IconExit, IconTick, IconLanguage } from "@douyinfe/semi-icons";
import { useAuth } from "@/hooks";
import { languageAtom } from "@/store/language-atom";

const { Text } = Typography;

interface UserDropdownMenuProps {
  className?: string;
}

export const UserDropdownMenu = ({ className }: UserDropdownMenuProps) => {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation("navigation");
  const { user, logout } = useAuth();
  const [language, setLanguage] = useAtom(languageAtom);

  const changeLanguage = (lng: "en" | "vi") => {
    i18n.changeLanguage(lng);
    setLanguage(lng);
    localStorage.setItem("i18n", lng);
  };

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  if (!user) return null;

  return (
    <Dropdown
      trigger="click"
      position="bottomRight"
      clickToHide
      render={
        <Dropdown.Menu>
          <Dropdown.Item onClick={() => navigate("/profile")}>
            <IconUser className="mr-2" />
            {t("profile")}
          </Dropdown.Item>

          {user.is_superuser && (
            <Dropdown.Item onClick={() => navigate("/settings")}>
              <IconSetting className="mr-2" />
              {t("settings")}
            </Dropdown.Item>
          )}

          <Dropdown.Divider />

          {/* Language submenu */}
          <Dropdown
            trigger="hover"
            position="leftTop"
            render={
              <Dropdown.Menu>
                <Dropdown.Item
                  onClick={() => changeLanguage("en")}
                  active={language === "en"}
                >
                  🇺🇸 English {language === "en" && <IconTick className="ml-2" />}
                </Dropdown.Item>
                <Dropdown.Item
                  onClick={() => changeLanguage("vi")}
                  active={language === "vi"}
                >
                  🇻🇳 Tiếng Việt {language === "vi" && <IconTick className="ml-2" />}
                </Dropdown.Item>
              </Dropdown.Menu>
            }
          >
            <Dropdown.Item>
              <IconLanguage className="mr-2" />
              {t("language")}
              <span className="ml-auto">▸</span>
            </Dropdown.Item>
          </Dropdown>

          <Dropdown.Divider />

          <Dropdown.Item type="danger" onClick={handleLogout}>
            <IconExit className="mr-2" />
            {t("logout")}
          </Dropdown.Item>
        </Dropdown.Menu>
      }
    >
      <div className={`flex items-center gap-2 cursor-pointer pl-1 pr-2 py-0.5 ${className || ""}`}>
        <Avatar
          size="small"
          src={user.profile_image_base64 || undefined}
          alt={user.name}
          style={{
            background: 'linear-gradient(135deg, #3B82F6, #1D4ED8)',
            boxShadow: '0 2px 6px rgba(37, 99, 235, 0.3)',
            border: '2px solid var(--semi-color-bg-0)',
            fontWeight: 600,
            color: '#FFFFFF'
          }}
        >
          {getInitials(user.name)}
        </Avatar>
        <Text className="hidden sm:inline text-sm font-semibold" style={{ letterSpacing: '-0.2px' }}>
          {user.name}
        </Text>
        <ChevronDown className="h-4 w-4 text-gray-400 opacity-60" />
      </div>
    </Dropdown>
  );
};
