import React from 'react';
import { Menu, LogIn, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { ViewType } from './Sidebar';
import { getCompanyMonogram } from '../../utils/formatters';

export const VIEW_TITLES: Record<ViewType, { title: string; subtitle: string }> = {
  dashboard: {
    title: 'Tổng quan Dashboard',
    subtitle: 'Thống kê cơ hội việc làm, mức độ tương thích hồ sơ và tiến độ ứng tuyển.',
  },
  jobs: {
    title: 'Khám phá việc làm',
    subtitle: 'Tìm kiếm cơ hội IT đa nền tảng (ITViec, TopCV, Remotive, Upwork...).',
  },
  recommendations: {
    title: 'Đề xuất việc làm phù hợp',
    subtitle: 'Xếp hạng cơ hội tương thích cao nhất bằng thuật toán tất định 7 chỉ số.',
  },
  resume: {
    title: 'Hồ sơ tạo thiết kế',
    subtitle: 'Không gian biên dịch CV chuẩn ATS, đối soát Evidence Map và Cover Letter.',
  },
  applications: {
    title: 'Quản lý đơn nộp',
    subtitle: 'Theo dõi hành trình ứng tuyển và trạng thái phản hồi từ nhà tuyển dụng.',
  },
  profile: {
    title: 'Hồ sơ ứng viên',
    subtitle: 'Dữ liệu kỹ năng, kinh nghiệm và dự án làm nguồn tham chiếu duy nhất.',
  },
  system: {
    title: 'Hệ thống & Dữ liệu',
    subtitle: 'Cấu hình API Endpoint máy chủ, dọn dẹp cache và bảo trì cơ sở dữ liệu.',
  },
};

export interface TopbarProps {
  activeView: ViewType;
  onOpenMobileDrawer: () => void;
  onNavigateToJobs?: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({ activeView, onOpenMobileDrawer }) => {
  const { currentUser, isAuthenticated, openAuthModal } = useAuth();
  const titleInfo = VIEW_TITLES[activeView] || { title: 'Job Hunter', subtitle: '' };

  const displayName = currentUser?.full_name || currentUser?.email?.split('@')[0] || 'User';
  const monogram = getCompanyMonogram(displayName);

  return (
    <header className="h-16 px-4 sm:px-6 bg-surface border-b border-border flex items-center justify-between gap-4 sticky top-0 z-30">
      {/* Left: Mobile Toggle & Page Title */}
      <div className="flex items-center gap-3 min-w-0">
        <button
          onClick={onOpenMobileDrawer}
          className="lg:hidden p-2 rounded-md text-text-secondary hover:text-text-primary hover:bg-slate-100 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/40"
          aria-label="Mở menu điều hướng"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="min-w-0">
          <h2 className="text-sm sm:text-base font-semibold text-text-primary truncate leading-tight">
            {titleInfo.title}
          </h2>
        </div>
      </div>

      {/* Right: Status indicator & User control */}
      <div className="flex items-center gap-3 flex-shrink-0">
        {/* Backend live indicator */}
        <div
          className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium"
          title="Kết nối Backend hoạt động bình thường"
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>Hệ thống sẵn sàng</span>
        </div>

        {isAuthenticated ? (
          <div className="flex items-center gap-2 pl-2 border-l border-border">
            <div className="w-8 h-8 rounded-full bg-primary-100 text-primary-800 text-xs font-bold flex items-center justify-center border border-primary-200">
              {monogram}
            </div>
            <span className="hidden md:inline-block text-xs font-semibold text-text-primary truncate max-w-[120px]">
              {displayName}
            </span>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={() => openAuthModal('login')}
            className="text-xs sm:text-sm gap-1.5"
          >
            <LogIn className="w-3.5 h-3.5 text-primary" />
            <span className="hidden sm:inline">Đăng nhập</span>
            <span className="sm:hidden">Vào</span>
          </Button>
        )}
      </div>
    </header>
  );
};
