
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Card, Button, Banner, Typography, Row, Col, Skeleton, Progress, Empty, Tooltip } from '@douyinfe/semi-ui';
import {
  IconActivity,
  IconBolt,
  IconUser,
  IconCreditCard,
  IconBox,
  IconUserGroup,
  IconServer,
  IconDesktop,
  IconRefresh,
  IconShield,
} from '@douyinfe/semi-icons';
import { useEffect, useState, useCallback } from "react";

import { analyticsApi, type DashboardStats, type DeviceStatus } from "@/services/analyticsService";
import { DeviceStatusList } from "@/components/dashboard/DeviceStatusList";
import { LatencyMonitorPanel } from "@/components/dashboard/LatencyMonitorPanel";
import type { OTAStats } from "@/services/otaDashboardService";
import { otaDashboardService } from "@/services/otaDashboardService";
import { ArrowUpRight, Cpu, Zap, Wifi, Radio } from "lucide-react";

const { Title, Text } = Typography;

// ============ Stat Card Component ============
interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  subtitle?: string;
  gradient: string;
  glowColor: string;
  delay?: number;
}

function StatCard({ icon, label, value, subtitle, gradient, glowColor, delay = 0 }: StatCardProps) {
  return (
    <div
      style={{
        position: 'relative',
        borderRadius: '2.5rem',
        padding: '28px',
        background: 'rgba(255, 255, 255, 0.03)',
        overflow: 'hidden',
        transition: 'all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
        cursor: 'default',
        animation: `cardSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms both`,
        boxShadow: '0 16px 32px rgba(0,0,0,0.06), inset 0 1px 2px rgba(255,255,255,0.5), inset 0 -1px 2px rgba(0,0,0,0.05)',
        border: '1px solid rgba(255, 255, 255, 0.2)',
        backdropFilter: 'blur(40px)',
        WebkitBackdropFilter: 'blur(40px)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-6px) scale(1.02)';
        e.currentTarget.style.boxShadow = `0 24px 48px rgba(0,0,0,0.1), 0 0 40px ${glowColor}, inset 0 2px 3px rgba(255,255,255,0.7), inset 0 -1px 2px rgba(0,0,0,0.05)`;
        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.4)';
        
        const spheres = e.currentTarget.querySelectorAll('.glow-sphere');
        spheres.forEach(s => {
            (s as HTMLElement).style.opacity = '0.35';
            (s as HTMLElement).style.filter = 'blur(40px)';
        });
        
        const iconWrap = e.currentTarget.querySelector('.stat-icon-wrapper');
        if (iconWrap) (iconWrap as HTMLElement).style.transform = 'translateY(-4px) scale(1.1)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0) scale(1)';
        e.currentTarget.style.boxShadow = '0 16px 32px rgba(0,0,0,0.06), inset 0 1px 2px rgba(255,255,255,0.5), inset 0 -1px 2px rgba(0,0,0,0.05)';
        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)';
        
        const spheres = e.currentTarget.querySelectorAll('.glow-sphere');
        spheres.forEach(s => {
            (s as HTMLElement).style.opacity = '0.15';
            (s as HTMLElement).style.filter = 'blur(60px)';
        });
        
        const iconWrap = e.currentTarget.querySelector('.stat-icon-wrapper');
        if (iconWrap) (iconWrap as HTMLElement).style.transform = 'translateY(0) scale(1)';
      }}
    >
      {/* 3 Glowing Spheres for Liquid Glass Color Bleed */}
      <div className="glow-sphere" style={{ position: 'absolute', top: '-15%', left: '-10%', width: '70%', height: '70%', background: '#0068FF', filter: 'blur(60px)', opacity: 0.15, zIndex: -1, transition: 'all 0.5s ease', borderRadius: '50%' }} />
      <div className="glow-sphere" style={{ position: 'absolute', bottom: '-20%', right: '-15%', width: '80%', height: '80%', background: '#A855F7', filter: 'blur(60px)', opacity: 0.15, zIndex: -1, transition: 'all 0.5s ease', borderRadius: '50%' }} />
      <div className="glow-sphere" style={{ position: 'absolute', top: '25%', right: '15%', width: '50%', height: '50%', background: '#0EA5E9', filter: 'blur(50px)', opacity: 0.15, zIndex: -1, transition: 'all 0.5s ease', borderRadius: '50%' }} />

      {/* Volumetric Specular Highlight Top Edge */}
      <div style={{ position: 'absolute', top: 0, left: '15%', right: '15%', height: '1.5px', background: 'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.7) 50%, rgba(255,255,255,0) 100%)', opacity: 0.7 }} />

      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', position: 'relative', zIndex: 1 }}>
        <div>
          <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: '12px', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            {label}
          </Text>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontSize: '36px', fontWeight: 800, letterSpacing: '-0.04em', color: 'var(--apple-text-primary)' }}>
              {value}
            </span>
            {subtitle && (
              <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--apple-text-tertiary)' }}>{subtitle}</span>
            )}
          </div>
        </div>
        
        {/* Floating 3D Icon */}
        <div
          className="stat-icon-wrapper"
          style={{
            width: '54px',
            height: '54px',
            borderRadius: '50%',
            background: 'rgba(255, 255, 255, 0.15)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--apple-text-primary)',
            fontSize: '22px',
            boxShadow: `inset 0 3px 6px rgba(255,255,255,0.6), inset 0 -2px 6px rgba(0,0,0,0.1), 0 8px 16px ${glowColor}`,
            border: '1px solid rgba(255, 255, 255, 0.3)',
            transition: 'transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)'
          }}
        >
          {icon}
        </div>
      </div>
    </div>
  );
}

// ============ Quick Action Card ============
interface QuickActionProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  gradient: string;
  onClick: () => void;
  delay?: number;
}

function QuickAction({ icon, title, description, gradient, onClick, delay = 0 }: QuickActionProps) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        padding: '16px 20px',
        borderRadius: '2rem',
        background: 'rgba(255, 255, 255, 0.05)',
        border: '1px solid rgba(255, 255, 255, 0.2)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        boxShadow: '0 8px 24px rgba(0,0,0,0.03), inset 0 1px 1.5px rgba(255,255,255,0.4)',
        cursor: 'pointer',
        position: 'relative',
        overflow: 'hidden',
        transition: 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
        animation: `cardSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) ${delay}ms both`,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateX(6px) scale(1.01)';
        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.5)';
        e.currentTarget.style.boxShadow = '0 12px 32px rgba(0,122,255,0.1), inset 0 2px 2px rgba(255,255,255,0.6)';
        
        const qaSpheres = e.currentTarget.querySelectorAll('.qa-glow');
        qaSpheres.forEach(s => { (s as HTMLElement).style.opacity = '0.4'; });
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateX(0) scale(1)';
        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)';
        e.currentTarget.style.boxShadow = '0 8px 24px rgba(0,0,0,0.03), inset 0 1px 1.5px rgba(255,255,255,0.4)';
        
        const qaSpheres = e.currentTarget.querySelectorAll('.qa-glow');
        qaSpheres.forEach(s => { (s as HTMLElement).style.opacity = '0.0'; });
      }}
    >
      <div className="qa-glow" style={{ position: 'absolute', top: '50%', left: '0', transform: 'translateY(-50%)', width: '100px', height: '100px', background: gradient, filter: 'blur(40px)', opacity: 0, transition: 'opacity 0.4s ease', zIndex: -1, borderRadius: '50%' }} />
      
      <div
        style={{
          width: '44px',
          height: '44px',
          borderRadius: '50%',
          background: 'rgba(255, 255, 255, 0.2)',
          backdropFilter: 'blur(10px)',
          border: '1px solid rgba(255, 255, 255, 0.4)',
          boxShadow: 'inset 0 2px 4px rgba(255,255,255,0.4), 0 4px 12px rgba(0,0,0,0.05)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--apple-text-primary)',
          flexShrink: 0,
        }}
      >
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0, zIndex: 1 }}>
        <Text strong style={{ display: 'block', fontSize: '15px', color: 'var(--apple-text-primary)' }}>{title}</Text>
        <Text type="tertiary" size="small">{description}</Text>
      </div>
      <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'rgba(0,0,0,0.03)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <ArrowUpRight size={16} style={{ color: 'var(--apple-text-primary)' }} />
      </div>
    </div>
  );
}

// ============ OTA Sub-components ============

function ActivityChart({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data);
  const maxVal = Math.max(...entries.map(([, v]) => v), 1);

  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 140, padding: "8px 4px 0" }}>
      {entries.map(([date, count]) => {
        const height = Math.max((count / maxVal) * 110, 6);
        const label = date.slice(5);
        return (
          <Tooltip key={date} content={`${date}: ${count} thiết bị`}>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
              <Text size="small" type="tertiary" style={{ fontSize: '11px' }}>{count}</Text>
              <div
                style={{
                  width: "100%",
                  maxWidth: 42,
                  height: `${height}px`,
                  borderRadius: "10px 10px 6px 6px",
                  background: "linear-gradient(180deg, #6366F1 0%, #818CF8 50%, #A5B4FC 100%)",
                  transition: "height 0.5s cubic-bezier(0.16, 1, 0.3, 1)",
                  boxShadow: count > 0 ? '0 4px 12px rgba(99, 102, 241, 0.25)' : 'none',
                }}
              />
              <Text size="small" type="tertiary" style={{ fontSize: '11px' }}>{label}</Text>
            </div>
          </Tooltip>
        );
      })}
    </div>
  );
}

function BoardDistribution({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  const colors = ["#6366F1", "#EC4899", "#F59E0B", "#10B981", "#3B82F6", "#8B5CF6"];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {Object.entries(data).map(([board, count], i) => (
        <div key={board}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <Text size="small" style={{ fontWeight: 500 }}>{board}</Text>
            <Text size="small" type="tertiary">
              {count} ({Math.round((count / total) * 100)}%)
            </Text>
          </div>
          <Progress
            percent={Math.round((count / total) * 100)}
            showInfo={false}
            stroke={colors[i % colors.length]}
            size="small"
          />
        </div>
      ))}
    </div>
  );
}

// ============ Main Dashboard ============

export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Data states
  const [usage, setUsage] = useState<any>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const [otaStats, setOtaStats] = useState<OTAStats | null>(null);

  // UI states
  const [loading, setLoading] = useState(true);
  const [otaLoading, setOtaLoading] = useState(true);

  const fetchOtaStats = useCallback(async () => {
    setOtaLoading(true);
    try {
      const data = await otaDashboardService.getStats();
      setOtaStats(data);
    } catch (err) {
      console.error("OTA stats fetch error:", err);
    } finally {
      setOtaLoading(false);
    }
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsData, devicesData] = await Promise.allSettled([
          analyticsApi.getDashboardStats(),
          analyticsApi.getDeviceStatus()
        ]);


        if (statsData.status === "fulfilled") setStats(statsData.value);
        if (devicesData.status === "fulfilled") setDevices(devicesData.value.devices);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    fetchOtaStats();
  }, [fetchOtaStats]);

  const isAdmin = user?.is_superuser;

  // Quota warnings
  const getQuotaWarning = (usedPercent: number | undefined, resourceName: string) => {
    if (usedPercent === undefined || usedPercent === null) return null;
    if (usedPercent >= 90) return { type: "danger", message: `${resourceName} gần hết (${usedPercent.toFixed(0)}%)` };
    if (usedPercent >= 80) return { type: "warning", message: `${resourceName} sắp đầy (${usedPercent.toFixed(0)}%)` };
    return null;
  };

  const warnings = [
    usage?.usage_percent && getQuotaWarning(usage.usage_percent.agents, "Số lượng Agent"),
    usage?.usage_percent && getQuotaWarning(usage.usage_percent.devices, "Số lượng Thiết bị"),
    usage?.usage_percent && getQuotaWarning(usage.usage_percent.tokens, "Token hàng tháng"),
  ].filter(Boolean) as { type: "danger" | "warning" | "info" | "success", message: string }[];


  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <Skeleton placeholder={<Skeleton.Title className='mb-4' />} loading={true} active>
          <Skeleton.Paragraph rows={3} />
        </Skeleton>
        <Row gutter={16}>
          <Col span={6}><Skeleton.Image /></Col>
          <Col span={6}><Skeleton.Image /></Col>
          <Col span={6}><Skeleton.Image /></Col>
          <Col span={6}><Skeleton.Image /></Col>
        </Row>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Quota Warnings */}
      {warnings.length > 0 && (
        <Banner
          type={warnings.some(w => w.type === 'danger') ? 'danger' : 'warning'}
          description={
            <div>
              <div style={{ fontWeight: 600, marginBottom: '8px' }}>Thông báo giới hạn:</div>
              <ul style={{ listStyle: 'disc', paddingLeft: '20px', margin: 0 }}>
                {warnings.map((w, idx) => <li key={idx}>{w.message}</li>)}
              </ul>

            </div>
          }
          style={{ borderRadius: '16px' }}
        />
      )}

      {/* Welcome Section */}
      <div style={{ animation: 'cardSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) both' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
          <Title heading={2} style={{ margin: 0, letterSpacing: '-0.03em' }}>
            Chào mừng trở lại
          </Title>
          <span style={{ fontSize: '28px', animation: 'wave 2s ease-in-out infinite' }}>👋</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Text type="secondary" style={{ fontSize: '16px' }}>
            {user?.full_name || user?.email}
          </Text>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            padding: '2px 10px',
            borderRadius: '20px',
            fontSize: '12px',
            fontWeight: 600,
            background: isAdmin
              ? 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15))'
              : 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(52,211,153,0.15))',
            color: isAdmin ? '#818CF8' : '#10B981',
            border: `1px solid ${isAdmin ? 'rgba(99,102,241,0.2)' : 'rgba(16,185,129,0.2)'}`,
          }}>
            {isAdmin ? "Admin" : "Community Edition"}
          </span>
        </div>
      </div>

      {/* Stats Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          icon={<Wifi size={20} />}
          label="Thiết bị Online"
          value={stats?.active_devices || 0}
          subtitle={`/ ${stats?.total_devices || 0}`}
          gradient="linear-gradient(135deg, #10B981, #34D399)"
          glowColor="rgba(16,185,129,0.12)"
          delay={0}
        />
        <StatCard
          icon={<Radio size={20} />}
          label="Tương tác Voice"
          value={stats?.messages_today || 0}
          subtitle={`/ ${stats?.total_messages || 0} total`}
          gradient="linear-gradient(135deg, #3B82F6, #60A5FA)"
          glowColor="rgba(59,130,246,0.12)"
          delay={80}
        />
        <StatCard
          icon={<Zap size={20} />}
          label="Tokens Usage"
          value={`${((usage?.tokens_used || 0) / 1000).toFixed(1)}k`}
          subtitle={`/ ${usage?.tokens_limit === -1 ? "∞" : `${((usage?.tokens_limit || 0) / 1000).toFixed(0)}k`}`}
          gradient="linear-gradient(135deg, #F59E0B, #FBBF24)"
          glowColor="rgba(245,158,11,0.12)"
          delay={160}
        />
        <StatCard
          icon={<Cpu size={20} />}
          label="AI Agents"
          value={stats?.total_agents || 0}
          gradient="linear-gradient(135deg, #8B5CF6, #A78BFA)"
          glowColor="rgba(139,92,246,0.12)"
          delay={240}
        />
      </div>

      {/* Real-time AI Pipeline Monitoring */}
      <div style={{ animation: 'cardSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 280ms both' }}>
        <LatencyMonitorPanel />
      </div>

      {/* OTA Stats Cards */}
      {otaStats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" style={{ animation: 'cardSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 300ms both' }}>
          {[
            { icon: <IconDesktop />, title: "Tổng thiết bị", value: otaStats.total_devices, subtitle: `${otaStats.enabled_devices} kích hoạt`, color: "#6366F1", bg: "rgba(99, 102, 241, 0.15)" },
            { icon: <IconActivity />, title: "Hoạt động hôm nay", value: otaStats.active_today, subtitle: `${otaStats.active_this_week} tuần này`, color: "#10B981", bg: "rgba(16, 185, 129, 0.15)" },
            { icon: <IconServer />, title: "Firmware", value: otaStats.total_firmware, subtitle: "versions", color: "#F59E0B", bg: "rgba(245, 158, 11, 0.15)" },
            { icon: <IconShield />, title: "License", value: `${otaStats.valid_licenses}/${otaStats.total_devices}`, subtitle: `${otaStats.expired_licenses} hết hạn`, color: otaStats.expired_licenses > 0 ? "#EF4444" : "#10B981", bg: otaStats.expired_licenses > 0 ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)" },
          ].map((s, idx) => (
            <div
              key={idx}
              style={{
                background: 'rgba(255, 255, 255, 0.05)',
                border: `1px solid rgba(255, 255, 255, 0.2)`,
                borderRadius: '2rem',
                padding: "24px",
                position: 'relative',
                overflow: 'hidden',
                backdropFilter: 'blur(30px)',
                WebkitBackdropFilter: 'blur(30px)',
                boxShadow: '0 12px 24px rgba(0,0,0,0.04), inset 0 1px 1px rgba(255,255,255,0.4)',
                transition: 'all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = `rgba(255, 255, 255, 0.5)`;
                e.currentTarget.style.transform = 'translateY(-6px) scale(1.02)';
                e.currentTarget.style.boxShadow = `0 20px 40px ${s.color}20, inset 0 2px 2px rgba(255,255,255,0.7)`;
                
                const bgGlow = e.currentTarget.querySelector('.ota-glow');
                if (bgGlow) {
                    (bgGlow as HTMLElement).style.opacity = '0.3';
                    (bgGlow as HTMLElement).style.filter = 'blur(30px)';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = `rgba(255, 255, 255, 0.2)`;
                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                e.currentTarget.style.boxShadow = '0 12px 24px rgba(0,0,0,0.04), inset 0 1px 1px rgba(255,255,255,0.4)';
                
                const bgGlow = e.currentTarget.querySelector('.ota-glow');
                if (bgGlow) {
                    (bgGlow as HTMLElement).style.opacity = '0.1';
                    (bgGlow as HTMLElement).style.filter = 'blur(50px)';
                }
              }}
            >
              <div className="ota-glow" style={{ position: 'absolute', bottom: '-20%', right: '-20%', width: '100%', height: '100%', background: s.color, filter: 'blur(50px)', opacity: 0.1, zIndex: -1, transition: 'all 0.5s ease', borderRadius: '50%' }} />

              <div style={{ position: 'absolute', top: 0, left: '20%', right: '20%', height: '1px', background: 'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.5) 50%, rgba(255,255,255,0) 100%)' }} />

              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                <div style={{
                  width: 44, height: 44, borderRadius: '50%',
                  background: 'rgba(255, 255, 255, 0.2)',
                  backdropFilter: 'blur(10px)',
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: 'var(--apple-text-primary)', fontSize: 20,
                  boxShadow: `inset 0 2px 4px rgba(255,255,255,0.6), inset 0 -2px 4px rgba(0,0,0,0.1), 0 8px 16px ${s.color}40`,
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                }}>
                  {s.icon}
                </div>
                <Text size="small" style={{ fontWeight: 600, color: 'var(--apple-text-primary)' }}>{s.title}</Text>
              </div>
              <Title heading={2} style={{ margin: 0, color: 'var(--apple-text-primary)', fontSize: '30px', fontWeight: 800 }}>{s.value}</Title>
              {s.subtitle && <Text size="small" type="tertiary" style={{ fontWeight: 500, marginTop: '4px', display: 'block' }}>{s.subtitle}</Text>}
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-7 gap-6">
        {/* Device Status List */}
        <div className="lg:col-span-4" style={{ animation: 'cardSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 350ms both' }}>
          <DeviceStatusList devices={devices} loading={loading} />
        </div>

        {/* Quick Actions */}
        <div className="lg:col-span-3" style={{ animation: 'cardSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 400ms both' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <Title heading={5} style={{ margin: 0 }}>Truy cập nhanh</Title>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <QuickAction
              icon={<IconUser style={{ fontSize: 18 }} />}
              title="Quản lý AI Agents"
              description="Tạo và cấu hình AI agents"
              gradient="linear-gradient(135deg, #8B5CF6, #A78BFA)"
              onClick={() => navigate("/agents")}
              delay={450}
            />
            <QuickAction
              icon={<IconBox style={{ fontSize: 18 }} />}
              title="Quản lý Thiết bị"
              description="Thêm thiết bị phần cứng"
              gradient="linear-gradient(135deg, #3B82F6, #60A5FA)"
              onClick={() => navigate("/devices")}
              delay={500}
            />
            <QuickAction
              icon={<IconBolt style={{ fontSize: 18 }} />}
              title="Web Flasher"
              description="Nạp firmware cho thiết bị"
              gradient="linear-gradient(135deg, #F59E0B, #FBBF24)"
              onClick={() => navigate("/tools/flasher")}
              delay={550}
            />
            {isAdmin ? (
              <QuickAction
                icon={<IconUserGroup style={{ fontSize: 18 }} />}
                title="Quản lý User"
                description="Admin Only"
                gradient="linear-gradient(135deg, #EF4444, #F87171)"
                onClick={() => navigate("/admin/users")}
                delay={600}
              />
            ) : null}
          </div>
        </div>
      </div>

      {/* IoT & Firmware Section */}
      <div style={{
        borderTop: '1px solid var(--apple-border-primary)',
        paddingTop: 28,
        animation: 'cardSlideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) 500ms both',
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{
                width: '32px', height: '32px', borderRadius: '10px',
                background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff',
              }}>
                <Radio size={16} />
              </div>
              <Title heading={4} style={{ margin: 0 }}>IoT & Firmware</Title>
            </div>
            <Text type="tertiary" style={{ marginTop: 4, display: 'block' }}>Tổng quan firmware, license và tính năng thiết bị</Text>
          </div>
          <Button
            icon={<IconRefresh />}
            onClick={fetchOtaStats}
            loading={otaLoading}
            size="small"
            style={{ borderRadius: '10px' }}
          >
            Làm mới
          </Button>
        </div>

        {otaLoading && !otaStats ? (
          <Skeleton placeholder={<Skeleton.Paragraph rows={4} />} loading={true} active />
        ) : otaStats ? (
          <>
            {/* Charts */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, marginTop: 8 }}>
              <Card
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <IconActivity style={{ color: '#6366F1' }} />
                    <span>Hoạt động 7 ngày</span>
                  </div>
                }
                headerStyle={{ padding: "14px 20px", borderBottom: '1px solid var(--apple-border-primary)' }}
                bodyStyle={{ padding: "20px" }}
                style={{ borderRadius: '16px' }}
              >
                <ActivityChart data={otaStats.activity_by_day} />
              </Card>
              <Card
                title={
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <IconDesktop style={{ color: '#EC4899' }} />
                    <span>Phân bố Board</span>
                  </div>
                }
                headerStyle={{ padding: "14px 20px", borderBottom: '1px solid var(--apple-border-primary)' }}
                bodyStyle={{ padding: "20px" }}
                style={{ borderRadius: '16px' }}
              >
                {Object.keys(otaStats.board_type_count).length > 0 ? (
                  <BoardDistribution data={otaStats.board_type_count} />
                ) : (
                  <Empty description="Chưa có dữ liệu" />
                )}
              </Card>
            </div>

            {/* License Summary */}
            <Card
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <IconShield style={{ color: '#10B981' }} />
                  <span>License</span>
                </div>
              }
              style={{ marginTop: 16, borderRadius: '16px' }}
              headerStyle={{ padding: "14px 20px", borderBottom: '1px solid var(--apple-border-primary)' }}
              bodyStyle={{ padding: "20px" }}
            >
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { value: otaStats.valid_licenses, label: "Có hiệu lực", color: "#10B981", bg: "rgba(16, 185, 129, 0.08)" },
                  { value: otaStats.expired_licenses, label: "Hết hạn", color: "#EF4444", bg: "rgba(239, 68, 68, 0.08)" },
                  { value: otaStats.unlimited_licenses, label: "Không giới hạn", color: "#6366F1", bg: "rgba(99, 102, 241, 0.08)" },
                  { value: otaStats.trial_licenses, label: "Dùng thử", color: "#F59E0B", bg: "rgba(245, 158, 11, 0.08)" },
                ].map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      textAlign: "center",
                      padding: '24px 16px',
                      borderRadius: '1.5rem',
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: `1px solid rgba(255, 255, 255, 0.15)`,
                      position: 'relative',
                      overflow: 'hidden',
                      backdropFilter: 'blur(20px)',
                      WebkitBackdropFilter: 'blur(20px)',
                      boxShadow: '0 8px 16px rgba(0,0,0,0.03), inset 0 1px 1px rgba(255,255,255,0.3)',
                      transition: 'all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-4px) scale(1.02)';
                      e.currentTarget.style.borderColor = `rgba(255, 255, 255, 0.3)`;
                      e.currentTarget.style.boxShadow = `0 12px 24px ${item.color}20, inset 0 2px 2px rgba(255,255,255,0.5)`;
                      
                      const bgGlow = e.currentTarget.querySelector('.license-glow');
                      if (bgGlow) {
                          (bgGlow as HTMLElement).style.opacity = '0.2';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0) scale(1)';
                      e.currentTarget.style.borderColor = `rgba(255, 255, 255, 0.15)`;
                      e.currentTarget.style.boxShadow = '0 8px 16px rgba(0,0,0,0.03), inset 0 1px 1px rgba(255,255,255,0.3)';
                      
                      const bgGlow = e.currentTarget.querySelector('.license-glow');
                      if (bgGlow) {
                          (bgGlow as HTMLElement).style.opacity = '0.05';
                      }
                    }}
                  >
                    <div className="license-glow" style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: '80px', height: '80px', background: item.color, filter: 'blur(40px)', opacity: 0.05, zIndex: -1, transition: 'all 0.4s ease', borderRadius: '50%' }} />
                    <Title heading={2} style={{ color: item.color, margin: 0, letterSpacing: '-0.03em', fontSize: '32px', fontWeight: 800 }}>{item.value}</Title>
                    <Text size="small" type="tertiary" style={{ fontWeight: 600, display: 'block', marginTop: '6px', color: 'var(--apple-text-secondary)' }}>{item.label}</Text>
                  </div>
                ))}
              </div>
            </Card>
          </>
        ) : (
          <Empty description="Không thể tải dữ liệu IoT" />
        )}
      </div>

      {/* Scoped Animations */}
      <style>{`
        @keyframes cardSlideUp {
          0% { opacity: 0; transform: translateY(20px); }
          100% { opacity: 1; transform: translateY(0); }
        }

        @keyframes wave {
          0%, 100% { transform: rotate(0deg); }
          10% { transform: rotate(14deg); }
          20% { transform: rotate(-8deg); }
          30% { transform: rotate(14deg); }
          40% { transform: rotate(-4deg); }
          50% { transform: rotate(10deg); }
          60%, 100% { transform: rotate(0deg); }
        }
      `}</style>
    </div>
  );
}

export default DashboardPage;
