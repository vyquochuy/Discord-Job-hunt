import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import * as matchesApi from '../api/matches.api';
import { TopRecommendation } from '../types/match';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { EmptyState } from '../components/ui/empty-state';
import { MatchScoreBadge } from '../components/jobs/MatchScoreBadge';
import { getCompanyMonogram, getSourceBadgeInfo } from '../utils/formatters';
import {
  Sparkles,
  Search,
  LogIn,
  UserPlus,
  ChevronRight,
  Loader2,
} from 'lucide-react';

export interface RecommendationsPageProps {
  onOpenJobDetail: (jobId: string) => void;
  onOpenScanner: () => void;
}

export const RecommendationsPage: React.FC<RecommendationsPageProps> = ({
  onOpenJobDetail,
  onOpenScanner,
}) => {
  const { isAuthenticated, openAuthModal } = useAuth();
  const { showToast } = useToast();

  const [recommendations, setRecommendations] = useState<TopRecommendation[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchRecommendations = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const recs = await matchesApi.getTopRecommendations(30);
      setRecommendations(recs || []);
    } catch (err: unknown) {
      const e = err as Error;
      showToast(`Không thể tải bảng đề xuất: ${e.message}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, showToast]);

  useEffect(() => {
    fetchRecommendations();
  }, [fetchRecommendations]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Đề xuất việc làm phù hợp"
        description="Phân tích mức độ phù hợp dựa trên thuật toán 7 chỉ số tất định (Deterministic 7-Signal Matching Engine) và bộ lọc điều kiện cứng."
        actions={
          isAuthenticated && (
            <Button
              variant="primary"
              size="sm"
              onClick={onOpenScanner}
              icon={<Search className="w-3.5 h-3.5" />}
            >
              <span>Quét lại đề xuất</span>
            </Button>
          )
        }
      />

      {!isAuthenticated ? (
        <EmptyState
          icon={<Sparkles className="w-6 h-6 text-primary" />}
          title="Yêu cầu Đăng nhập"
          description="Bảng xếp hạng đề xuất việc làm cần liên kết với hồ sơ ứng viên cá nhân của bạn để đối soát các tín hiệu tương thích và tư cách ứng tuyển (Eligibility)."
          action={
            <div className="flex gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={() => openAuthModal('login', 'recommendations')}
                icon={<LogIn className="w-3.5 h-3.5" />}
              >
                <span>Đăng nhập</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => openAuthModal('register', 'recommendations')}
                icon={<UserPlus className="w-3.5 h-3.5" />}
              >
                <span>Tạo tài khoản</span>
              </Button>
            </div>
          }
        />
      ) : loading ? (
        <div className="py-16 flex flex-col items-center justify-center gap-3 text-text-muted">
          <Loader2 className="w-7 h-7 text-primary animate-spin" />
          <p className="text-sm font-medium">Đang đối soát hồ sơ và xếp hạng vị trí tương thích...</p>
        </div>
      ) : recommendations.length === 0 ? (
        <EmptyState
          icon={<Sparkles className="w-6 h-6 text-slate-400" />}
          title="Chưa có dữ liệu bảng xếp hạng đề xuất"
          description="Hãy chạy tiến trình quét tin tuyển dụng để hệ thống đối soát dữ liệu hồ sơ và tạo danh sách tương thích cao nhất."
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
          {recommendations.map((rec, idx) => {
            const monogram = getCompanyMonogram(rec.company_name);
            const sourceInfo = getSourceBadgeInfo(rec.source);

            return (
              <Card
                key={rec.job_id}
                hoverable
                onClick={() => onOpenJobDetail(rec.job_id)}
                className="p-4 sm:p-5 cursor-pointer flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 transition-all"
              >
                <div className="flex items-start gap-3.5 min-w-0 flex-1">
                  {/* Rank badge */}
                  <div className="w-8 text-center text-base sm:text-lg font-bold text-slate-400 flex-shrink-0 pt-0.5">
                    #{idx + 1}
                  </div>

                  <div className="w-10 h-10 rounded-lg bg-slate-100 text-slate-700 font-bold text-xs flex items-center justify-center flex-shrink-0 border border-slate-200 mt-0.5">
                    {monogram}
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm sm:text-base font-semibold text-text-primary hover:text-primary transition-colors truncate">
                        {rec.title}
                      </h3>
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
                      <p className="text-[11px] text-text-muted mt-1 leading-snug">
                        {rec.recommendation}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-3 flex-shrink-0 pt-3 sm:pt-0 border-t sm:border-t-0 border-border">
                  <MatchScoreBadge score={rec.score} eligibility={rec.eligibility} size="md" showEligibility />
                  <Button
                    variant="primary"
                    size="xs"
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpenJobDetail(rec.job_id);
                    }}
                    className="text-xs gap-1"
                  >
                    <span>Phân tích</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};
