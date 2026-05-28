/**
 * Notifications Page
 * Allows users to send notifications/TTS to their devices
 */
import { useTranslation } from "react-i18next";
import { NotificationTester } from "@/components/settings/NotificationTester";
import { PageHead } from "@/components";
import { Card, Typography } from "@douyinfe/semi-ui";
import { Mic, Volume2, Send, Radio } from "lucide-react";

const { Title, Text } = Typography;

// Voice Shortcuts data
const voiceShortcuts = [
    { command: "Dừng / Dừng lại / Ngừng / Tắt", action: "Dừng ngay lập tức TTS hoặc nhạc đang phát" },
    { command: "Im đi", action: "Dừng im lặng (không phản hồi lại)" },
    { command: "To hơn / Lớn hơn / Tăng âm lượng", action: "Tăng âm lượng thiết bị (+10%)" },
    { command: "Nhỏ hơn / Bé hơn / Giảm âm lượng", action: "Giảm âm lượng thiết bị (-10%)" },
    { command: "Cảm ơn / Cám ơn", action: "Phản hồi nhanh: 'Không có gì ạ!'" },
    { command: "OK / Được rồi", action: "Phản hồi nhanh: 'Vâng ạ!'" },
    { command: "Bạn còn đó không / Bạn ơi", action: "Kiểm tra trạng thái: 'Tôi nghe đây ạ'" },
];

export default function NotificationsPage() {
    const { t } = useTranslation(["settings", "common"]);

    return (
        <div className="space-y-6">
            <PageHead
                title={t("notifications.title", "Gửi Thông Báo")}
                description={t("notifications.description", "Gửi thông báo và phát TTS trực tiếp tới các thiết bị")}
            />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left: Notification Tester */}
                <NotificationTester />

                {/* Right: Voice Shortcuts Info */}
                <Card className="h-fit">
                    <div className="p-6">
                        <div className="flex items-center gap-2 mb-4">
                            <Mic className="h-5 w-5 text-purple-500" />
                            <Title heading={5} className="!m-0">Lệnh tắt giọng nói (Voice Shortcuts)</Title>
                        </div>
                        <Text type="tertiary" className="block mb-4">
                            Các lệnh này được xử lý ngay lập tức trên server mà không cần qua AI, giúp phản hồi cực nhanh.
                        </Text>

                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b">
                                        <th className="text-left py-2 px-2 font-medium">Lệnh (Nói gì)</th>
                                        <th className="text-left py-2 px-2 font-medium">Hành động</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {voiceShortcuts.map((shortcut, idx) => (
                                        <tr key={idx} className="border-b last:border-0">
                                            <td className="py-2 px-2 text-blue-600 font-medium">{shortcut.command}</td>
                                            <td className="py-2 px-2 text-gray-600">{shortcut.action}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Tips Section */}
            <Card className="bg-gradient-to-r from-blue-50 to-purple-50 border-blue-200">
                <div className="p-6">
                    <div className="flex items-center gap-2 mb-4">
                        <Radio className="h-5 w-5 text-blue-500" />
                        <Title heading={5} className="!m-0">Mẹo sử dụng Thông báo</Title>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="flex items-start gap-3">
                            <div className="p-2 rounded-lg bg-blue-100">
                                <Send className="h-4 w-4 text-blue-600" />
                            </div>
                            <div>
                                <Text strong>Gửi cho một thiết bị</Text>
                                <Text type="tertiary" className="block text-sm">Chọn thiết bị cụ thể từ dropdown để gửi thông báo riêng</Text>
                            </div>
                        </div>

                        <div className="flex items-start gap-3">
                            <div className="p-2 rounded-lg bg-purple-100">
                                <Volume2 className="h-4 w-4 text-purple-600" />
                            </div>
                            <div>
                                <Text strong>Phát TTS</Text>
                                <Text type="tertiary" className="block text-sm">Bật "Phát âm thanh" để thiết bị đọc to nội dung thông báo</Text>
                            </div>
                        </div>

                        <div className="flex items-start gap-3">
                            <div className="p-2 rounded-lg bg-green-100">
                                <Radio className="h-4 w-4 text-green-600" />
                            </div>
                            <div>
                                <Text strong>Broadcast</Text>
                                <Text type="tertiary" className="block text-sm">Chọn "Tất cả thiết bị online" để gửi đồng thời tới tất cả</Text>
                            </div>
                        </div>
                    </div>
                </div>
            </Card>
        </div>
    );
}
