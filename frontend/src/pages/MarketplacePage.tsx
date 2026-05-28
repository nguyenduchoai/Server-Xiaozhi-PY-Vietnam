import { toast } from "sonner";
import { useState, useEffect, useCallback, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { PageHead } from "@/components";
import {
    Tabs,
    TabPane,
    Card,
    Tag,
    Button,
    Input,
    Select,
    Typography,
    Rating,
    Empty,
    Spin,
    Modal,
    Form,
    Banner,
    Popconfirm,
} from "@douyinfe/semi-ui";
import {
    IconSearch,
    IconShoppingBag,
    IconBox,
    IconPlus,
    IconEdit,
    IconDelete,
    IconSetting,
} from "@douyinfe/semi-icons";
import { Package, Store, Download, ShieldCheck, Crown, Eye } from "lucide-react";

import marketplaceService from "@/services/marketplaceService";
import type { Skill, SkillInstallation, SkillCategory, SkillCreate, SkillUpdate } from "@/services/marketplaceService";

const { Title, Text, Paragraph } = Typography;

// ==================== Helper: generate slug ====================
const toSlug = (name: string) =>
    name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

export const MarketplacePage = () => {
    const { t } = useTranslation("marketplace");
    const [searchQuery, setSearchQuery] = useState("");
    const [activeTab, setActiveTab] = useState("browse");
    const [skills, setSkills] = useState<Skill[]>([]);
    const [_featuredSkills, setFeaturedSkills] = useState<Skill[]>([]);
    const [installedSkills, setInstalledSkills] = useState<SkillInstallation[]>([]);
    const [categories, setCategories] = useState<SkillCategory[]>([]);
    const [selectedCategory, setSelectedCategory] = useState("all");
    const [sortBy, setSortBy] = useState<"popular" | "newest" | "rating">("popular");
    const [loading, setLoading] = useState(false);
    const [installingSkillId, setInstallingSkillId] = useState<string | null>(null);



    // Admin Management state
    const [mySkills, setMySkills] = useState<Skill[]>([]);
    const [showCreateDialog, setShowCreateDialog] = useState(false);
    const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
    const [adminLoading, setAdminLoading] = useState(false);

    useEffect(() => {
        fetchCategories();
        fetchFeaturedSkills();
        fetchInstalledSkills();
    }, []);

    useEffect(() => {
        fetchSkills();
    }, [searchQuery, selectedCategory, sortBy]);



    const fetchCategories = async () => {
        try {
            const response = await marketplaceService.getCategories();
            setCategories(response.data || []);
        } catch (error) {
            console.error("Failed to fetch categories:", error);
        }
    };

    const fetchSkills = async () => {
        setLoading(true);
        try {
            const response = await marketplaceService.browseSkills({
                search: searchQuery || undefined,
                category: selectedCategory !== "all" ? selectedCategory : undefined,
                sort: sortBy,
                page: 1,
                page_size: 50,
            });
            setSkills(response.data || []);
        } catch (error) {
            console.error("Failed to fetch skills:", error);
            setSkills([]);
        } finally {
            setLoading(false);
        }
    };

    const fetchFeaturedSkills = async () => {
        try {
            const response = await marketplaceService.getFeaturedSkills(6);
            setFeaturedSkills(response.data || []);
        } catch (error) {
            console.error("Failed to fetch featured skills:", error);
        }
    };

    const fetchInstalledSkills = async () => {
        try {
            const response = await marketplaceService.getInstalledSkills();
            setInstalledSkills(response.data || []);
        } catch (error) {
            console.error("Failed to fetch installed skills:", error);
        }
    };

    const fetchMySkills = useCallback(async () => {
        setAdminLoading(true);
        try {
            const response = await marketplaceService.getMySkills();
            setMySkills(response.data || []);
        } catch (error) {
            console.error("Failed to fetch my skills:", error);
        } finally {
            setAdminLoading(false);
        }
    }, []);

    const handleInstall = async (skillId: string) => {
        setInstallingSkillId(skillId);
        try {
            await marketplaceService.installSkill(skillId);
            toast.success("Cài đặt thành công!");
            fetchInstalledSkills();
            fetchSkills();
        } catch (error) {
            console.error("Failed to install skill:", error);
            toast.error("Cài đặt thất bại");
        } finally {
            setInstallingSkillId(null);
        }
    };

    const handleUninstall = async (skillId: string) => {
        try {
            await marketplaceService.uninstallSkill(skillId);
            toast.success("Đã gỡ cài đặt");
            fetchInstalledSkills();
            fetchSkills();
        } catch (error) {
            console.error("Failed to uninstall skill:", error);
            toast.error("Gỡ cài đặt thất bại");
        }
    };

    const isInstalled = (skillId: string) => {
        return installedSkills.some((s) => s.skill_id === skillId);
    };

    // ==================== Admin CRUD ====================
    const handleCreateSkill = async (values: Record<string, any>) => {
        try {
            const data: SkillCreate = {
                name: values.name,
                slug: values.slug || toSlug(values.name),
                description: values.description || "",
                short_description: values.short_description,
                skill_type: values.skill_type || "mcp_server",
                category: values.category || "utilities",
                tags: values.tags ? values.tags.split(",").map((t: string) => t.trim()) : [],
                config: {},
                version: values.version || "1.0.0",
                icon_url: values.icon_url,
                banner_url: values.banner_url,
                is_premium: values.is_premium || false,
                price: values.price ? parseInt(values.price) : 0,
                is_public: values.is_public ?? true,
                is_featured: values.is_featured || false,
            };
            await marketplaceService.createSkill(data);
            toast.success("Đã tạo skill mới!");
            setShowCreateDialog(false);
            fetchMySkills();
            fetchSkills();
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || "Tạo thất bại");
        }
    };

    const handleUpdateSkill = async (values: Record<string, any>) => {
        if (!editingSkill) return;
        try {
            const data: SkillUpdate = {
                name: values.name,
                description: values.description,
                short_description: values.short_description,
                category: values.category,
                tags: values.tags ? values.tags.split(",").map((t: string) => t.trim()) : undefined,
                version: values.version,
                icon_url: values.icon_url,
                banner_url: values.banner_url,
                is_premium: values.is_premium,
                price: values.price != null ? parseInt(values.price) : undefined,
                is_public: values.is_public,
                is_featured: values.is_featured,
            };
            await marketplaceService.updateSkill(editingSkill.id, data);
            toast.success("Đã cập nhật!");
            setEditingSkill(null);
            fetchMySkills();
            fetchSkills();
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || "Cập nhật thất bại");
        }
    };

    const handleDeleteSkill = async (skillId: string) => {
        try {
            await marketplaceService.deleteSkill(skillId);
            toast.success("Đã xoá!");
            fetchMySkills();
            fetchSkills();
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || "Xoá thất bại");
        }
    };

    // ==================== Templates & Themes (filtered from skills) ====================
    const [themeSearch, setThemeSearch] = useState("");
    const [themeFilter, setThemeFilter] = useState("all");

    const themeAndTemplateSkills = useMemo(() => {
        // Filter skills that are themes, templates, or device features
        const themeTypes = ["voice_pack", "agent_template", "prompt_template"];
        const filtered = skills.filter(s => {
            const isThemeType = themeTypes.includes(s.skill_type);
            const hasThemeTag = s.tags?.some(t => ["theme", "template", "feature"].includes(t));
            return isThemeType || hasThemeTag;
        });

        // Apply local search & filter
        let result = filtered;
        if (themeSearch) {
            const q = themeSearch.toLowerCase();
            result = result.filter(s =>
                s.name.toLowerCase().includes(q) ||
                s.description?.toLowerCase().includes(q) ||
                s.tags?.some(t => t.toLowerCase().includes(q))
            );
        }
        if (themeFilter !== "all") {
            if (themeFilter === "theme") {
                result = result.filter(s => s.tags?.includes("theme") || s.skill_type === "voice_pack");
            } else if (themeFilter === "template") {
                result = result.filter(s => s.skill_type === "agent_template" || s.tags?.includes("template"));
            } else if (themeFilter === "feature") {
                result = result.filter(s => s.tags?.includes("feature") || s.skill_type === "prompt_template");
            }
        }
        return result;
    }, [skills, themeSearch, themeFilter]);

    // ==================== Enhanced SkillCard ====================
    const SkillCard = ({ skill, showInstall = true }: { skill: Skill; showInstall?: boolean }) => (
        <Card
            bodyStyle={{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column' }}
            className="hover:shadow-lg transition-all duration-300 h-full overflow-hidden group"
            style={{ borderRadius: 12 }}
        >
            {/* Banner Image */}
            <div
                className="relative h-36 overflow-hidden"
                style={{
                    background: skill.banner_url
                        ? `url(${skill.banner_url}) center/cover`
                        : `linear-gradient(135deg, ${
                            skill.category === 'entertainment' ? '#667eea, #764ba2' :
                            skill.category === 'health' ? '#e55d87, #5fc3e4' :
                            skill.category === 'home_automation' ? '#fc4a1a, #f7b733' :
                            skill.category === 'communication' ? '#4facfe, #00f2fe' :
                            '#667eea, #764ba2'
                          })`,
                }}
            >
                {/* Featured badge */}
                {skill.is_featured && (
                    <div className="absolute top-3 left-3">
                        <Tag color="amber" type="solid" size="small" style={{ borderRadius: 8 }}>
                            ⭐ Featured
                        </Tag>
                    </div>
                )}

                {/* Price badge */}
                <div className="absolute top-3 right-3">
                    {skill.is_premium && skill.price ? (
                        <Tag
                            color="green"
                            type="solid"
                            size="small"
                            style={{
                                borderRadius: 8,
                                fontWeight: 600,
                                backdropFilter: 'blur(4px)',
                            }}
                        >
                            <Crown className="h-3 w-3 mr-1 inline-block" />
                            {skill.price.toLocaleString()}đ
                        </Tag>
                    ) : (
                        <Tag
                            color="cyan"
                            type="solid"
                            size="small"
                            style={{ borderRadius: 8, backdropFilter: 'blur(4px)' }}
                        >
                            Miễn phí
                        </Tag>
                    )}
                </div>

                {/* Category tag */}
                <div className="absolute bottom-3 left-3">
                    <Tag type="ghost" size="small" style={{
                        background: 'rgba(255,255,255,0.9)',
                        borderRadius: 6,
                        color: '#333',
                        border: 'none',
                    }}>
                        {skill.category}
                    </Tag>
                </div>
            </div>

            {/* Content */}
            <div className="p-4 flex flex-col flex-1">
                <div className="flex items-center gap-3 mb-3">
                    {skill.icon_url ? (
                        <img
                            src={skill.icon_url}
                            alt={skill.name}
                            className="w-11 h-11 rounded-xl object-cover shadow-sm"
                            style={{ border: '2px solid #f0f0f0' }}
                        />
                    ) : (
                        <div className="w-11 h-11 rounded-xl flex items-center justify-center shadow-sm"
                             style={{
                                 background: 'linear-gradient(135deg, #667eea, #764ba2)',
                                 border: '2px solid #f0f0f0',
                             }}>
                            <Package className="h-5 w-5 text-white" />
                        </div>
                    )}
                    <div className="flex-1 min-w-0">
                        <Title heading={5} style={{ margin: 0 }} ellipsis={{ showTooltip: true }}>
                            {skill.name}
                        </Title>
                    </div>
                </div>

                <Paragraph ellipsis={{ rows: 2, showTooltip: true }} className="text-gray-500 mb-3 flex-1" style={{ fontSize: 13 }}>
                    {skill.short_description || skill.description}
                </Paragraph>

                {/* Tags */}
                <div className="flex flex-wrap gap-1 mb-3">
                    {skill.tags?.slice(0, 3).map((tag) => (
                        <Tag key={tag} type="ghost" size="small" style={{ borderRadius: 6, fontSize: 11 }}>
                            {tag}
                        </Tag>
                    ))}
                </div>

                {/* Author + Rating */}
                <div className="flex items-center justify-between text-sm text-gray-500 mb-3">
                    <span className="flex items-center gap-1">
                        By <span className="font-medium text-gray-700">{skill.author_name}</span>
                        {skill.author_verified && (
                            <ShieldCheck className="inline h-3.5 w-3.5 text-blue-500" />
                        )}
                    </span>
                    <div className="flex items-center gap-1">
                        <Rating allowClear={false} defaultValue={skill.rating} size="small" style={{ fontSize: 11 }} disabled />
                        <span className="font-medium">{skill.rating.toFixed(1)}</span>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex justify-between items-center pt-3 border-t border-gray-100 mt-auto">
                    <div className="flex items-center gap-3 text-sm text-gray-400">
                        <span className="flex items-center gap-1">
                            <Download className="h-3.5 w-3.5" />
                            {skill.install_count.toLocaleString()}
                        </span>
                        <span className="flex items-center gap-1">
                            <Eye className="h-3.5 w-3.5" />
                            {(skill as any).view_count?.toLocaleString?.() || 0}
                        </span>
                    </div>
                    {showInstall && (
                        isInstalled(skill.id) ? (
                            <Button type="secondary" size="small" onClick={() => handleUninstall(skill.id)}
                                    style={{ borderRadius: 8 }}>
                                Gỡ
                            </Button>
                        ) : (
                            <Button
                                theme="solid"
                                size="small"
                                onClick={() => handleInstall(skill.id)}
                                disabled={installingSkillId === skill.id}
                                style={{ borderRadius: 8 }}
                            >
                                {installingSkillId === skill.id ? "..." : t("install", "Cài đặt")}
                            </Button>
                        )
                    )}
                </div>
            </div>
        </Card>
    );

    // ==================== Skill Form Dialog ====================
    const SkillFormDialog = ({
        visible,
        onClose,
        onSubmit,
        initialValues,
        title,
    }: {
        visible: boolean;
        onClose: () => void;
        onSubmit: (values: Record<string, any>) => void;
        initialValues?: Record<string, any>;
        title: string;
    }) => (
        <Modal
            title={title}
            visible={visible}
            onCancel={onClose}
            footer={null}
            width={600}
            style={{ top: 40 }}
        >
            <Form
                onSubmit={onSubmit}
                labelPosition="top"
                initValues={initialValues || {
                    skill_type: "mcp_server",
                    category: "utilities",
                    is_public: true,
                    is_premium: false,
                    price: 0,
                }}
            >
                <div className="grid grid-cols-2 gap-4">
                    <Form.Input field="name" label="Tên Skill" rules={[{ required: true }]}
                                placeholder="Phát nhạc ZingMP3" />
                    <Form.Input field="slug" label="Slug" placeholder="phat-nhac-zingmp3"
                                helpText="Tự tạo từ tên nếu bỏ trống" />
                </div>
                <Form.TextArea field="description" label="Mô tả chi tiết" rows={3}
                               rules={[{ required: true }]} />
                <Form.Input field="short_description" label="Mô tả ngắn" maxLength={200}
                            placeholder="Nghe nhạc online qua ZingMP3" />

                <div className="grid grid-cols-2 gap-4">
                    <Form.Select field="skill_type" label="Loại"
                        optionList={[
                            { value: "mcp_server", label: "🔌 MCP Server" },
                            { value: "plugin", label: "🧩 Plugin" },
                            { value: "agent_template", label: "🤖 Agent Template" },
                            { value: "voice_pack", label: "🎤 Voice Pack" },
                            { value: "prompt_template", label: "📝 Prompt Template" },
                        ]}
                    />
                    <Form.Select field="category" label="Danh mục"
                        optionList={[
                            { value: "home_automation", label: "🏠 Nhà Thông Minh" },
                            { value: "entertainment", label: "🎵 Giải Trí" },
                            { value: "productivity", label: "📊 Năng Suất" },
                            { value: "information", label: "📰 Thông Tin" },
                            { value: "communication", label: "💬 Giao Tiếp" },

                            { value: "health", label: "🏥 Sức Khoẻ" },
                            { value: "utilities", label: "🔧 Tiện Ích" },
                        ]}
                    />
                </div>

                <Form.Input field="tags" label="Tags (phân cách bằng dấu phẩy)"
                            placeholder="music, streaming, entertainment" />

                <div className="grid grid-cols-2 gap-4">
                    <Form.Input field="icon_url" label="🖼️ URL Icon (w-10)"
                                placeholder="https://example.com/icon.png" />
                    <Form.Input field="banner_url" label="🎨 URL Banner (h-36)"
                                placeholder="https://example.com/banner.jpg" />
                </div>

                <Banner type="info" description="Hình banner sẽ hiển thị phía trên card. Kích thước lý tưởng: 400x200px. Icon: 80x80px." style={{ marginBottom: 12 }} />

                <div className="grid grid-cols-3 gap-4">
                    <Form.Switch field="is_premium" label="💎 Premium" />
                    <Form.InputNumber field="price" label="💰 Giá (VND)" min={0} />
                    <Form.Input field="version" label="Version" placeholder="1.0.0" />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <Form.Switch field="is_public" label="🌐 Công khai" />
                    <Form.Switch field="is_featured" label="⭐ Nổi bật" />
                </div>

                <div className="flex justify-end gap-2 mt-4 pt-4 border-t">
                    <Button onClick={onClose}>Huỷ</Button>
                    <Button htmlType="submit" theme="solid" type="primary">
                        {initialValues ? "Cập nhật" : "Tạo mới"}
                    </Button>
                </div>
            </Form>
        </Modal>
    );

    return (
        <>
            <PageHead
                title={t("skill_marketplace", "Skill Marketplace")}
                description="marketplace:page_description"
            />

            <div className="p-6 space-y-6">
                <Tabs type="line" activeKey={activeTab} onChange={(key) => {
                    setActiveTab(key);
                    if (key === "manage") fetchMySkills();
                }}>
                    <TabPane
                        tab={
                            <span>
                                <IconShoppingBag style={{ marginRight: 8 }} />
                                Browse
                            </span>
                        }
                        itemKey="browse"
                    >
                        <div className="pt-6 space-y-8">
                            {/* Filters & Search */}
                            <div className="flex flex-col md:flex-row gap-4 justify-between bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
                                <Input
                                    prefix={<IconSearch />}
                                    placeholder={t("search_skills", "Tìm kiếm skills...")}
                                    value={searchQuery}
                                    onChange={(val) => setSearchQuery(val)}
                                    style={{ width: 300, borderRadius: 10 }}
                                />
                                <div className="flex gap-2">
                                    <Select
                                        value={selectedCategory}
                                        onChange={(v) => setSelectedCategory(v as string)}
                                        style={{ width: 180 }}
                                        optionList={[
                                            { value: "all", label: t("all_categories", "Tất cả") },
                                            ...categories.map(c => ({ value: c.value, label: c.label }))
                                        ]}
                                    />
                                    <Select
                                        value={sortBy}
                                        onChange={(v) => setSortBy(v as any)}
                                        style={{ width: 150 }}
                                        optionList={[
                                            { value: "popular", label: "Phổ biến" },
                                            { value: "newest", label: "Mới nhất" },
                                            { value: "rating", label: "Đánh giá cao" }
                                        ]}
                                    />
                                </div>
                            </div>

                            {/* All Skills */}
                            <div className="space-y-4">
                                <Title heading={4}>
                                    {searchQuery
                                        ? `Kết quả cho "${searchQuery}"`
                                        : selectedCategory !== "all"
                                            ? categories.find((c) => c.value === selectedCategory)?.label || "Skills"
                                            : "Tất cả Skills"}
                                </Title>
                                {loading ? (
                                    <div className="flex items-center justify-center p-12">
                                        <Spin size="large" />
                                    </div>
                                ) : skills.length === 0 ? (
                                    <Empty
                                        image={<IconBox style={{ fontSize: 48 }} />}
                                        title="Không tìm thấy skill"
                                        description={searchQuery
                                            ? "Thử thay đổi từ khoá tìm kiếm"
                                            : "Hãy là người đầu tiên đăng skill!"}
                                    />
                                ) : (
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                                        {skills.map((skill) => (
                                            <SkillCard key={skill.id} skill={skill} />
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </TabPane>

                    <TabPane
                        tab={
                            <span>
                                <IconBox style={{ marginRight: 8 }} />
                                Đã cài ({installedSkills.length})
                            </span>
                        }
                        itemKey="installed"
                    >
                        <div className="pt-6">
                            {installedSkills.length === 0 ? (
                                <Empty
                                    image={<IconShoppingBag style={{ fontSize: 48 }} />}
                                    title="Chưa cài skill nào"
                                    description="Khám phá marketplace để tìm skills phù hợp."
                                >
                                    <Button onClick={() => setActiveTab("browse")}>
                                        Khám phá Marketplace
                                    </Button>
                                </Empty>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                    {installedSkills.map((installation) => (
                                        <Card key={installation.id} className="flex flex-col h-full" style={{ borderRadius: 12 }}>
                                            <div className="flex items-center gap-3 mb-4">
                                                {installation.skill_icon ? (
                                                    <img
                                                        src={installation.skill_icon}
                                                        alt={installation.skill_name}
                                                        className="w-10 h-10 rounded-xl object-cover"
                                                    />
                                                ) : (
                                                    <div className="w-10 h-10 rounded-xl flex items-center justify-center"
                                                         style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)' }}>
                                                        <Package className="h-5 w-5 text-white" />
                                                    </div>
                                                )}
                                                <div>
                                                    <Title heading={5} style={{ margin: 0 }}>{installation.skill_name}</Title>
                                                    <Text type="tertiary" size="small">v{installation.version_installed}</Text>
                                                </div>
                                            </div>

                                            <div className="flex items-center gap-2 mb-4 flex-1">
                                                <Tag color={installation.is_active ? "green" : "grey"} style={{ borderRadius: 6 }}>
                                                    {installation.is_active ? "Đang hoạt động" : "Đã tắt"}
                                                </Tag>
                                            </div>

                                            <div className="text-sm text-gray-500 mb-4 border-t pt-2">
                                                Cài ngày {new Date(installation.installed_at).toLocaleDateString("vi")}
                                            </div>

                                            <Button
                                                type="danger"
                                                theme="light"
                                                block
                                                style={{ borderRadius: 8 }}
                                                onClick={() => handleUninstall(installation.skill_id)}
                                            >
                                                Gỡ cài đặt
                                            </Button>
                                        </Card>
                                    ))}
                                </div>
                            )}
                        </div>
                    </TabPane>

                    {/* Templates/Themes Tab */}
                    <TabPane
                        tab={
                            <span>
                                <Store className="h-4 w-4 mr-2 inline-block" />
                                Templates & Themes
                            </span>
                        }
                        itemKey="items"
                    >
                        <div className="pt-6 space-y-6">
                            {/* Filters */}
                            <div className="flex flex-col md:flex-row gap-4 justify-between bg-white p-4 rounded-xl border border-gray-100 shadow-sm">
                                <Input
                                    prefix={<IconSearch />}
                                    placeholder="Tìm themes, templates, tính năng..."
                                    value={themeSearch}
                                    onChange={(val) => setThemeSearch(val)}
                                    style={{ width: 300, borderRadius: 10 }}
                                />
                                <Select
                                    value={themeFilter}
                                    onChange={(v) => setThemeFilter(v as string)}
                                    style={{ width: 200 }}
                                    optionList={[
                                        { value: "all", label: "Tất cả" },
                                        { value: "theme", label: "🎨 Themes" },
                                        { value: "template", label: "🤖 Templates" },
                                        { value: "feature", label: "⚡ Tính năng" },
                                    ]}
                                />
                            </div>

                            {/* Grid */}
                            {themeAndTemplateSkills.length === 0 ? (
                                <Empty
                                    image={<IconBox style={{ fontSize: 48 }} />}
                                    title="Chưa có item nào"
                                    description={themeSearch ? "Thử tìm kiếm khác" : "Marketplace đang được cập nhật."}
                                />
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                                    {themeAndTemplateSkills.map((skill) => (
                                        <SkillCard key={skill.id} skill={skill} />
                                    ))}
                                </div>
                            )}
                        </div>
                    </TabPane>

                    {/* ==================== Admin Management Tab ==================== */}
                    <TabPane
                        tab={
                            <span>
                                <IconSetting style={{ marginRight: 8 }} />
                                Quản lý Skills
                            </span>
                        }
                        itemKey="manage"
                    >
                        <div className="pt-6 space-y-6">
                            <div className="flex items-center justify-between">
                                <Title heading={4} style={{ margin: 0 }}>Quản lý Skills của tôi</Title>
                                <Button
                                    icon={<IconPlus />}
                                    theme="solid"
                                    style={{ borderRadius: 8 }}
                                    onClick={() => setShowCreateDialog(true)}
                                >
                                    Tạo Skill mới
                                </Button>
                            </div>

                            <Banner
                                type="info"
                                description="Tạo và quản lý skills trên Marketplace. Thêm hình banner, icon, định giá và publish cho người dùng cài đặt."
                            />

                            {adminLoading ? (
                                <div className="flex items-center justify-center p-12">
                                    <Spin size="large" />
                                </div>
                            ) : mySkills.length === 0 ? (
                                <Empty
                                    image={<IconBox style={{ fontSize: 48 }} />}
                                    title="Chưa có skill nào"
                                    description="Tạo skill đầu tiên để chia sẻ trên Marketplace!"
                                >
                                    <Button theme="solid" onClick={() => setShowCreateDialog(true)}>
                                        Tạo Skill
                                    </Button>
                                </Empty>
                            ) : (
                                <div className="space-y-4">
                                    {mySkills.map((skill) => (
                                        <Card key={skill.id} style={{ borderRadius: 12 }}>
                                            <div className="flex items-start gap-4">
                                                {/* Thumbnail */}
                                                <div className="w-20 h-20 rounded-xl overflow-hidden flex-shrink-0" style={{
                                                    background: skill.banner_url
                                                        ? `url(${skill.banner_url}) center/cover`
                                                        : 'linear-gradient(135deg, #667eea, #764ba2)',
                                                }}>
                                                    {skill.icon_url && (
                                                        <div className="w-full h-full flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.3)' }}>
                                                            <img src={skill.icon_url} alt="" className="w-10 h-10 rounded-lg" />
                                                        </div>
                                                    )}
                                                </div>

                                                {/* Info */}
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <Title heading={5} style={{ margin: 0 }}>{skill.name}</Title>
                                                        <Tag color={skill.is_public ? "green" : "grey"} size="small" style={{ borderRadius: 6 }}>
                                                            {skill.is_public ? "Công khai" : "Nháp"}
                                                        </Tag>
                                                        {skill.is_featured && (
                                                            <Tag color="amber" size="small" style={{ borderRadius: 6 }}>⭐ Featured</Tag>
                                                        )}
                                                        {skill.is_premium && (
                                                            <Tag color="violet" size="small" style={{ borderRadius: 6 }}>
                                                                💎 {skill.price?.toLocaleString()}đ
                                                            </Tag>
                                                        )}
                                                    </div>
                                                    <Text type="tertiary" size="small" ellipsis={{ showTooltip: true }} style={{ maxWidth: 500 }}>
                                                        {skill.short_description || skill.description}
                                                    </Text>
                                                    <div className="flex items-center gap-3 mt-2 text-sm text-gray-400">
                                                        <span>v{skill.version}</span>
                                                        <span>📥 {skill.install_count}</span>
                                                        <span>⭐ {skill.rating.toFixed(1)}</span>
                                                        <Tag size="small" style={{ borderRadius: 6 }}>{skill.category}</Tag>
                                                    </div>
                                                </div>

                                                {/* Actions */}
                                                <div className="flex items-center gap-2 flex-shrink-0">
                                                    <Button
                                                        icon={<IconEdit />}
                                                        theme="light"
                                                        style={{ borderRadius: 8 }}
                                                        onClick={() => setEditingSkill(skill)}
                                                    >
                                                        Sửa
                                                    </Button>
                                                    <Popconfirm
                                                        title="Xoá skill này?"
                                                        content="Thao tác này không thể hoàn tác."
                                                        onConfirm={() => handleDeleteSkill(skill.id)}
                                                    >
                                                        <Button
                                                            icon={<IconDelete />}
                                                            type="danger"
                                                            theme="light"
                                                            style={{ borderRadius: 8 }}
                                                        >
                                                            Xoá
                                                        </Button>
                                                    </Popconfirm>
                                                </div>
                                            </div>
                                        </Card>
                                    ))}
                                </div>
                            )}
                        </div>
                    </TabPane>
                </Tabs>
            </div>

            {/* Create Dialog */}
            <SkillFormDialog
                visible={showCreateDialog}
                onClose={() => setShowCreateDialog(false)}
                onSubmit={handleCreateSkill}
                title="🆕 Tạo Skill Mới"
            />

            {/* Edit Dialog */}
            {editingSkill && (
                <SkillFormDialog
                    visible={!!editingSkill}
                    onClose={() => setEditingSkill(null)}
                    onSubmit={handleUpdateSkill}
                    title={`✏️ Chỉnh sửa: ${editingSkill.name}`}
                    initialValues={{
                        ...editingSkill,
                        tags: editingSkill.tags?.join(", "),
                    }}
                />
            )}
        </>
    );
};
