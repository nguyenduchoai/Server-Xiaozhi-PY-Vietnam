import { toast } from "sonner";
/**
 * Admin Hardware Types Management Page
 * 
 * Allows admins to manage Board Types and Screen Types used across:
 * - Device Registration
 * - Asset Templates
 * - Firmware OTA
 */

import { useState, useEffect, useCallback } from "react";
import {
  Button,
  Card,
  Table,
  Tabs,
  TabPane,
  Input,
  TextArea,
  Switch,
  Tag,
  Modal,
  
  Typography,
  Dropdown,
  Popconfirm
} from "@douyinfe/semi-ui";
import {
  IconPlus,
  IconEdit,
  IconDelete,
  IconMore,
  IconDesktop,
  IconMonitorStroked,
  IconServer
} from "@douyinfe/semi-icons";
import { PageHead } from "@/components/PageHead";
import {
  hardwareTypesApi,
  type BoardType,
  type ScreenType,
  type BoardTypeCreate,
  type ScreenTypeCreate,
} from "@/services/hardwareTypesService";

const { Text, Title } = Typography;

export function AdminHardwareTypesPage() {
  const [loading, setLoading] = useState(true);
  const [boardTypes, setBoardTypes] = useState<BoardType[]>([]);
  const [screenTypes, setScreenTypes] = useState<ScreenType[]>([]);
  const [activeTab, setActiveTab] = useState("boards");

  // Dialog states
  const [showBoardDialog, setShowBoardDialog] = useState(false);
  const [showScreenDialog, setShowScreenDialog] = useState(false);
  const [editingBoard, setEditingBoard] = useState<BoardType | null>(null);
  const [editingScreen, setEditingScreen] = useState<ScreenType | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Board form state
  const [boardForm, setBoardForm] = useState<BoardTypeCreate>({
    code: "",
    name: "",
    description: "",
    chip_family: "ESP32",
    flash_size_mb: 4,
    psram_size_mb: 0,
    is_active: true,
    sort_order: 0,
  });

  // Screen form state
  const [screenForm, setScreenForm] = useState<ScreenTypeCreate>({
    code: "",
    name: "",
    description: "",
    driver: "none",
    width: 0,
    height: 0,
    color_depth: 1,
    is_active: true,
    sort_order: 0,
  });

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await hardwareTypesApi.getAll(false);
      setBoardTypes(data.board_types);
      setScreenTypes(data.screen_types);
    } catch (error) {
      console.error("Failed to fetch hardware types:", error);
      toast.error("Không thể tải dữ liệu");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSeedDefaults = async () => {
    try {
      setIsSubmitting(true);
      const result = await hardwareTypesApi.seedDefaults();
      toast.success(`Đã tạo ${result.boards_created} board types và ${result.screens_created} screen types`);
      fetchData();
    } catch (error) {
      console.error("Failed to seed defaults:", error);
      toast.error("Không thể tạo dữ liệu mặc định");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Board handlers
  const openBoardDialog = (board?: BoardType) => {
    if (board) {
      setEditingBoard(board);
      setBoardForm({
        code: board.code,
        name: board.name,
        description: board.description || "",
        chip_family: board.chip_family,
        flash_size_mb: board.flash_size_mb,
        psram_size_mb: board.psram_size_mb,
        is_active: board.is_active,
        sort_order: board.sort_order,
      });
    } else {
      setEditingBoard(null);
      setBoardForm({
        code: "",
        name: "",
        description: "",
        chip_family: "ESP32",
        flash_size_mb: 4,
        psram_size_mb: 0,
        is_active: true,
        sort_order: boardTypes.length,
      });
    }
    setShowBoardDialog(true);
  };

  const handleSaveBoard = async () => {
    try {
      setIsSubmitting(true);
      if (editingBoard) {
        await hardwareTypesApi.updateBoardType(editingBoard.id, boardForm);
        toast.success("Đã cập nhật board type");
      } else {
        await hardwareTypesApi.createBoardType(boardForm);
        toast.success("Đã tạo board type mới");
      }
      setShowBoardDialog(false);
      fetchData();
    } catch (error) {
      console.error("Failed to save board type:", error);
      toast.error("Không thể lưu board type");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Screen handlers
  const openScreenDialog = (screen?: ScreenType) => {
    if (screen) {
      setEditingScreen(screen);
      setScreenForm({
        code: screen.code,
        name: screen.name,
        description: screen.description || "",
        driver: screen.driver,
        width: screen.width,
        height: screen.height,
        color_depth: screen.color_depth,
        is_active: screen.is_active,
        sort_order: screen.sort_order,
      });
    } else {
      setEditingScreen(null);
      setScreenForm({
        code: "",
        name: "",
        description: "",
        driver: "none",
        width: 0,
        height: 0,
        color_depth: 1,
        is_active: true,
        sort_order: screenTypes.length,
      });
    }
    setShowScreenDialog(true);
  };

  const handleSaveScreen = async () => {
    try {
      setIsSubmitting(true);
      if (editingScreen) {
        await hardwareTypesApi.updateScreenType(editingScreen.id, screenForm);
        toast.success("Đã cập nhật screen type");
      } else {
        await hardwareTypesApi.createScreenType(screenForm);
        toast.success("Đã tạo screen type mới");
      }
      setShowScreenDialog(false);
      fetchData();
    } catch (error) {
      console.error("Failed to save screen type:", error);
      toast.error("Không thể lưu screen type");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete handlers
  const handleDeleteBoard = async (id: number) => {
    try {
      await hardwareTypesApi.deleteBoardType(id);
      toast.success("Đã xóa board type");
      fetchData();
    } catch (error) {
      console.error("Failed to delete board:", error);
      toast.error("Không thể xóa");
    }
  };

  const handleDeleteScreen = async (id: number) => {
    try {
      await hardwareTypesApi.deleteScreenType(id);
      toast.success("Đã xóa screen type");
      fetchData();
    } catch (error) {
      console.error("Failed to delete screen:", error);
      toast.error("Không thể xóa");
    }
  };

  const boardColumns = [
    {
      title: 'Code',
      dataIndex: 'code',
      render: (text: string) => <Text style={{ fontFamily: 'monospace' }}>{text}</Text>
    },
    {
      title: 'Tên',
      dataIndex: 'name',
    },
    {
      title: 'Chip Family',
      dataIndex: 'chip_family',
    },
    {
      title: 'Flash',
      dataIndex: 'flash_size_mb',
      render: (v: number) => `${v} MB`
    },
    {
      title: 'PSRAM',
      dataIndex: 'psram_size_mb',
      render: (v: number) => `${v} MB`
    },
    {
      title: 'Trạng thái',
      dataIndex: 'is_active',
      render: (active: boolean) => <Tag color={active ? "green" : "red"}>{active ? "Active" : "Inactive"}</Tag>
    },
    {
      title: 'Thao tác',
      key: 'actions',
      render: (_: any, record: BoardType) => (
        <Dropdown
          trigger="click"
          position="bottomRight"
          render={
            <Dropdown.Menu>
              <Dropdown.Item onClick={() => openBoardDialog(record)} icon={<IconEdit />}>
                Chỉnh sửa
              </Dropdown.Item>
              <Popconfirm
                title="Xác nhận xóa"
                onConfirm={() => handleDeleteBoard(record.id)}
              >
                <Dropdown.Item type="danger" icon={<IconDelete />}>
                  Xóa
                </Dropdown.Item>
              </Popconfirm>
            </Dropdown.Menu>
          }
        >
          <Button icon={<IconMore />} theme="borderless" />
        </Dropdown>
      )
    }
  ];

  const screenColumns = [
    {
      title: 'Code',
      dataIndex: 'code',
      render: (text: string) => <Text style={{ fontFamily: 'monospace' }}>{text}</Text>
    },
    {
      title: 'Tên',
      dataIndex: 'name',
    },
    {
      title: 'Driver',
      dataIndex: 'driver',
    },
    {
      title: 'Độ phân giải',
      key: 'res',
      render: (_: any, r: ScreenType) => r.width > 0 ? `${r.width}x${r.height}` : "-"
    },
    {
      title: 'Color',
      dataIndex: 'color_depth',
      render: (v: number) => v === 1 ? "Mono" : `${v}-bit`
    },
    {
      title: 'Trạng thái',
      dataIndex: 'is_active',
      render: (active: boolean) => <Tag color={active ? "green" : "red"}>{active ? "Active" : "Inactive"}</Tag>
    },
    {
      title: 'Thao tác',
      key: 'actions',
      render: (_: any, record: ScreenType) => (
        <Dropdown
          trigger="click"
          position="bottomRight"
          render={
            <Dropdown.Menu>
              <Dropdown.Item onClick={() => openScreenDialog(record)} icon={<IconEdit />}>
                Chỉnh sửa
              </Dropdown.Item>
              <Popconfirm
                title="Xác nhận xóa"
                onConfirm={() => handleDeleteScreen(record.id)}
              >
                <Dropdown.Item type="danger" icon={<IconDelete />}>
                  Xóa
                </Dropdown.Item>
              </Popconfirm>
            </Dropdown.Menu>
          }
        >
          <Button icon={<IconMore />} theme="borderless" />
        </Dropdown>
      )
    }
  ];

  return (
    <>
      <div className="container mx-auto py-6 space-y-6">
        <PageHead title="Quản lý Hardware Types" />

        <div className="flex items-center justify-between">
          <div>
            <Title heading={3} style={{ margin: 0 }}>Quản lý Hardware Types</Title>
            <Text type="secondary">
              Quản lý các loại board và màn hình cho thiết bị ESP32
            </Text>
          </div>
          <Button onClick={handleSeedDefaults} loading={isSubmitting} icon={<IconServer />} theme="light">
            Tạo dữ liệu mặc định
          </Button>
        </div>

        <Tabs
          type="card"
          activeKey={activeTab}
          onChange={(k) => setActiveTab(k as string)}
          tabBarExtraContent={
            activeTab === "boards" ? (
              <Button onClick={() => openBoardDialog()} icon={<IconPlus />} theme="solid">Thêm Board</Button>
            ) : (
              <Button onClick={() => openScreenDialog()} icon={<IconPlus />} theme="solid">Thêm Screen</Button>
            )
          }
        >
          <TabPane
            itemKey="boards"
            tab={
              <span><IconDesktop style={{ marginRight: 8 }} /> Board Types ({boardTypes.length})</span>
            }
          >
            <Card bodyStyle={{ padding: 0 }}>
              <Table
                columns={boardColumns}
                dataSource={boardTypes}
                pagination={{ pageSize: 10 }}
                loading={loading}
                empty={<div className="p-8 text-center text-gray-500">Chưa có board type nào</div>}
              />
            </Card>
          </TabPane>
          <TabPane
            itemKey="screens"
            tab={
              <span><IconMonitorStroked style={{ marginRight: 8 }} /> Screen Types ({screenTypes.length})</span>
            }
          >
            <Card bodyStyle={{ padding: 0 }}>
              <Table
                columns={screenColumns}
                dataSource={screenTypes}
                pagination={{ pageSize: 10 }}
                loading={loading}
                empty={<div className="p-8 text-center text-gray-500">Chưa có screen type nào</div>}
              />
            </Card>
          </TabPane>
        </Tabs>

        {/* Board Dialog */}
        <Modal
          visible={showBoardDialog}
          onCancel={() => {
            setShowBoardDialog(false);
            setEditingBoard(null);
            setBoardForm({ code: "", name: "", description: "", chip_family: "ESP32", flash_size_mb: 4, psram_size_mb: 0, is_active: true, sort_order: 0 });
          }}
          title={editingBoard ? "Chỉnh sửa Board Type" : "Thêm Board Type"}
          onOk={handleSaveBoard}
          confirmLoading={isSubmitting}
          okText={editingBoard ? "Cập nhật" : "Tạo mới"}
          cancelText="Hủy"
          okButtonProps={{ disabled: !boardForm.code || !boardForm.name }}
          width={600}
          centered
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Code *</Text>
                <Input
                  placeholder="esp32s3"
                  value={boardForm.code}
                  onChange={(v) => setBoardForm({ ...boardForm, code: v })}
                />
              </div>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Tên *</Text>
                <Input
                  placeholder="ESP32-S3"
                  value={boardForm.name}
                  onChange={(v) => setBoardForm({ ...boardForm, name: v })}
                />
              </div>
            </div>

            <div>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>Mô tả</Text>
              <TextArea
                placeholder="Mô tả về board..."
                value={boardForm.description}
                onChange={(v) => setBoardForm({ ...boardForm, description: v })}
                rows={2}
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Chip Family</Text>
                <Input
                  placeholder="ESP32-S3"
                  value={boardForm.chip_family}
                  onChange={(v) => setBoardForm({ ...boardForm, chip_family: v })}
                />
              </div>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Flash (MB)</Text>
                <Input
                  type="number"
                  min={1}
                  max={32}
                  value={boardForm.flash_size_mb}
                  onChange={(v) => setBoardForm({ ...boardForm, flash_size_mb: Number(v) })}
                />
              </div>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>PSRAM (MB)</Text>
                <Input
                  type="number"
                  min={0}
                  max={16}
                  value={boardForm.psram_size_mb}
                  onChange={(v) => setBoardForm({ ...boardForm, psram_size_mb: Number(v) })}
                />
              </div>
            </div>

            <div className="flex items-center justify-between border-t pt-4">
              <div className="flex items-center gap-2">
                <Text strong>Kích hoạt</Text>
                <Switch
                  checked={boardForm.is_active}
                  onChange={(checked) => setBoardForm({ ...boardForm, is_active: checked })}
                />
              </div>
              <div className="flex items-center gap-2">
                <Text strong>Thứ tự:</Text>
                <Input
                  type="number"
                  style={{ width: 80 }}
                  value={boardForm.sort_order}
                  onChange={(v) => setBoardForm({ ...boardForm, sort_order: Number(v) })}
                />
              </div>
            </div>
          </div>
        </Modal>

        {/* Screen Dialog */}
        <Modal
          visible={showScreenDialog}
          onCancel={() => {
            setShowScreenDialog(false);
            setEditingScreen(null);
            setScreenForm({ code: "", name: "", description: "", driver: "none", width: 0, height: 0, color_depth: 1, is_active: true, sort_order: 0 });
          }}
          title={editingScreen ? "Chỉnh sửa Screen Type" : "Thêm Screen Type"}
          onOk={handleSaveScreen}
          confirmLoading={isSubmitting}
          okText={editingScreen ? "Cập nhật" : "Tạo mới"}
          cancelText="Hủy"
          okButtonProps={{ disabled: !screenForm.code || !screenForm.name }}
          width={600}
          centered
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Code *</Text>
                <Input
                  placeholder="ssd1306_128x64"
                  value={screenForm.code}
                  onChange={(v) => setScreenForm({ ...screenForm, code: v })}
                />
              </div>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Tên *</Text>
                <Input
                  placeholder="OLED 128x64"
                  value={screenForm.name}
                  onChange={(v) => setScreenForm({ ...screenForm, name: v })}
                />
              </div>
            </div>

            <div>
              <Text strong style={{ display: 'block', marginBottom: 4 }}>Mô tả</Text>
              <TextArea
                placeholder="Mô tả về màn hình..."
                value={screenForm.description}
                onChange={(v) => setScreenForm({ ...screenForm, description: v })}
                rows={2}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Driver</Text>
                <Input
                  placeholder="ssd1306"
                  value={screenForm.driver}
                  onChange={(v) => setScreenForm({ ...screenForm, driver: v })}
                />
              </div>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Color Depth (bits)</Text>
                <Input
                  type="number"
                  min={1}
                  max={32}
                  value={screenForm.color_depth}
                  onChange={(v) => setScreenForm({ ...screenForm, color_depth: Number(v) })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Width (px)</Text>
                <Input
                  type="number"
                  min={0}
                  max={2048}
                  value={screenForm.width}
                  onChange={(v) => setScreenForm({ ...screenForm, width: Number(v) })}
                />
              </div>
              <div>
                <Text strong style={{ display: 'block', marginBottom: 4 }}>Height (px)</Text>
                <Input
                  type="number"
                  min={0}
                  max={2048}
                  value={screenForm.height}
                  onChange={(v) => setScreenForm({ ...screenForm, height: Number(v) })}
                />
              </div>
            </div>

            <div className="flex items-center justify-between border-t pt-4">
              <div className="flex items-center gap-2">
                <Text strong>Kích hoạt</Text>
                <Switch
                  checked={screenForm.is_active}
                  onChange={(checked) => setScreenForm({ ...screenForm, is_active: checked })}
                />
              </div>
              <div className="flex items-center gap-2">
                <Text strong>Thứ tự:</Text>
                <Input
                  type="number"
                  style={{ width: 80 }}
                  value={screenForm.sort_order}
                  onChange={(v) => setScreenForm({ ...screenForm, sort_order: Number(v) })}
                />
              </div>
            </div>
          </div>
        </Modal>
      </div>
    </>
  );
}

export default AdminHardwareTypesPage;
