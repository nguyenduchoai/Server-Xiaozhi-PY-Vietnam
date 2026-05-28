/**
 * KnowledgeSearchBar - Semi Design implementation
 */

import { useState, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { Input, Button, Dropdown, Typography } from "@douyinfe/semi-ui";
import { IconSearch, IconClose, IconFilter } from "@douyinfe/semi-icons";
import { ALL_SECTORS, KnowledgeSectorBadge } from "./KnowledgeSectorBadge";
import type { MemorySector } from "@/types";

const { Text } = Typography;

type KnowledgeSearchBarProps = {
  onSearch: (query: string) => void;
  onFilterChange: (sector: MemorySector | null) => void;
  selectedSector: MemorySector | null;
  isSearching?: boolean;
};

export const KnowledgeSearchBar = ({
  onSearch,
  onFilterChange,
  selectedSector,
  isSearching = false,
}: KnowledgeSearchBarProps) => {
  const { t, i18n } = useTranslation("agents");
  const [query, setQuery] = useState("");

  const handleInputChange = useCallback((value: string) => {
    setQuery(value);
  }, []);

  const handleSearch = useCallback(() => {
    onSearch(query);
  }, [onSearch, query]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter") {
        handleSearch();
      }
    },
    [handleSearch]
  );

  const handleClear = useCallback(() => {
    setQuery("");
    onSearch("");
  }, [onSearch]);

  const handleSectorSelect = useCallback(
    (sector: MemorySector) => {
      onFilterChange(selectedSector === sector ? null : sector);
    },
    [selectedSector, onFilterChange]
  );

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex-1">
        <Input
          prefix={<IconSearch />}
          suffix={query ? (
            <IconClose className="cursor-pointer" onClick={handleClear} />
          ) : null}
          placeholder={t("search_knowledge")}
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          showClear={false}
        />
      </div>

      <Button
        icon={<IconSearch />}
        theme="solid"
        type="primary"
        onClick={handleSearch}
        loading={isSearching}
      >
        {t("search")}
      </Button>

      <Dropdown
        trigger="click"
        position="bottomRight"
        clickToHide
        render={
          <Dropdown.Menu>
            {ALL_SECTORS.map((sector) => (
              <Dropdown.Item
                key={sector}
                active={selectedSector === sector}
                onClick={() => handleSectorSelect(sector)}
              >
                <KnowledgeSectorBadge
                  sector={sector}
                  locale={i18n.language as "en" | "vi"}
                />
              </Dropdown.Item>
            ))}
            {selectedSector && (
              <>
                <Dropdown.Divider />
                <Dropdown.Item onClick={() => onFilterChange(null)}>
                  <Text type="tertiary">{t("clear_filter")}</Text>
                </Dropdown.Item>
              </>
            )}
          </Dropdown.Menu>
        }
      >
        <Button
          icon={<IconFilter />}
          type={selectedSector ? "primary" : "tertiary"}
          theme={selectedSector ? "light" : "borderless"}
        />
      </Dropdown>
    </div>
  );
};
