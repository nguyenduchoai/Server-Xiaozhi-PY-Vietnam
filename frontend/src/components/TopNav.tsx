import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
    LayoutDashboard,
    Bot,
    Smartphone,
    Brain,
    MessageCircle,
    ShoppingBag,
    Users,
    Activity,
    Package,
    Server,
    Cpu,
    ChevronDown,
    X,
    Menu,
    Shield,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Tooltip } from '@douyinfe/semi-ui';

interface TopNavProps {
    isAdmin?: boolean;
}

interface MenuItem {
    label: string;
    path?: string;
    icon?: React.ReactNode;
    items?: { label: string; path: string }[];
}

const menuGroups: MenuItem[] = [
    { label: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard size={18} /> },
    { 
        label: 'Cấu hình AI', 
        icon: <Bot size={18} />,
        items: [
            { label: 'Agents', path: '/agents' },
            { label: 'Providers', path: '/providers' },
            { label: 'Tools', path: '/tools' },
            { label: 'MCP Configs', path: '/mcp-configs' },
        ]
    },
    { 
        label: 'Thiết bị', 
        icon: <Smartphone size={18} />,
        items: [
            { label: 'Devices', path: '/devices' },
            { label: 'Asset Templates', path: '/asset-templates' },
            { label: 'Display Customizer', path: '/display-customizer' },
            { label: 'Themes', path: '/themes' },
        ]
    },
    { 
        label: 'Tri thức', 
        icon: <Brain size={18} />,
        items: [
            { label: 'Memory', path: '/memory' },
            { label: 'Kho Tri Thức', path: '/knowledge' },
        ]
    },
    { 
        label: 'Giao tiếp', 
        icon: <MessageCircle size={18} />,
        items: [
            { label: 'Chat', path: '/chat' },
            { label: 'Thông Báo', path: '/notifications' },
        ]
    },
    { label: 'Marketplace', path: '/marketplace', icon: <ShoppingBag size={18} /> },
];

const adminGroups: MenuItem[] = [
    {
        label: 'Quản trị (Admin)',
        icon: <Shield size={18} />,
        items: [
            { label: 'Users', path: '/admin/users' },
            { label: 'Thiết bị Hệ thống', path: '/admin/devices' },
            { label: 'Hardware Types', path: '/admin/hardware-types' },
            { label: 'MCP Endpoint', path: '/admin/mcp-endpoint' },
            { label: 'Sức khỏe Hệ thống', path: '/admin/system-health' },
            { label: '', path: '', type: 'divider' as any },
            { label: 'Cài đặt Hệ thống', path: '/admin/system-settings', danger: true },
        ]
    }
];

export function TopNav({ isAdmin = false }: TopNavProps) {
    const navigate = useNavigate();
    const location = useLocation();
    const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const navRef = useRef<HTMLElement>(null);
    const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const isActive = useCallback((path: string) => location.pathname.startsWith(path), [location.pathname]);

    // Clear any pending close timer
    const cancelClose = useCallback(() => {
        if (closeTimerRef.current) {
            clearTimeout(closeTimerRef.current);
            closeTimerRef.current = null;
        }
    }, []);

    // Delayed close to allow mouse movement between button and dropdown
    const scheduleClose = useCallback(() => {
        cancelClose();
        closeTimerRef.current = setTimeout(() => {
            setActiveDropdown(null);
        }, 150);
    }, [cancelClose]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (navRef.current && !navRef.current.contains(event.target as Node)) {
                cancelClose();
                setActiveDropdown(null);
                setMobileMenuOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
            cancelClose();
        };
    }, [cancelClose]);

    useEffect(() => {
        setMobileMenuOpen(false);
    }, [location.pathname]);

    const toggleDropdown = useCallback((key: string) => {
        cancelClose();
        setActiveDropdown(prev => prev === key ? null : key);
    }, [cancelClose]);

    const handleItemClick = useCallback((path: string) => {
        navigate(path);
        setActiveDropdown(null);
        setMobileMenuOpen(false);
    }, [navigate]);

    return (
        <nav 
            ref={navRef}
            className="relative z-50 w-full"
            role="navigation"
            aria-label="Main navigation"
        >
            <style>{`
                /* Responsive compact mode for TopNav */
                .nav-btn-desktop { padding: 4px 8px !important; min-width: 60px !important; justify-content: center !important; border-radius: 12px !important; }
                .nav-btn-desktop svg { margin: 0 !important; }
            `}</style>
            <div className="flex items-center justify-center h-12">
                <div className="hidden lg:flex items-center gap-1 flex-1 justify-center">
                    {menuGroups.map((group, idx) => {
                        const groupKey = `group-${idx}`;
                        const hasActive = group.items?.some(item => isActive(item.path));
                        const isDropdownOpen = activeDropdown === groupKey;
                        
                        return (
                            <div key={idx} className="relative flex-shrink-0"
                                            onMouseEnter={cancelClose}
                                            onMouseLeave={scheduleClose}
                                        >
                                {group.items ? (
                                    <>
                                        <button
                                            onClick={() => toggleDropdown(groupKey)}
                                            onMouseEnter={() => { cancelClose(); setActiveDropdown(groupKey); }}
                                            className={cn(
                                                "nav-btn-desktop flex flex-col items-center justify-center gap-0.5 px-2 h-12 rounded-xl text-xs font-medium transition-all duration-200 whitespace-nowrap bg-transparent cursor-pointer border-none",
                                                hasActive ? "bg-primary/10 text-primary" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-900"
                                            )}
                                            aria-expanded={isDropdownOpen}
                                            aria-haspopup="true"
                                        >
                                            {group.icon}
                                            <div className="flex items-center gap-0.5">
                                                <span className="topnav-label text-[10px] leading-tight">{group.label}</span>
                                                <ChevronDown 
                                                    size={10} 
                                                    className={cn(
                                                        "topnav-caret transition-transform duration-200",
                                                        isDropdownOpen && "rotate-180"
                                                    )} 
                                                />
                                            </div>
                                        </button>
                                        {isDropdownOpen && group.items && (
                                            <div 
                                                className="absolute top-full left-0 w-56 bg-white outline-none border border-border rounded-xl shadow-lg shadow-black/5 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-200"
                                                style={{ marginTop: 0, paddingTop: 4 }}
                                                onMouseEnter={cancelClose}
                                                onMouseLeave={scheduleClose}
                                            >
                                                {group.items.map((item, itemIdx) => {
                                                    if ((item as any).type === 'divider') {
                                                        return <div key={itemIdx} className="h-px bg-border my-1 w-full" />;
                                                    }
                                                    return (
                                                        <button
                                                            key={itemIdx}
                                                            onClick={() => handleItemClick(item.path!)}
                                                            className={cn(
                                                                "w-full text-left px-4 py-2.5 text-sm transition-colors",
                                                                isActive(item.path!)
                                                                    ? "bg-primary/10 text-primary font-medium"
                                                                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                                                            )}
                                                        >
                                                            {item.label}
                                                        </button>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <button
                                        onClick={() => handleItemClick(group.path!)}
                                        className={cn(
                                            "nav-btn-desktop flex flex-col items-center justify-center gap-0.5 px-2 h-12 rounded-xl text-xs font-medium transition-all duration-200 whitespace-nowrap border-none bg-transparent cursor-pointer",
                                            isActive(group.path!) ? "bg-primary/10 text-primary" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-900"
                                        )}
                                    >
                                        {group.icon}
                                        <span className="topnav-label text-[10px] leading-tight">{group.label}</span>
                                    </button>
                                )}
                            </div>
                        );
                    })}

                    {isAdmin && (
                        <>
                            <div className="w-px h-6 bg-border mx-2" />
                            <span className="text-xs text-muted-foreground/50 font-medium px-2">ADMIN</span>
                            {adminGroups.map((group, idx) => {
                                const groupKey = `admin-${idx}`;
                                const hasActive = group.items?.some(item => isActive(item.path));
                                const isDropdownOpen = activeDropdown === groupKey;
                                
                                return (
                                    <div key={idx} className="relative flex-shrink-0"
                                        onMouseEnter={cancelClose}
                                        onMouseLeave={scheduleClose}
                                    >
                                        {group.items ? (
                                            <>
                                                <button
                                                    onClick={() => toggleDropdown(groupKey)}
                                                    onMouseEnter={() => { cancelClose(); setActiveDropdown(groupKey); }}
                                                    className={cn(
                                                        "nav-btn-desktop flex flex-col items-center justify-center gap-0.5 px-2 h-12 rounded-xl text-xs font-medium transition-all duration-200 whitespace-nowrap bg-transparent cursor-pointer border-none",
                                                        hasActive ? "bg-red-500/10 text-red-600" : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-900"
                                                    )}
                                                    aria-expanded={isDropdownOpen}
                                                    aria-haspopup="true"
                                                >
                                                    {group.icon}
                                                    <div className="flex items-center gap-0.5">
                                                        <span className="topnav-label text-[10px] leading-tight">{group.label}</span>
                                                        <ChevronDown 
                                                            size={10} 
                                                            className={cn(
                                                                "topnav-caret transition-transform duration-200",
                                                                isDropdownOpen && "rotate-180"
                                                            )} 
                                                        />
                                                    </div>
                                                </button>
                                                {isDropdownOpen && group.items && (
                                                    <div 
                                                        className="absolute top-full right-0 w-56 bg-white outline-none border border-border rounded-xl shadow-lg shadow-black/5 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-200"
                                                        style={{ marginTop: 0, paddingTop: 4 }}
                                                        onMouseEnter={cancelClose}
                                                        onMouseLeave={scheduleClose}
                                                    >
                                                       {group.items.map((item, itemIdx) => {
                                                            if ((item as any).type === 'divider') {
                                                                return <div key={itemIdx} className="h-px bg-border my-1 w-full" />;
                                                            }
                                                            return (
                                                                <button
                                                                    key={itemIdx}
                                                                    onClick={() => handleItemClick(item.path!)}
                                                                    className={cn(
                                                                        "w-full text-left px-4 py-2.5 text-sm transition-colors",
                                                                        isActive(item.path!)
                                                                            ? "bg-destructive/10 text-destructive font-medium"
                                                                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                                                                    )}
                                                                >
                                                                    {item.label}
                                                                </button>
                                                            );
                                                        })}
                                                    </div>
                                                )}
                                            </>
                                        ) : (
                                            <button
                                                onClick={() => handleItemClick(group.path!)}
                                                className={cn(
                                                    "nav-btn-desktop flex flex-col items-center justify-center gap-0.5 px-2 h-12 rounded-xl text-xs font-medium transition-all duration-200 whitespace-nowrap flex-shrink-0 bg-transparent cursor-pointer border-none",
                                                    isActive(group.path!)
                                                        ? "bg-red-500/10 text-red-600"
                                                        : "text-slate-600 hover:bg-slate-100/50 hover:text-slate-900"
                                                )}
                                            >
                                                {group.icon}
                                                <span className="topnav-label text-[10px] leading-tight">{group.label}</span>
                                            </button>
                                        )}
                                    </div>
                                );
                            })}
                        </>
                    )}
                </div>

                <button
                    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    className="lg:hidden flex items-center justify-center w-10 h-10 rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                    aria-label="Toggle menu"
                    aria-expanded={mobileMenuOpen}
                >
                    {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
                </button>
            </div>

            {mobileMenuOpen && (
                <div className="lg:hidden border-t border-border bg-background animate-in slide-in-from-top duration-200">
                    <div className="px-4 py-3 space-y-1 max-h-[70vh] overflow-y-auto">
                        {menuGroups.map((group, idx) => {
                            const mobileKey = `mobile-${idx}`;
                            const hasActive = group.items?.some(item => isActive(item.path));
                            const isDropdownOpen = activeDropdown === mobileKey;
                            
                            return (
                                <div key={idx}>
                                    {group.items ? (
                                        <>
                                            <button
                                                onClick={() => toggleDropdown(mobileKey)}
                                                className={cn(
                                                    "w-full flex items-center justify-between px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                                                    hasActive ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent"
                                                )}
                                            >
                                                <span className="flex items-center gap-2">
                                                    {group.icon}
                                                    {group.label}
                                                </span>
                                                <ChevronDown 
                                                    size={16} 
                                                    className={cn(
                                                        "transition-transform",
                                                        isDropdownOpen && "rotate-180"
                                                    )} 
                                                />
                                            </button>
                                            {isDropdownOpen && group.items && (
                                                <div className="ml-4 mt-1 space-y-0.5">
                                                   {group.items.map((item, itemIdx) => {
                                                        if ((item as any).type === 'divider') {
                                                            return <div key={itemIdx} className="h-px bg-border my-1 w-full" />;
                                                        }
                                                        return (
                                                            <button
                                                                key={itemIdx}
                                                                onClick={() => handleItemClick(item.path!)}
                                                                className={cn(
                                                                    "w-full text-left px-3 py-2 rounded-md text-sm transition-colors",
                                                                    isActive(item.path!)
                                                                        ? "bg-primary/10 text-primary font-medium"
                                                                        : "text-muted-foreground hover:bg-accent"
                                                                )}
                                                            >
                                                                {item.label}
                                                            </button>
                                                        );
                                                    })}
                                                </div>
                                            )}
                                        </>
                                    ) : (
                                        <button
                                            onClick={() => handleItemClick(group.path!)}
                                            className={cn(
                                                "w-full flex items-center gap-2 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                                                isActive(group.path!) ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-accent"
                                            )}
                                        >
                                            {group.icon}
                                            {group.label}
                                        </button>
                                    )}
                                </div>
                            );
                        })}

                        {isAdmin && (
                            <>
                                <div className="my-2 border-t border-border" />
                                <div className="text-xs text-muted-foreground/50 font-medium px-3 py-1">ADMIN</div>
                                {adminGroups.map((group, idx) => {
                                    const mobileKey = `admin-mobile-${idx}`;
                                    const hasActive = group.items?.some(item => isActive(item.path));
                                    const isDropdownOpen = activeDropdown === mobileKey;
                                    
                                    return (
                                        <div key={idx}>
                                            {group.items ? (
                                                <>
                                                    <button
                                                        onClick={() => toggleDropdown(mobileKey)}
                                                        className={cn(
                                                            "w-full flex items-center justify-between px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                                                            hasActive ? "bg-destructive/10 text-destructive" : "text-muted-foreground hover:bg-accent"
                                                        )}
                                                    >
                                                        <span className="flex items-center gap-2">
                                                            {group.icon}
                                                            {group.label}
                                                        </span>
                                                        <ChevronDown 
                                                            size={16} 
                                                            className={cn(
                                                                "transition-transform",
                                                                isDropdownOpen && "rotate-180"
                                                            )} 
                                                        />
                                                    </button>
                                                    {isDropdownOpen && group.items && (
                                                        <div className="ml-4 mt-1 space-y-0.5">
                                                           {group.items.map((item, itemIdx) => {
                                                                if ((item as any).type === 'divider') {
                                                                    return <div key={itemIdx} className="h-px bg-border my-1 w-full" />;
                                                                }
                                                                return (
                                                                    <button
                                                                        key={itemIdx}
                                                                        onClick={() => handleItemClick(item.path!)}
                                                                        className={cn(
                                                                            "w-full text-left px-3 py-2 rounded-md text-sm transition-colors",
                                                                            isActive(item.path!)
                                                                                ? "bg-destructive/10 text-destructive font-medium"
                                                                                : "text-muted-foreground hover:bg-accent"
                                                                        )}
                                                                    >
                                                                        {item.label}
                                                                    </button>
                                                                );
                                                            })}
                                                        </div>
                                                    )}
                                                </>
                                            ) : (
                                                <button
                                                    onClick={() => handleItemClick(group.path!)}
                                                    className={cn(
                                                        "w-full flex items-center gap-2 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                                                        isActive(group.path!) ? "bg-destructive/10 text-destructive" : "text-muted-foreground hover:bg-accent"
                                                    )}
                                                >
                                                    {group.icon}
                                                    {group.label}
                                                </button>
                                            )}
                                        </div>
                                    );
                                })}
                            </>
                        )}
                    </div>
                </div>
            )}
        </nav>
    );
}

export default TopNav;
