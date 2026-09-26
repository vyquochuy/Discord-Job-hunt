import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import * as jobsApi from '../api/jobs.api';
import * as matchesApi from '../api/matches.api';
import * as profileApi from '../api/profile.api';
import * as applicationsApi from '../api/applications.api';
import { TopRecommendation } from '../types/match';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { MetricCardSkeleton } from '../components/ui/skeleton';
import { EmptyState } from '../components/ui/empty-state';
import { MatchScoreBadge } from '../components/jobs/MatchScoreBadge';
import { getCompanyMonogram, getSourceBadgeInfo } from '../utils/formatters';
import {
  Briefcase,
  Award,
  Bookmark,
  Send,
  PlusCircle,
  RefreshCw,
  Search,
  ArrowRight,
  LogIn,
  UserPlus,
  Sparkles,
} from 'lucide-react';

export interface DashboardPageProps {
  onNavigate: (view: 'dashboard' | 'jobs' | 'recommendations' | 'resume' | 'applications' | 'profile' | 'system') => void;
  onOpenJobDetail: (jobId: string) => void;
  onOpenScanner: () => void;
  onOpenManualIngest: () => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  onNavigate,
  onOpenJobDetail,
  onOpenScanner,
  onOpenManualIngest,
}) => {
  const { isAuthenticated, openAuthModal } = useAuth();
  const { showToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [totalJobs, setTotalJobs] = useState(0);
  const [topRecs, setTopRecs] = useState<TopRecommendation[]>([]);
  const [savedCount, setSavedCount] = useState<number | null>(null);
  const [appsCount, setAppsCount] = useState<number | null>(null);

  const fetchDashboardData = useCallback(async () => {
    setLoading(true);
    try {
      // 1. Public jobs count
      try {
        const jobsRes = await jobsApi.getJobs({ page: 1, page_size: 5 });
        setTotalJobs(jobsRes.total || 0);
      } catch (e) {
        console.warn('Could not load public jobs for dashboard:', e);
      }

      // 2. Protected counts if authenticated
      if (isAuthenticated) {
        const [recs, saved, apps] = await Promise.all([
          matchesApi.getTopRecommendations(5).catch(() => []),
          jobsApi.getSavedJobs().catch(() => []),
          applicationsApi.getApplications(1, 10).catch(() => []),
        ]);

        setTopRecs(recs || []);
        setSavedCount(Array.isArray(saved) ? saved.length : 0);
        setAppsCount(Array.isArray(apps) ? apps.length : 0);
      } else {
        setTopRecs([]);
        setSavedCount(null);
        setAppsCount(null);
      }
    } catch (err: unknown) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleSyncContext = async () => {
    if (!isAuthenticated) {
      showToast('Vui lòng đăng nhập để đồng bộ hồ sơ ứng viên!', 'warning');
      openAuthModal('login', 'profile');
      return;
    }
    setSyncing(true);
    try {
      showToast('Đang đồng bộ hồ sơ từ context file...', 'info');
      const res = await profileApi.syncProfileFromContext();
      showToast(
        `Đã đồng bộ ${res.skills_imported} kỹ năng, ${res.experiences_imported} kinh nghiệm, ${res.projects_imported} dự án!`,
        'success'
      );
      fetchDashboardData();
    } catch (err: unknown) {
      const e = err as Error;
      showToast(`Đồng bộ thất bại: ${e.message}`, 'error');
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Tổng quan Dashboard"
        description="Thống kê cơ hội việc làm, mức độ tương thích hồ sơ và tiến độ ứng tuyển."
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={onOpenManualIngest}
              icon={<PlusCircle className="w-3.5 h-3.5" />}
            >
              <span>Nhập JD thủ công</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleSyncContext}
              loading={syncing}
              icon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              <span>Đồng bộ Context</span>
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={onOpenScanner}
              icon={<Search className="w-3.5 h-3.5" />}
            >
              <span>Quét tin tuyển dụng</span>
            </Button>
          </>
        }
      />

      {/* KPI Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading ? (
          <>
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
            <MetricCardSkeleton />
          </>
        ) : (
          <>
            {/* Metric 1: Total Jobs */}
            <Card className="p-4 sm:p-5 flex items-center gap-4 hover:border-slate-300 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0 border border-blue-100">
                <Briefcase className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <div className="text-2xl font-bold text-text-primary tracking-tight leading-none">
                  {totalJobs.toLocaleString('vi-VN')}
                </div>
                <div className="text-xs text-text-secondary mt-1 font-medium truncate">
                  Tin tuyển dụng đang theo dõi
                </div>
              </div>
            </Card>

            {/* Metric 2: Recommendations */}
            <Card className="p-4 sm:p-5 flex items-center gap-4 hover:border-slate-300 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0 border border-emerald-100">
                <Award className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <div className="text-2xl font-bold text-text-primary tracking-tight leading-none">
                  {isAuthenticated ? topRecs.length : '—'}
                </div>
                <div className="text-xs text-text-secondary mt-1 font-medium truncate">
                  {isAuthenticated ? 'Vị trí đề xuất hàng đầu' : 'Đăng nhập để xem đề xuất'}
                </div>
              </div>
            </Card>

            {/* Metric 3: Saved Jobs */}
            <Card className="p-4 sm:p-5 flex items-center gap-4 hover:border-slate-300 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center flex-shrink-0 border border-amber-100">
                <Bookmark className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <div className="text-2xl font-bold text-text-primary tracking-tight leading-none">
                  {isAuthenticated && savedCount !== null ? savedCount : '—'}
                </div>
                <div className="text-xs text-text-secondary mt-1 font-medium truncate">
                  {isAuthenticated ? 'Tin việc làm đã lưu' : 'Đăng nhập để xem'}
                </div>
              </div>
            </Card>

            {/* Metric 4: Applications Count */}
            <Card className="p-4 sm:p-5 flex items-center gap-4 hover:border-slate-300 transition-colors">
              <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center flex-shrink-0 border border-purple-100">
                <Send className="w-6 h-6" />
              </div>
              <div className="min-w-0">
                <div className="text-2xl font-bold text-text-primary tracking-tight leading-none">
                  {isAuthenticated && appsCount !== null ? appsCount : '—'}
                </div>
                <div className="text-xs text-text-secondary mt-1 font-medium truncate">
                  {isAuthenticated ? 'Hồ sơ đã nộp' : 'Đăng nhập để xem'}
                </div>
              </div>
            </Card>
          </>
        )}
      </div>

      {/* Top Recommendations Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-base sm:text-lg font-bold text-text-primary leading-tight">
              Đề xuất ứng tuyển hàng đầu
            </h2>
            <p className="text-xs text-text-secondary mt-0.5">
              Các cơ hội có điểm tương thích cao nhất dựa trên phân tích hồ sơ và thị trường.
            </p>
          </div>
          {isAuthenticated && topRecs.length > 0 && (
            <Button
              variant="outline"
              size="xs"
              onClick={() => onNavigate('recommendations')}
              icon={<ArrowRight className="w-3.5 h-3.5" />}
            >
              <span>Xem tất cả ({topRecs.length})</span>
            </Button>
          )}
        </div>

        {!isAuthenticated ? (
          <EmptyState
            icon={<Sparkles className="w-6 h-6 text-primary" />}
            title="Đăng nhập để nhận Đề xuất việc làm phù hợp"
            description="Hệ thống AI sẽ đối soát hồ sơ và kỹ năng của bạn với các tin tuyển dụng để tính điểm tương thích 7 chỉ số tất định chuẩn xác."
            action={
              <>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => openAuthModal('login')}
                  icon={<LogIn className="w-3.5 h-3.5" />}
                >
                  <span>Đăng nhập ngay</span>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openAuthModal('register')}
                  icon={<UserPlus className="w-3.5 h-3.5" />}
                >
                  <span>Tạo tài khoản mới</span>
                </Button>
              </>
            }
          />
        ) : topRecs.length === 0 ? (
          <EmptyState
            icon={<Briefcase className="w-6 h-6 text-slate-400" />}
            title="Chưa có dữ liệu đề xuất việc làm"
            description="Nhấn nút 'Quét tin tuyển dụng' để tự động thu thập và đối soát điểm tương thích cho hồ sơ của bạn."
            action={
              <Button
                variant="primary"
                size="sm"
                onClick={onOpenScanner}
                icon={<Search className="w-3.5 h-3.5" />}
              >
                <span>Quét tin tuyển dụng ngay</span>
              </Button>
            }
          />
        ) : (
          <div className="space-y-3">
            {topRecs.map((rec) => {
              const monogram = getCompanyMonogram(rec.company_name);
              const sourceInfo = getSourceBadgeInfo(rec.source);

              return (
                <Card
                  key={rec.job_id}
                  hoverable
                  onClick={() => onOpenJobDetail(rec.job_id)}
                  className="p-4 sm:p-4.5 cursor-pointer flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3.5 transition-all"
                >
                  <div className="flex items-start gap-3.5 min-w-0 flex-1">
                    <div className="w-10 h-10 rounded-lg bg-slate-100 text-slate-700 font-bold text-xs flex items-center justify-center flex-shrink-0 border border-slate-200 mt-0.5">
                      {monogram}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-sm font-semibold text-text-primary hover:text-primary transition-colors truncate">
                          {rec.title}
                        </h4>
                        <span
                          className={`text-[10px] font-medium px-2 py-0.5 rounded border ${sourceInfo.colorClass}`}
                        >
                          {sourceInfo.label}
                        </span>
                      </div>

                      <div className="text-xs text-text-secondary mt-1 flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-slate-700">{rec.company_name}</span>
                        <span>•</span>
                        <span>{rec.location || 'Việt Nam'}</span>
                        <span>•</span>
                        <span>{rec.work_mode || 'Flexible'}</span>
                      </div>

                      {rec.recommendation && (
                        <div className="text-[11px] text-primary font-medium mt-1 flex items-center gap-1">
                          <span>{rec.recommendation}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-3 flex-shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-border">
                    <MatchScoreBadge score={rec.score} eligibility={rec.eligibility} size="md" showEligibility />
                    <Button
                      variant="outline"
                      size="xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpenJobDetail(rec.job_id);
                      }}
                      className="text-xs"
                    >
                      Chi tiết
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
