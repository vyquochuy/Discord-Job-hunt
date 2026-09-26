import React from 'react';
import {
  LayoutDashboard,
  Briefcase,
  Sparkles,
  FileText,
  Send,
  User,
  Settings,
  LogOut,
  LogIn,
  Layers,
  Shield,
} from 'lucide-react';
import { cn } from '../../utils/cn';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { getCompanyMonogram } from '../../utils/formatters';

export type ViewType =
  | 'dashboard'
  | 'jobs'
  | 'recommendations'
  | 'resume'
  | 'applications'
  | 'profile'
  | 'system';

interface NavItem {
  id: ViewType;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: 'TỔNG QUAN',
    items: [
      { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { id: 'jobs', label: 'Khám phá việc làm', icon: Briefcase },
      { id: 'recommendations', label: 'Đề xuất phù hợp', icon: Sparkles },
    ],
  },
  {
    title: 'ỨNG TUYỂN & HỒ SƠ',
    items: [
      { id: 'resume', label: 'Hồ sơ tạo thiết kế', icon: FileText },
      { id: 'applications', label: 'Quản lý đơn nộp', icon: Send },
      { id: 'profile', label: 'Hồ sơ ứng viên', icon: User },
    ],
  },
  {
    title: 'CẤU HÌNH',
    items: [
      { id: 'system', label: 'Hệ thống & Dữ liệu', icon: Settings, badge: 'Admin' },
    ],
  },
];

export interface SidebarProps {
  activeView: ViewType;
  onNavigate: (view: ViewType) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onCloseMobileDrawer?: () => void;
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeView,
  onNavigate,
  collapsed = false,
  onCloseMobileDrawer,
  className,
}) => {
  const { currentUser, isSuperuser, isAuthenticated, logout, openAuthModal } = useAuth();

  const handleItemClick = (id: ViewType) => {
    onNavigate(id);
    if (onCloseMobileDrawer) {
      onCloseMobileDrawer();
    }
  };

  const displayName = currentUser?.full_name || currentUser?.email?.split('@')[0] || 'Ứng viên';
  const monogram = getCompanyMonogram(displayName);

  return (
    <aside
      className={cn(
        'h-full bg-surface border-r border-border flex flex-col justify-between select-none transition-all duration-200',
        collapsed ? 'w-[68px]' : 'w-[240px]',
        className
      )}
    >
      {/* Top Branding */}
      <div>
        <div className="h-16 px-5 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center flex-shrink-0 shadow-subtle">
              <Layers className="w-4 h-4" />
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <h1 className="text-sm font-bold text-text-primary tracking-tight leading-none truncate">
                  Job Hunter
                </h1>
                <span className="text-[10px] font-medium text-text-muted uppercase tracking-wider block mt-0.5">
                  Enterprise SaaS
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Sections */}
        <nav className="p-3 space-y-5 overflow-y-auto max-h-[calc(100vh-140px)]">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="space-y-1">
              {!collapsed && (
                <div className="px-2.5 pb-1 text-[11px] font-semibold text-text-muted tracking-wider uppercase">
                  {section.title}
                </div>
              )}
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive = activeView === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => handleItemClick(item.id)}
                    title={collapsed ? item.label : undefined}
                    className={cn(
                      'w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs sm:text-sm font-medium transition-colors',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
                      isActive
                        ? 'bg-primary-50 text-primary-700 font-semibold'
                        : 'text-text-secondary hover:bg-slate-100 hover:text-text-primary',
                      collapsed && 'justify-center px-0'
                    )}
                  >
                    <Icon className={cn('w-4 h-4 flex-shrink-0', isActive ? 'text-primary' : 'text-slate-500')} />
                    {!collapsed && (
                      <>
                        <span className="truncate flex-1 text-left">{item.label}</span>
                        {item.badge && (
                          <Badge variant="purple" className="text-[10px] py-0 px-1.5 ml-auto">
                            {item.badge}
                          </Badge>
                        )}
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* Bottom User Area */}
      <div className="p-3 border-t border-border bg-slate-50/60">
        {isAuthenticated ? (
          <div className="flex items-center justify-between gap-2.5">
            <div className="flex items-center gap-2.5 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-800 text-xs font-bold flex items-center justify-center flex-shrink-0 border border-primary-200">
                {monogram}
              </div>
              {!collapsed && (
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-semibold text-text-primary truncate block">
                      {displayName}
                    </span>
                    {isSuperuser && (
                      <Badge variant="purple" className="text-[9px] py-0 px-1">
                        Admin
                      </Badge>
                    )}
                  </div>
                  <span className="text-[11px] text-text-muted truncate block">
                    {currentUser?.email}
                  </span>
                </div>
              )}
            </div>
            {!collapsed && (
              <button
                onClick={logout}
                title="Đăng xuất"
                className="text-slate-400 hover:text-danger p-1 rounded-md hover:bg-red-50 transition-colors flex-shrink-0"
              >
                <LogOut className="w-4 h-4" />
                <span className="sr-only">Đăng xuất</span>
              </button>
            )}
          </div>
        ) : (
          !collapsed && (
            <div className="p-2.5 rounded-lg border border-dashed border-border bg-white space-y-2">
              <div className="flex items-center gap-2 text-xs text-text-secondary">
                <Shield className="w-3.5 h-3.5 text-text-muted" />
                <span>Khách vãng lai</span>
              </div>
              <Button
                variant="primary"
                size="xs"
                className="w-full justify-center"
                onClick={() => openAuthModal('login')}
              >
                <LogIn className="w-3.5 h-3.5" />
                <span>Đăng nhập</span>
              </Button>
            </div>
          )
        )}
      </div>
    </aside>
  );
};
