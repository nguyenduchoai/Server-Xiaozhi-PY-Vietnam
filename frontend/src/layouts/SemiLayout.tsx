import React, { useState, useEffect } from 'react';
import { Layout } from '@douyinfe/semi-ui';
import { useAuth } from '@/hooks/useAuth';
import { UserDropdownMenu } from '@/components/UserDropdownMenu';
import { TopNav } from '@/components/TopNav';
import { Sun, Moon } from "lucide-react";
import { useSiteSettings } from "@/hooks/useSiteSettings";

const { Content } = Layout;

function useDarkMode() {
    const [isDark, setIsDark] = useState(() => {
        const saved = localStorage.getItem('theme-mode');
        if (saved) return saved === 'dark';
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    });

    useEffect(() => {
        const body = document.body;
        if (isDark) {
            body.setAttribute('theme-mode', 'dark');
            body.classList.add('semi-always-dark');
            localStorage.setItem('theme-mode', 'dark');
        } else {
            body.removeAttribute('theme-mode');
            body.classList.remove('semi-always-dark');
            localStorage.setItem('theme-mode', 'light');
        }
    }, [isDark]);

    return { isDark, toggle: () => setIsDark(prev => !prev) };
}

export default function SemiLayout({ children }: { children: React.ReactNode }) {
    const { user } = useAuth();
    const { data: siteSettings } = useSiteSettings();
    const { isDark, toggle: toggleDarkMode } = useDarkMode();

    const siteName = siteSettings?.web?.site_name || "AI Assistant";
    const siteLogo = siteSettings?.web?.site_logo || "/logo.jpg";

    const isAdmin = user?.is_superuser === true || user?.role === "admin" || user?.role === "super_admin";

    return (
        <Layout className="h-screen w-full" style={{ background: 'var(--apple-gray-100)', overflow: 'hidden' }}>
            {/* FLOATING ISLAND GLASSMORPHISM NAVBAR */}
            <div className="fixed top-4 left-0 right-0 z-[100] px-4 md:px-8 w-full max-w-[1700px] mx-auto transition-all duration-300 pointer-events-none">
                <div 
                    className="flex items-center justify-between px-3 md:px-5 h-16 pointer-events-auto"
                    style={{ 
                        background: isDark ? 'rgba(30, 41, 59, 0.85)' : 'rgba(255, 255, 255, 0.85)',
                        border: isDark ? '1px solid rgba(51, 65, 85, 0.8)' : '1px solid rgba(226, 232, 240, 0.8)',
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 10px 15px -3px rgba(0, 0, 0, 0.05)',
                        borderRadius: 32,
                        backdropFilter: 'blur(24px) saturate(200%)',
                        WebkitBackdropFilter: 'blur(24px) saturate(200%)',
                    }}
                >
                    {/* LOGO AREA */}
                    <div className="flex items-center gap-3 shrink-0">
                        <img
                            src={siteLogo}
                            alt={siteName}
                            style={{
                                width: 36,
                                height: 36,
                                borderRadius: '10px'
                            }}
                        />
                        <span className="text-base font-bold hidden xl:block" style={{ color: isDark ? '#F1F5F9' : '#0F172A' }}>{siteName}</span>
                    </div>

                    {/* DYNAMIC TOP NAV */}
                    <div className="flex-1 flex justify-center items-center overflow-visible mx-2">
                        <TopNav isAdmin={isAdmin} />
                    </div>

                    {/* RIGHT WIDGETS */}
                    <div className="flex items-center gap-3 shrink-0">
                        <button
                            onClick={toggleDarkMode}
                            className="flex items-center justify-center w-10 h-10 rounded-[20px] transition-all duration-200 hover:-translate-y-0.5"
                            style={{ 
                                background: isDark ? 'rgba(51, 65, 85, 0.7)' : 'rgba(241, 245, 249, 0.7)',
                                border: '1px solid transparent'
                            }}
                            onMouseEnter={(e) => { e.currentTarget.style.background = isDark ? '#334155' : '#E2E8F0'; }}
                            onMouseLeave={(e) => { e.currentTarget.style.background = isDark ? 'rgba(51, 65, 85, 0.7)' : 'rgba(241, 245, 249, 0.7)'; }}
                            aria-label={isDark ? 'Chế độ sáng' : 'Chế độ tối'}
                        >
                            {isDark ? <Sun size={18} color="#F8FAFC" /> : <Moon size={18} color="#475569" />}
                        </button>
                        
                        <div className="flex items-center justify-center rounded-[24px] p-1 transition-all duration-200 hover:-translate-y-0.5"
                             style={{
                                background: isDark ? 'rgba(51, 65, 85, 0.5)' : 'rgba(255, 255, 255, 0.5)',
                                border: isDark ? '1px solid rgba(71, 85, 105, 0.6)' : '1px solid rgba(226, 232, 240, 0.6)',
                             }}>
                             <UserDropdownMenu />
                        </div>
                    </div>
                </div>
            </div>

            <Content
                className="overflow-y-auto relative z-0 w-full"
                style={{
                    background: 'var(--apple-gray-100)',
                }}
            >
                <div style={{ paddingTop: '88px', paddingBottom: '24px', paddingLeft: '24px', paddingRight: '24px', minHeight: '100vh' }}>
                    {children}
                </div>
            </Content>
        </Layout>
    );
}
