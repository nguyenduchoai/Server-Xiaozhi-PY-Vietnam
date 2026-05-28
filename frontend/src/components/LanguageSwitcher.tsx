/**
 * LanguageSwitcher - Semi Design implementation
 */

import { useAtom } from "jotai";
import { useTranslation } from "react-i18next";
import { Button, Dropdown } from "@douyinfe/semi-ui";
import { IconLanguage } from "@douyinfe/semi-icons";
import { languageAtom } from "@/store/language-atom";

export const LanguageSwitcher = () => {
  const { i18n } = useTranslation();
  const [language, setLanguage] = useAtom(languageAtom);

  const changeLanguage = (lng: "en" | "vi") => {
    i18n.changeLanguage(lng);
    setLanguage(lng);
    localStorage.setItem("i18n", lng);
  };

  return (
    <Dropdown
      trigger="click"
      position="bottomRight"
      clickToHide
      render={
        <Dropdown.Menu>
          <Dropdown.Item
            onClick={() => changeLanguage("en")}
            active={language === "en"}
          >
            🇺🇸 English
          </Dropdown.Item>
          <Dropdown.Item
            onClick={() => changeLanguage("vi")}
            active={language === "vi"}
          >
            🇻🇳 Tiếng Việt
          </Dropdown.Item>
        </Dropdown.Menu>
      }
    >
      <Button
        icon={<IconLanguage />}
        theme="borderless"
        type="tertiary"
      />
    </Dropdown>
  );
};

export default LanguageSwitcher;
