

import { Card, Table, Tag, Typography, Empty } from '@douyinfe/semi-ui';
import { IconWifi, IconUnlink, IconServer, IconClock } from '@douyinfe/semi-icons';
import { formatDistanceToNow } from "date-fns";
import { vi } from "date-fns/locale";
import type { DeviceStatus } from "@/services/analyticsService";
import type { ColumnProps } from '@douyinfe/semi-ui/lib/es/table';

const { Text } = Typography;

interface DeviceStatusListProps {
    devices: DeviceStatus[];
    loading?: boolean;
}

export function DeviceStatusList({ devices, loading }: DeviceStatusListProps) {
    const columns: ColumnProps<DeviceStatus>[] = [
        {
            title: 'Tên thiết bị',
            dataIndex: 'name',
            render: (text, record) => (
                <div className="flex items-center gap-2">
                    <IconServer style={{ color: 'var(--semi-color-text-2)' }} />
                    <div>
                        <Text strong style={{ display: 'block' }}>{text}</Text>
                        <Text size="small" type="tertiary">{record.mac_address}</Text>
                    </div>
                </div>
            )
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            render: (status) => {
                if (status === 'online') {
                    return (
                        <Tag color="green" prefixIcon={<IconWifi />}>
                            Online
                        </Tag>
                    );
                } else if (status === 'available') {
                    return (
                        <Tag color="blue" prefixIcon={<IconWifi />}>
                            Available
                        </Tag>
                    );
                } else {
                    return (
                        <Tag color="red" prefixIcon={<IconUnlink />}>
                            Offline
                        </Tag>
                    );
                }
            }
        },
        {
            title: 'Hoạt động cuối',
            dataIndex: 'last_seen',
            render: (lastSeen) => (
                <div className="flex items-center gap-1 text-gray-500">
                    <IconClock />
                    {lastSeen ? formatDistanceToNow(new Date(lastSeen), {
                        addSuffix: true,
                        locale: vi
                    }) : "Chưa bao giờ"}
                </div>
            )
        }
    ];

    return (
        <Card
            title={
                <div className="flex justify-between items-center w-full">
                    <Text strong style={{ fontSize: '18px' }} className="mb-4 block">Trạng thái thiết bị</Text>
                    <Tag>{devices.length}</Tag>
                </div>
            }
            headerExtraContent={
                <Text type="tertiary" size="small">Real-time status</Text>
            }
            loading={loading}
            bodyStyle={{ padding: 0 }}
        >
            <Table
                columns={columns}
                dataSource={devices}
                pagination={{ pageSize: 5 }}
                empty={<Empty image={<IconServer style={{ fontSize: 48, color: 'var(--semi-color-text-2)' }} />} description="Chưa có thiết bị kết nối" />}
            />
        </Card>
    );
}
