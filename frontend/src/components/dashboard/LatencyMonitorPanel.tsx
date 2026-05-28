/**
 * LatencyMonitorPanel — Real-time AI pipeline latency visualization
 * Polls /analytics/latency every 5s and shows gauges + recent conversations
 */

import { useEffect, useState, useCallback } from "react";
import { Banner, Card, Typography, Empty, Spin } from "@douyinfe/semi-ui";
import { apiClient } from "@/config/axios-instance";
import { API_ENDPOINTS } from "@/lib/api/endpoints";

const { Text } = Typography;

interface LatencyStats {
  count: number;
  avg_asr_ms: number;
  avg_llm_ms: number;
  avg_tts_ms: number;
  avg_e2e_ms: number;
  p95_e2e_ms: number;
  active_sessions: number;
  recent: Array<{
    time: number;
    agent: string;
    text: string;
    asr_ms: number;
    llm_ms: number;
    tts_ms: number;
    e2e_ms: number;
  }>;
}

// Latency gauge bar component
function LatencyGauge({
  label,
  value,
  maxValue,
  color,
  unit = "ms",
}: {
  label: string;
  value: number;
  maxValue: number;
  color: string;
  unit?: string;
}) {
  const percent = Math.min((value / maxValue) * 100, 100);
  const status =
    value === 0
      ? "idle"
      : value < maxValue * 0.4
        ? "good"
        : value < maxValue * 0.7
          ? "warn"
          : "slow";
  const statusColors: Record<string, string> = {
    idle: "var(--semi-color-text-3)",
    good: "#10B981",
    warn: "#F59E0B",
    slow: "#EF4444",
  };

  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 6,
        }}
      >
        <Text size="small" style={{ fontWeight: 500 }}>
          {label}
        </Text>
        <Text
          size="small"
          style={{ fontWeight: 600, color: statusColors[status] }}
        >
          {value > 0 ? `${value}${unit}` : "—"}
        </Text>
      </div>
      <div
        style={{
          height: 8,
          borderRadius: 4,
          background: "var(--semi-color-fill-0)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${percent}%`,
            borderRadius: 4,
            background: `linear-gradient(90deg, ${color}, ${color}CC)`,
            transition: "width 0.6s cubic-bezier(0.16, 1, 0.3, 1)",
            boxShadow: value > 0 ? `0 0 12px ${color}40` : "none",
          }}
        />
      </div>
    </div>
  );
}

// Recent conversation item
function ConversationItem({
  item,
}: {
  item: LatencyStats["recent"][0];
}) {
  const timeStr = new Date(item.time * 1000).toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        padding: "10px 0",
        borderBottom: "1px solid var(--semi-color-border)",
      }}
    >
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background:
            item.e2e_ms < 2000
              ? "#10B981"
              : item.e2e_ms < 4000
                ? "#F59E0B"
                : "#EF4444",
          marginTop: 6,
          flexShrink: 0,
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 8,
          }}
        >
          <Text
            size="small"
            ellipsis={{ showTooltip: true }}
            style={{
              flex: 1,
              fontWeight: 500,
            }}
          >
            {item.text || "..."}
          </Text>
          <Text
            size="small"
            type="tertiary"
            style={{ flexShrink: 0 }}
          >
            {timeStr}
          </Text>
        </div>
        <div
          style={{
            display: "flex",
            gap: 12,
            marginTop: 4,
          }}
        >
          {item.agent && (
            <Text size="small" type="tertiary">
              🤖 {item.agent}
            </Text>
          )}
          <Text size="small" style={{ color: "#3B82F6" }}>
            ASR {item.asr_ms}ms
          </Text>
          <Text size="small" style={{ color: "#8B5CF6" }}>
            LLM {item.llm_ms}ms
          </Text>
          <Text size="small" style={{ color: "#EC4899" }}>
            TTS {item.tts_ms}ms
          </Text>
        </div>
      </div>
    </div>
  );
}

export function LatencyMonitorPanel() {
  const [stats, setStats] = useState<LatencyStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLatency = useCallback(async () => {
    try {
      const response = await apiClient.get(API_ENDPOINTS.ANALYTICS.LATENCY);
      setStats(response.data);
      setError(null);
    } catch (err) {
      console.error("Latency analytics fetch error:", err);
      setError("Không tải được dữ liệu latency từ server.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLatency();
    const interval = setInterval(fetchLatency, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, [fetchLatency]);

  if (loading) {
    return (
      <Card
        style={{ borderRadius: 16 }}
        bodyStyle={{
          display: "flex",
          justifyContent: "center",
          padding: 40,
        }}
      >
        <Spin size="large" />
      </Card>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: 16,
      }}
    >
      {/* Latency Gauges */}
      <Card
        title={
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 8,
                background: "linear-gradient(135deg, #6366F1, #8B5CF6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                fontSize: 14,
              }}
            >
              ⚡
            </div>
            <span>AI Pipeline Latency</span>
            {stats && stats.active_sessions > 0 && (
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  padding: "2px 8px",
                  borderRadius: 12,
                  fontSize: 11,
                  fontWeight: 600,
                  background: "rgba(16, 185, 129, 0.1)",
                  color: "#10B981",
                  animation: "pulse 2s ease-in-out infinite",
                }}
              >
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: "#10B981",
                  }}
                />
                {stats.active_sessions} active
              </span>
            )}
          </div>
        }
        style={{ borderRadius: 16 }}
        headerStyle={{
          padding: "14px 20px",
          borderBottom: "1px solid var(--semi-color-border)",
        }}
        bodyStyle={{ padding: 20 }}
      >
        {error ? (
          <Banner
            type="danger"
            fullMode={false}
            description={error}
            style={{ margin: "20px 0" }}
          />
        ) : stats && stats.count > 0 ? (
          <>
            <LatencyGauge
              label="ASR (Speech → Text)"
              value={stats.avg_asr_ms}
              maxValue={3000}
              color="#3B82F6"
            />
            <LatencyGauge
              label="LLM (First Token)"
              value={stats.avg_llm_ms}
              maxValue={3000}
              color="#8B5CF6"
            />
            <LatencyGauge
              label="TTS (Text → Audio)"
              value={stats.avg_tts_ms}
              maxValue={5000}
              color="#EC4899"
            />
            <div
              style={{
                borderTop: "1px solid var(--semi-color-border)",
                paddingTop: 12,
                marginTop: 4,
              }}
            >
              <LatencyGauge
                label="End-to-End (Voice → Response)"
                value={stats.avg_e2e_ms}
                maxValue={8000}
                color="#10B981"
              />
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <Text size="small" type="tertiary">
                  P95: {stats.p95_e2e_ms}ms
                </Text>
                <Text size="small" type="tertiary">
                  Samples: {stats.count}
                </Text>
              </div>
            </div>
          </>
        ) : (
          <Empty
            description="Chưa có dữ liệu latency. Hãy nói chuyện với thiết bị!"
            style={{ padding: "20px 0" }}
          />
        )}
      </Card>

      {/* Recent Conversations */}
      <Card
        title={
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <div
              style={{
                width: 28,
                height: 28,
                borderRadius: 8,
                background: "linear-gradient(135deg, #10B981, #34D399)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#fff",
                fontSize: 14,
              }}
            >
              💬
            </div>
            <span>Live Conversations</span>
          </div>
        }
        style={{ borderRadius: 16 }}
        headerStyle={{
          padding: "14px 20px",
          borderBottom: "1px solid var(--semi-color-border)",
        }}
        bodyStyle={{ padding: "4px 20px", maxHeight: 280, overflowY: "auto" }}
      >
        {error ? (
          <Banner
            type="danger"
            fullMode={false}
            description="API live conversations chưa phản hồi."
            style={{ margin: "20px 0" }}
          />
        ) : stats && stats.recent.length > 0 ? (
          stats.recent.map((item, idx) => (
            <ConversationItem key={idx} item={item} />
          ))
        ) : (
          <Empty
            description="Chưa có cuộc hội thoại nào"
            style={{ padding: "20px 0" }}
          />
        )}
      </Card>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
      `}</style>
    </div>
  );
}
