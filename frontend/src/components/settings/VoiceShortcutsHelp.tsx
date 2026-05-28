/**
 * VoiceShortcutsHelp - Semi Design implementation
 */

import { Card, Typography, Table } from "@douyinfe/semi-ui";
import { Zap } from "lucide-react";

const { Title, Text } = Typography;

export function VoiceShortcutsHelp() {
    const shortcuts = [
        { command: "Dừng / Dừng lại / Ngừng / Tắt", action: "Dừng ngay lập tức TTS hoặc nhạc đang phát" },
        { command: "Im đi", action: "Dừng im lặng (không phản hồi lại)" },
        { command: "To hơn / Lớn hơn / Tăng âm lượng", action: "Tăng âm lượng thiết bị (+10%)" },
        { command: "Nhỏ hơn / Bé hơn / Giảm âm lượng", action: "Giảm âm lượng thiết bị (-10%)" },
        { command: "Cảm ơn / Cám ơn", action: "Phản hồi nhanh: 'Không có gì ạ!'" },
        { command: "OK / Được rồi", action: "Phản hồi nhanh: 'Vâng ạ'" },
        { command: "Bạn còn đó không / Bạn ơi", action: "Kiểm tra trạng thái: 'Tôi nghe đây ạ'" },
    ];

    const columns = [
        {
            title: "Lệnh (Nói gì)",
            dataIndex: "command",
            width: "40%",
            render: (text: string) => <Text strong>{text}</Text>,
        },
        {
            title: "Hành động",
            dataIndex: "action",
        },
    ];

    return (
        <Card
            title={
                <div className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-yellow-500" />
                    <Title heading={5} className="!mb-0">Lệnh tắt giọng nói (Voice Shortcuts)</Title>
                </div>
            }
        >
            <Text type="tertiary" className="block mb-4">
                Các lệnh này được xử lý ngay lập tức trên server mà không cần qua AI, giúp phản hồi cực nhanh.
            </Text>
            <Table
                columns={columns}
                dataSource={shortcuts}
                pagination={false}
                size="small"
            />
        </Card>
    );
}
