
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


// ============ Main Dashboard ============

export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Data states
  const [usage, setUsage] = useState<any>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [devices, setDevices] = useState<DeviceStatus[]>([]);

  // UI states
  const [loading, setLoading] = useState(true);

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
  }, []);

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
