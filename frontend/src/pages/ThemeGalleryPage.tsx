/**
 * Theme Gallery Page - Semi Design version (consistent with admin UI)
 */
import { useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import {
    Card,
    Typography,
    Input,
    Select,
    Button,
    Tag,
    Empty,
    Spin,
    Modal,
    Toast,
    Row,
    Col,
    Space,
    Popconfirm
} from "@douyinfe/semi-ui";
import {
    IconSearch,
    IconGridView,
    IconList,
    IconDownload,
    IconDelete,
    IconTick
} from "@douyinfe/semi-icons";
import { Palette, Monitor, Sparkles } from "lucide-react";
import { PageHead } from "@/components";

import {
    useThemes,
    useThemeCategories,
    useScreenTypes,
    useApplyTheme,
    useDeleteTheme,
    type Theme,
} from "@/queries/theme-queries";
import { useDeviceList } from "@/queries/device-queries";

const { Title, Text } = Typography;

export default function ThemeGalleryPage() {
    const [searchParams, setSearchParams] = useSearchParams();

    // Filters
    const [search, setSearch] = useState(searchParams.get("search") || "");
    const [category, setCategory] = useState(searchParams.get("category") || "");
    const [screenType, setScreenType] = useState(searchParams.get("screen_type") || "");
    const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

    // Apply theme modal
    const [selectedTheme, setSelectedTheme] = useState<Theme | null>(null);
    const [selectedDevice, setSelectedDevice] = useState<string>("");
    const [isApplyModalVisible, setIsApplyModalVisible] = useState(false);

    // Queries
    const { data: themesData, isLoading: themesLoading, refetch } = useThemes({
        search: search || undefined,
        category: category || undefined,
        screen_type: screenType || undefined,
        page: 1,
        limit: 50,
    });
    const { data: categories } = useThemeCategories();
    const { data: screenTypes } = useScreenTypes();
    const { data: devicesData } = useDeviceList({});

    // Mutations
    const applyThemeMutation = useApplyTheme();
    const deleteThemeMutation = useDeleteTheme();

    const themes = themesData?.themes || [];
    const devices = devicesData?.data || [];

    // Category options for select
    const categoryOptions = useMemo(() => [
        { value: "", label: "Tất cả danh mục" },
        ...(categories?.map(c => ({ value: c.id, label: `${c.icon} ${c.name}` })) || [])
    ], [categories]);

    // Screen type options
    const screenTypeOptions = useMemo(() => [
        { value: "", label: "Tất cả kích thước" },
        ...(screenTypes?.map(s => ({ value: s.id, label: s.name })) || [])
    ], [screenTypes]);

    // Device options
    const deviceOptions = useMemo(() =>
        devices.map(d => ({ value: d.id, label: d.device_name || d.mac_address })),
        [devices]
    );

    const handleSearch = (value: string) => {
        setSearch(value);
        setSearchParams(prev => {
            if (value) prev.set("search", value);
            else prev.delete("search");
            return prev;
        });
    };

    const handleCategoryChange = (value: string) => {
        setCategory(value);
        setSearchParams(prev => {
            if (value) prev.set("category", value);
            else prev.delete("category");
            return prev;
        });
    };

    const handleScreenTypeChange = (value: string) => {
        setScreenType(value);
        setSearchParams(prev => {
            if (value) prev.set("screen_type", value);
            else prev.delete("screen_type");
            return prev;
        });
    };

    const openApplyModal = (theme: Theme) => {
        setSelectedTheme(theme);
        setIsApplyModalVisible(true);
    };

    const handleApplyTheme = async () => {
        if (!selectedTheme || !selectedDevice) {
            Toast.warning("Vui lòng chọn thiết bị");
            return;
        }

        try {
            await applyThemeMutation.mutateAsync({
                deviceId: selectedDevice,
                themeId: selectedTheme.id,
            });
            Toast.success(`Đã áp dụng theme "${selectedTheme.name}" cho thiết bị`);
            setIsApplyModalVisible(false);
            setSelectedTheme(null);
            setSelectedDevice("");
        } catch {
            Toast.error("Không thể áp dụng theme");
        }
    };

    const handleDeleteTheme = async (theme: Theme) => {
        try {
            await deleteThemeMutation.mutateAsync(theme.id);
            Toast.success(`Đã xóa theme "${theme.name}"`);
            refetch();
        } catch {
            Toast.error("Không thể xóa theme");
        }
    };

    // Theme card component
    const ThemeCard = ({ theme }: { theme: Theme }) => {
        const colors = theme.theme_data?.colors;

        return (
            <Card
                className="theme-card"
                style={{ overflow: "hidden" }}
                bodyStyle={{ padding: 0 }}
                shadows="hover"
            >
                {/* Preview */}
                <div
                    style={{
                        height: 160,
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        position: "relative",
                        background: colors
                            ? `linear-gradient(135deg, ${colors.background} 0%, ${colors.primary} 100%)`
                            : "linear-gradient(135deg, #1e293b 0%, #475569 100%)"
                    }}
                >
                    {/* Simulated screen content */}
                    <div style={{ textAlign: "center", color: colors?.text || "#fff" }}>
                        <div style={{ fontSize: 24, fontWeight: 600, marginBottom: 4 }}>14:30</div>
                        <div style={{ fontSize: 32, marginBottom: 4 }}>😊</div>
                        <div style={{ fontSize: 12, opacity: 0.8 }}>🌤️ 32°C</div>
                    </div>

                    {/* Color swatches */}
                    {colors && (
                        <div style={{ position: "absolute", bottom: 8, left: 8, display: "flex", gap: 4 }}>
                            <div style={{
                                width: 16, height: 16, borderRadius: "50%",
                                backgroundColor: colors.primary, border: "2px solid rgba(255,255,255,0.3)"
                            }} />
                            <div style={{
                                width: 16, height: 16, borderRadius: "50%",
                                backgroundColor: colors.secondary, border: "2px solid rgba(255,255,255,0.3)"
                            }} />
                        </div>
                    )}

                    {/* System badge */}
                    {theme.is_system && (
                        <Tag color="blue" style={{ position: "absolute", top: 8, right: 8 }}>
                            Mặc định
                        </Tag>
                    )}
                </div>

                {/* Info */}
                <div style={{ padding: 12 }}>
                    <Text strong ellipsis={{ showTooltip: true }} style={{ display: "block", marginBottom: 4 }}>
                        {theme.name}
                    </Text>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <Tag size="small" color="grey">{theme.screen_type}</Tag>
                        <Space>
                            <Text type="tertiary" size="small">
                                <IconDownload size="small" /> {theme.download_count}
                            </Text>
                        </Space>
                    </div>

                    {/* Actions */}
                    <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
                        <Button
                            theme="solid"
                            type="primary"
                            size="small"
                            icon={<IconTick />}
                            onClick={() => openApplyModal(theme)}
                            style={{ flex: 1 }}
                        >
                            Áp dụng
                        </Button>
                        {!theme.is_system && (
                            <Popconfirm
                                title="Xác nhận xóa"
                                content={`Xóa theme "${theme.name}"?`}
                                onConfirm={() => handleDeleteTheme(theme)}
                            >
                                <Button
                                    theme="borderless"
                                    type="danger"
                                    size="small"
                                    icon={<IconDelete />}
                                />
                            </Popconfirm>
                        )}
                    </div>
                </div>
            </Card>
        );
    };

    return (
        <div className="theme-gallery-page">
            <PageHead
                title="Kho Theme"
                description="Chọn giao diện cho thiết bị của bạn"
            />

            {/* Header */}
            <Card style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <div style={{
                            width: 40, height: 40, borderRadius: 10,
                            background: "linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%)",
                            display: "flex", alignItems: "center", justifyContent: "center"
                        }}>
                            <Palette size={22} color="white" />
                        </div>
                        <div>
                            <Title heading={4} style={{ margin: 0 }}>Kho Theme</Title>
                            <Text type="tertiary">{themesData?.total || 0} theme có sẵn</Text>
                        </div>
                    </div>

                    <Space>
                        <Button
                            theme={viewMode === "grid" ? "solid" : "borderless"}
                            icon={<IconGridView />}
                            onClick={() => setViewMode("grid")}
                        />
                        <Button
                            theme={viewMode === "list" ? "solid" : "borderless"}
                            icon={<IconList />}
                            onClick={() => setViewMode("list")}
                        />
                    </Space>
                </div>

                {/* Filters */}
                <Row gutter={12}>
                    <Col span={8}>
                        <Input
                            prefix={<IconSearch />}
                            placeholder="Tìm theme..."
                            value={search}
                            onChange={handleSearch}
                            showClear
                        />
                    </Col>
                    <Col span={8}>
                        <Select
                            placeholder="Danh mục"
                            value={category}
                            onChange={(v) => handleCategoryChange(String(v || ""))}
                            optionList={categoryOptions}
                            style={{ width: "100%" }}
                            prefix={<Sparkles size={16} />}
                        />
                    </Col>
                    <Col span={8}>
                        <Select
                            placeholder="Kích thước màn hình"
                            value={screenType}
                            onChange={(v) => handleScreenTypeChange(String(v || ""))}
                            optionList={screenTypeOptions}
                            style={{ width: "100%" }}
                            prefix={<Monitor size={16} />}
                        />
                    </Col>
                </Row>
            </Card>

            {/* Theme Grid */}
            {themesLoading ? (
                <div style={{ textAlign: "center", padding: 60 }}>
                    <Spin size="large" />
                </div>
            ) : themes.length === 0 ? (
                <Empty
                    title="Chưa có theme nào"
                    description="Hãy tạo theme mới từ Tạo Theme"
                    style={{ padding: 60 }}
                />
            ) : (
                <Row gutter={[16, 16]}>
                    {themes.map((theme) => (
                        <Col key={theme.id} xs={24} sm={12} md={8} lg={6} xl={4}>
                            <ThemeCard theme={theme} />
                        </Col>
                    ))}
                </Row>
            )}

            {/* Apply Theme Modal */}
            <Modal
                title={
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <Palette size={20} />
                        Áp dụng Theme
                    </div>
                }
                visible={isApplyModalVisible}
                onCancel={() => setIsApplyModalVisible(false)}
                onOk={handleApplyTheme}
                okText="Áp dụng"
                cancelText="Hủy"
                confirmLoading={applyThemeMutation.isPending}
            >
                {selectedTheme && (
                    <div>
                        {/* Theme preview */}
                        <div style={{
                            height: 120,
                            borderRadius: 8,
                            marginBottom: 16,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            background: selectedTheme.theme_data?.colors
                                ? `linear-gradient(135deg, ${selectedTheme.theme_data.colors.background} 0%, ${selectedTheme.theme_data.colors.primary} 100%)`
                                : "#1e293b"
                        }}>
                            <div style={{ textAlign: "center", color: selectedTheme.theme_data?.colors?.text || "#fff" }}>
                                <div style={{ fontSize: 18, fontWeight: 600 }}>{selectedTheme.name}</div>
                                <div style={{ fontSize: 10, opacity: 0.8 }}>{selectedTheme.screen_type}</div>
                            </div>
                        </div>

                        {/* Device select */}
                        <Text style={{ display: "block", marginBottom: 8 }}>Chọn thiết bị:</Text>
                        <Select
                            placeholder="Chọn thiết bị"
                            value={selectedDevice}
                            onChange={(v) => setSelectedDevice(String(v || ""))}
                            optionList={deviceOptions}
                            style={{ width: "100%" }}
                        />
                    </div>
                )}
            </Modal>
        </div>
    );
}
