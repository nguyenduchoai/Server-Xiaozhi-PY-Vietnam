import { useState, useEffect, useCallback } from "react";
import {
  Download,
  Plus,
  Search,
  Cpu,
  Monitor,
  Loader2,
  Star,
  Trash2,
  Edit,
  MoreVertical,
  FileBox,
  Smartphone,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/useAuth";
import { assetTemplateApi, type AssetTemplate, type BoardTypeInfo } from "@/services/assetTemplateService";
import { PageHead } from "@/components/PageHead";

const BOARD_TYPE_LABELS: Record<string, string> = {
  esp32: "ESP32",
  esp32s3: "ESP32-S3",
  esp32c3: "ESP32-C3",
  esp32c6: "ESP32-C6",
};

const SCREEN_TYPE_LABELS: Record<string, string> = {
  none: "Không màn hình",
  ssd1306_128x64: "OLED 128x64",
  ssd1306_128x32: "OLED 128x32",
  st7789_240x240: "LCD 240x240",
  st7789_240x320: "LCD 240x320",
  st7789_172x320: "LCD 172x320",
  ili9341_240x320: "ILI9341 240x320",
};

export function AssetTemplatesPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  const isAdmin = user?.is_superuser === true || user?.role === 'admin' || user?.role === 'super_admin';

  const [loading, setLoading] = useState(true);
  const [templates, setTemplates] = useState<AssetTemplate[]>([]);
  const [boardTypes, setBoardTypes] = useState<BoardTypeInfo | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedBoardType, setSelectedBoardType] = useState<string>("all");
  const [selectedScreenType, setSelectedScreenType] = useState<string>("all");

  // Dialog states
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<AssetTemplate | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    board_type: "esp32s3",
    screen_type: "none",
    screen_width: 0,
    screen_height: 0,
    wake_word: "",
    font_name: "",
    emoji_style: "",
    is_default: false,
  });
  const [assetFile, setAssetFile] = useState<File | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  const fetchTemplates = useCallback(async () => {
    try {
      setLoading(true);
      const [templatesRes, typesRes] = await Promise.all([
        assetTemplateApi.list({
          board_type: selectedBoardType !== "all" ? selectedBoardType : undefined,
          screen_type: selectedScreenType !== "all" ? selectedScreenType : undefined,
          search: searchQuery || undefined,
        }),
        assetTemplateApi.getBoardTypes(),
      ]);
      setTemplates(templatesRes.data);
      setBoardTypes(typesRes);
    } catch (error) {
      console.error("Failed to fetch templates:", error);
    } finally {
      setLoading(false);
    }
  }, [selectedBoardType, selectedScreenType, searchQuery]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleDownload = async (template: AssetTemplate) => {
    try {
      const blob = await assetTemplateApi.download(template.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `assets_${template.board_type}_${template.screen_width}x${template.screen_height}.bin`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast({
        title: "Thành công",
        description: "Đã tải xuống file assets.bin",
      });

      // Refresh to update download count
      fetchTemplates();
    } catch (error) {
      toast({
        title: "Lỗi",
        description: "Không thể tải file",
        variant: "destructive",
      });
    }
  };

  const handleCreateSubmit = async () => {
    if (!formData.name) {
      toast({ title: "Lỗi", description: "Vui lòng nhập tên mẫu", variant: "destructive" });
      return;
    }

    setIsSubmitting(true);
    try {
      // Read asset file as base64
      let assetFileBase64: string | undefined;
      if (assetFile) {
        assetFileBase64 = await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result as string);
          reader.readAsDataURL(assetFile);
        });
      }

      if (selectedTemplate) {
        // Update
        await assetTemplateApi.update(selectedTemplate.id, {
          ...formData,
          asset_file_base64: assetFileBase64,
          preview_image_base64: previewImage || undefined,
        });
        toast({ title: "Thành công", description: "Đã cập nhật mẫu" });
      } else {
        // Create
        await assetTemplateApi.create({
          ...formData,
          asset_file_base64: assetFileBase64,
          preview_image_base64: previewImage || undefined,
        });
        toast({ title: "Thành công", description: "Đã tạo mẫu mới" });
      }

      setShowCreateDialog(false);
      resetForm();
      fetchTemplates();
    } catch (error: any) {
      toast({
        title: "Lỗi",
        description: error?.response?.data?.detail || "Không thể lưu mẫu",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedTemplate) return;

    setIsSubmitting(true);
    try {
      await assetTemplateApi.delete(selectedTemplate.id);
      toast({ title: "Thành công", description: "Đã xóa mẫu" });
      setShowDeleteDialog(false);
      setSelectedTemplate(null);
      fetchTemplates();
    } catch (error) {
      toast({ title: "Lỗi", description: "Không thể xóa mẫu", variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      board_type: "esp32s3",
      screen_type: "none",
      screen_width: 0,
      screen_height: 0,
      wake_word: "",
      font_name: "",
      emoji_style: "",
      is_default: false,
    });
    setAssetFile(null);
    setPreviewImage(null);
    setSelectedTemplate(null);
  };

  const openEditDialog = (template: AssetTemplate) => {
    setSelectedTemplate(template);
    setFormData({
      name: template.name,
      description: template.description || "",
      board_type: template.board_type,
      screen_type: template.screen_type,
      screen_width: template.screen_width,
      screen_height: template.screen_height,
      wake_word: template.wake_word || "",
      font_name: template.font_name || "",
      emoji_style: template.emoji_style || "",
      is_default: template.is_default,
    });
    setPreviewImage(template.preview_image_base64);
    setShowCreateDialog(true);
  };

  const handleAssetFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith(".bin")) {
        toast({ title: "Lỗi", description: "Chỉ chấp nhận file .bin", variant: "destructive" });
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        toast({ title: "Lỗi", description: "File không được vượt quá 10MB", variant: "destructive" });
        return;
      }
      setAssetFile(file);
    }
  };

  const handlePreviewImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => setPreviewImage(reader.result as string);
      reader.readAsDataURL(file);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "N/A";
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(2)} MB`;
  };

  return (
    <div className="container mx-auto space-y-6 p-6">
      <PageHead title="Asset Templates" />

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <FileBox className="h-8 w-8" />
            Asset Templates
          </h1>
          <p className="text-muted-foreground">
            Mẫu giao diện thiết bị ESP32 - Chọn và tải xuống cho thiết bị của bạn
          </p>
        </div>
        {isAdmin && (
          <Button onClick={() => { resetForm(); setShowCreateDialog(true); }}>
            <Plus className="mr-2 h-4 w-4" />
            Tạo mẫu mới
          </Button>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col gap-4 sm:flex-row">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Tìm kiếm mẫu..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            <Select value={selectedBoardType} onValueChange={setSelectedBoardType}>
              <SelectTrigger className="w-[180px]">
                <Cpu className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Board type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tất cả board</SelectItem>
                {boardTypes?.board_types.map((bt) => (
                  <SelectItem key={bt.value} value={bt.value}>
                    {BOARD_TYPE_LABELS[bt.value] || bt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={selectedScreenType} onValueChange={setSelectedScreenType}>
              <SelectTrigger className="w-[200px]">
                <Monitor className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Screen type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tất cả màn hình</SelectItem>
                {boardTypes?.screen_types.map((st) => (
                  <SelectItem key={st.value} value={st.value}>
                    {SCREEN_TYPE_LABELS[st.value] || st.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Template Grid */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      ) : templates.length === 0 ? (
        <Card>
          <CardContent className="flex h-64 flex-col items-center justify-center text-muted-foreground">
            <FileBox className="mb-4 h-12 w-12" />
            <p>Không có mẫu nào</p>
            {isAdmin && (
              <Button className="mt-4" onClick={() => { resetForm(); setShowCreateDialog(true); }}>
                <Plus className="mr-2 h-4 w-4" />
                Tạo mẫu đầu tiên
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {templates.map((template) => (
            <Card key={template.id} className="overflow-hidden">
              <div className="relative aspect-video bg-muted">
                {template.preview_image_base64 ? (
                  <img
                    src={template.preview_image_base64}
                    alt={template.name}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center">
                    <Smartphone className="h-16 w-16 text-muted-foreground/50" />
                  </div>
                )}
                {template.is_default && (
                  <Badge className="absolute right-2 top-2 bg-yellow-500">
                    <Star className="mr-1 h-3 w-3" />
                    Mặc định
                  </Badge>
                )}
              </div>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-lg">{template.name}</CardTitle>
                  {isAdmin && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreVertical className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openEditDialog(template)}>
                          <Edit className="mr-2 h-4 w-4" />
                          Chỉnh sửa
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => {
                            setSelectedTemplate(template);
                            setShowDeleteDialog(true);
                          }}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Xóa
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
                {template.description && (
                  <CardDescription className="line-clamp-2">{template.description}</CardDescription>
                )}
              </CardHeader>
              <CardContent className="space-y-2 pb-2">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">
                    <Cpu className="mr-1 h-3 w-3" />
                    {BOARD_TYPE_LABELS[template.board_type] || template.board_type}
                  </Badge>
                  {template.screen_type !== "none" && (
                    <Badge variant="secondary">
                      <Monitor className="mr-1 h-3 w-3" />
                      {template.screen_width}x{template.screen_height}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>{formatFileSize(template.asset_file_size)}</span>
                  <span>{template.download_count} lượt tải</span>
                </div>
              </CardContent>
              <CardFooter>
                <Button
                  className="w-full"
                  onClick={() => handleDownload(template)}
                  disabled={!template.asset_file_size}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Tải xuống
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedTemplate ? "Chỉnh sửa mẫu" : "Tạo mẫu mới"}</DialogTitle>
            <DialogDescription>
              {selectedTemplate
                ? "Cập nhật thông tin mẫu asset"
                : "Tạo mẫu asset mới cho thiết bị ESP32"}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label htmlFor="name">Tên mẫu *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="VD: Xiaozhi Classic"
                />
              </div>

              <div className="col-span-2">
                <Label htmlFor="description">Mô tả</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Mô tả ngắn về mẫu này..."
                  rows={2}
                />
              </div>

              <div>
                <Label>Board Type *</Label>
                <Select
                  value={formData.board_type}
                  onValueChange={(v) => setFormData({ ...formData, board_type: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {boardTypes?.board_types.map((bt) => (
                      <SelectItem key={bt.value} value={bt.value}>
                        {BOARD_TYPE_LABELS[bt.value] || bt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Screen Type</Label>
                <Select
                  value={formData.screen_type}
                  onValueChange={(v) => setFormData({ ...formData, screen_type: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {boardTypes?.screen_types.map((st) => (
                      <SelectItem key={st.value} value={st.value}>
                        {SCREEN_TYPE_LABELS[st.value] || st.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="width">Screen Width</Label>
                <Input
                  id="width"
                  type="number"
                  value={formData.screen_width}
                  onChange={(e) => setFormData({ ...formData, screen_width: parseInt(e.target.value) || 0 })}
                />
              </div>

              <div>
                <Label htmlFor="height">Screen Height</Label>
                <Input
                  id="height"
                  type="number"
                  value={formData.screen_height}
                  onChange={(e) => setFormData({ ...formData, screen_height: parseInt(e.target.value) || 0 })}
                />
              </div>

              <div>
                <Label htmlFor="wake_word">Wake Word</Label>
                <Input
                  id="wake_word"
                  value={formData.wake_word}
                  onChange={(e) => setFormData({ ...formData, wake_word: e.target.value })}
                  placeholder="VD: xiaozhi"
                />
              </div>

              <div>
                <Label htmlFor="font">Font</Label>
                <Input
                  id="font"
                  value={formData.font_name}
                  onChange={(e) => setFormData({ ...formData, font_name: e.target.value })}
                  placeholder="VD: NotoSans"
                />
              </div>

              <div className="col-span-2">
                <Label htmlFor="asset_file">File Assets (.bin)</Label>
                <Input
                  id="asset_file"
                  type="file"
                  accept=".bin"
                  onChange={handleAssetFileChange}
                />
                {assetFile && (
                  <p className="mt-1 text-sm text-muted-foreground">
                    {assetFile.name} ({formatFileSize(assetFile.size)})
                  </p>
                )}
              </div>

              <div className="col-span-2">
                <Label htmlFor="preview">Ảnh preview</Label>
                <Input
                  id="preview"
                  type="file"
                  accept="image/*"
                  onChange={handlePreviewImageChange}
                />
                {previewImage && (
                  <img
                    src={previewImage}
                    alt="Preview"
                    className="mt-2 h-32 rounded-md object-cover"
                  />
                )}
              </div>

              <div className="col-span-2 flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={formData.is_default}
                  onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
                  className="h-4 w-4"
                />
                <Label htmlFor="is_default" className="cursor-pointer">
                  Đặt làm mẫu mặc định cho board type này
                </Label>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Hủy
            </Button>
            <Button onClick={handleCreateSubmit} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {selectedTemplate ? "Cập nhật" : "Tạo mới"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xác nhận xóa</AlertDialogTitle>
            <AlertDialogDescription>
              Bạn có chắc muốn xóa mẫu "{selectedTemplate?.name}"? Hành động này không thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Hủy</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Xóa
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

export default AssetTemplatesPage;
