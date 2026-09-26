import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import * as jobsApi from '../../api/jobs.api';
import * as matchesApi from '../../api/matches.api';
import { JobDetail } from '../../types/job';
import { JobMatch } from '../../types/match';
import { formatCurrency, getCompanyMonogram, getSourceBadgeInfo } from '../../utils/formatters';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogBody,
  DialogFooter,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { MatchScoreBadge } from './MatchScoreBadge';
import {
  MapPin,
  Laptop,
  Layers,
  DollarSign,
  Mail,
  ExternalLink,
  Bookmark,
  RefreshCw,
  FileText,
  Send,
  Loader2,
  Check,
  Target,
  Sparkles,
} from 'lucide-react';

export interface JobDetailModalProps {
  jobId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTailorResume?: (jobId: string) => void;
  onApplyJob?: (jobId: string) => void;
}

const SIGNAL_NAME_MAP: Record<string, string> = {
  requirement_fit: 'Yêu cầu cốt lõi',
  technical_skill_match: 'Kỹ năng kỹ thuật',
  project_relevance: 'Dự án liên quan',
  experience_relevance: 'Kinh nghiệm',
  education_match: 'Học vấn',
  seniority_match: 'Cấp bậc',
  work_fit: 'Hình thức làm việc',
};

const DEFAULT_SIGNAL_NAMES = [
  'Yêu cầu cốt lõi',
  'Kỹ năng kỹ thuật',
  'Dự án liên quan',
  'Kinh nghiệm',
  'Học vấn',
  'Cấp bậc',
  'Hình thức làm việc',
];

export const JobDetailModal: React.FC<JobDetailModalProps> = ({
  jobId,
  open,
  onOpenChange,
  onTailorResume,
  onApplyJob,
}) => {
  const { currentUser, openAuthModal } = useAuth();
  const { showToast } = useToast();

  const [loading, setLoading] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [job, setJob] = useState<JobDetail | null>(null);
  const [match, setMatch] = useState<JobMatch | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const [jobData, matchData] = await Promise.all([
        jobsApi.getJobDetail(jobId),
        matchesApi.getMatchDetail(jobId).catch(() => null),
      ]);
      setJob(jobData);
      setMatch(matchData);
    } catch (err: unknown) {
      const e = err as Error;
      setError(e.message || 'Không thể tải thông tin công việc');
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (open && jobId) {
      fetchDetail();
    } else {
      setJob(null);
      setMatch(null);
      setError(null);
    }
  }, [open, jobId, fetchDetail]);

  const handleRecalculateMatch = async () => {
    if (!jobId) return;
    if (!currentUser) {
      showToast('Vui lòng đăng nhập để tính toán điểm tương thích hồ sơ!', 'warning');
      openAuthModal('login');
      return;
    }
    setCalculating(true);
    try {
      showToast('Đang tính toán lại điểm tương thích 7 chỉ số...', 'info');
      const updatedMatch = await matchesApi.calculateMatch(jobId, true);
      setMatch(updatedMatch);
      showToast('Đã cập nhật điểm phù hợp thành công!', 'success');
    } catch (err: unknown) {
      const e = err as Error;
      showToast(`Lỗi tính điểm: ${e.message}`, 'error');
    } finally {
      setCalculating(false);
    }
  };

  const handleSaveJob = async () => {
    if (!jobId) return;
    if (!currentUser) {
      showToast('Vui lòng đăng nhập để lưu tin tuyển dụng!', 'warning');
      openAuthModal('login');
      return;
    }
    setSaving(true);
    try {
      await jobsApi.saveJob(jobId, 'Lưu từ SaaS Web App');
      showToast('Đã lưu công việc vào danh sách theo dõi!', 'success');
    } catch (err: unknown) {
      const e = err as Error;
      showToast(`Không thể lưu tin: ${e.message}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  const salaryText =
    job?.min_salary || job?.max_salary
      ? `${formatCurrency(job.min_salary, job.salary_currency)} - ${formatCurrency(job.max_salary, job.salary_currency)}`
      : 'Thỏa thuận';

  const sourceInfo = getSourceBadgeInfo(job?.source);

  // Parsing signals
  const rawSignals = match?.signals;
  const signalList: { key: string; name: string; score: number }[] = [];

  if (Array.isArray(rawSignals)) {
    rawSignals.forEach((sig, idx) => {
      const name = (sig as { name?: string }).name || DEFAULT_SIGNAL_NAMES[idx] || `Chỉ số ${idx + 1}`;
      signalList.push({
        key: `sig-${idx}`,
        name: SIGNAL_NAME_MAP[name] || name,
        score: typeof (sig as { score?: number }).score === 'number' ? (sig as { score: number }).score : 0,
      });
    });
  } else if (rawSignals && typeof rawSignals === 'object') {
    Object.entries(rawSignals).forEach(([k, v], idx) => {
      const score = typeof v === 'number' ? v : (v as { score?: number })?.score ?? 0;
      const rawName = (typeof v === 'object' && v && 'name' in v && (v as { name?: string }).name)
        ? (v as { name: string }).name
        : k;
      const displayName =
        SIGNAL_NAME_MAP[rawName] ||
        DEFAULT_SIGNAL_NAMES[idx] ||
        String(rawName).replace(/_/g, ' ');

      signalList.push({
        key: k,
        name: displayName,
        score,
      });
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="xl" className="max-h-[88vh]">
        <DialogHeader className="pb-3">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              <div className="w-10 h-10 rounded-lg bg-slate-100 text-slate-700 font-bold text-sm flex items-center justify-center flex-shrink-0 border border-slate-200 mt-0.5">
                {getCompanyMonogram(job?.company_name)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <DialogTitle className="text-base sm:text-lg">
                    {loading ? 'Đang tải thông tin chi tiết...' : job?.title}
                  </DialogTitle>
                  {job?.source && (
                    <span className={`text-[11px] font-medium px-2 py-0.5 rounded border ${sourceInfo.colorClass}`}>
                      {sourceInfo.label}
                    </span>
                  )}
                </div>
                <DialogDescription className="text-xs sm:text-sm font-medium text-text-secondary mt-0.5">
                  {job?.company_name} • {job?.location || 'Việt Nam'}
                </DialogDescription>
              </div>
            </div>

            {match && (
              <div className="flex-shrink-0 text-right">
                <MatchScoreBadge score={match.score} eligibility={match.eligibility} size="lg" showEligibility />
              </div>
            )}
          </div>
        </DialogHeader>

        <DialogBody className="space-y-5">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-text-muted">
              <Loader2 className="w-7 h-7 text-primary animate-spin" />
              <p className="text-sm font-medium">Đang tải chi tiết công việc và phân tích tương thích...</p>
            </div>
          ) : error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-danger text-center">
              {error}
            </div>
          ) : job ? (
            <>
              {/* Match Intelligence Section (If present) */}
              {match ? (
                <div className="p-4 sm:p-5 rounded-lg bg-primary-50/50 border border-primary-100 space-y-3.5">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-primary" />
                      <span className="text-xs font-bold text-primary-900 tracking-wider uppercase">
                        ĐIỂM TƯƠNG THÍCH 7 CHỈ SỐ TẤT ĐỊNH
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs text-primary font-medium">
                      <Target className="w-3.5 h-3.5" />
                      <span>{match.recommendation || 'Đề xuất ứng tuyển'}</span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                    {/* 7 signals bars */}
                    <div className="space-y-2 bg-white p-3.5 rounded-lg border border-primary-100/80">
                      <div className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-2">
                        Bảng phân tích 7 chỉ số
                      </div>
                      {signalList.map((sig) => {
                        const percent = Math.min(100, Math.max(0, sig.score * 100));

                        return (
                          <div key={sig.key}>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-700 font-medium">{sig.name}</span>
                              <span className="font-semibold text-text-primary">{Math.round(percent)}%</span>
                            </div>
                            <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
                              <div
                                className="h-full bg-primary rounded-full transition-all duration-300"
                                style={{ width: `${percent}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Evidence summary */}
                    <div className="space-y-2 bg-white p-3.5 rounded-lg border border-primary-100/80 flex flex-col">
                      <div className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-1">
                        Tổng hợp bằng chứng đối soát
                      </div>
                      <div className="text-xs text-text-secondary leading-relaxed overflow-y-auto max-h-[190px] flex-1 pr-1">
                        {match.explanation_text ? (
                          <p className="whitespace-pre-wrap">{match.explanation_text}</p>
                        ) : (
                          <p className="text-text-muted italic">Chưa có phân tích bằng chứng chi tiết.</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between gap-3">
                  <p className="text-xs text-text-secondary">
                    Chưa có kết quả phân tích 7 chỉ số tương thích cho vị trí này.
                  </p>
                  <Button
                    variant="outline"
                    size="xs"
                    onClick={handleRecalculateMatch}
                    loading={calculating}
                    icon={<RefreshCw className="w-3 h-3" />}
                  >
                    Tính điểm phù hợp
                  </Button>
                </div>
              )}

              {/* Job Metadata Pills */}
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant="slate" icon={<MapPin className="w-3 h-3" />}>
                  {job.location || 'Việt Nam'}
                </Badge>
                <Badge variant="primary" icon={<Laptop className="w-3 h-3" />}>
                  {job.work_mode || 'ONSITE'}
                </Badge>
                <Badge variant="slate" icon={<Layers className="w-3 h-3" />}>
                  {job.level || 'All Levels'}
                </Badge>
                {(job.min_salary || job.max_salary) && (
                  <Badge variant="success" icon={<DollarSign className="w-3 h-3" />}>
                    {salaryText}
                  </Badge>
                )}
                {job.contact_email && (
                  <Badge variant="slate" icon={<Mail className="w-3 h-3" />}>
                    {job.contact_email}
                  </Badge>
                )}
                {job.source_url && (
                  <a
                    href={job.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline ml-auto font-medium"
                  >
                    <span>Bài đăng gốc</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>

              {/* Extracted Canonical Skills */}
              {job.skills && job.skills.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                    Kỹ năng chuẩn hóa trích xuất
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {job.skills.map((s) => (
                      <span
                        key={s.id}
                        className={`inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-md font-medium border ${
                          s.is_required
                            ? 'bg-primary-50 text-primary-800 border-primary-200'
                            : 'bg-slate-50 text-slate-700 border-slate-200'
                        }`}
                      >
                        {s.canonical_name || 'Skill'}
                        {s.is_required && <Check className="w-3 h-3 text-primary-600" />}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Full Description */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-text-primary uppercase tracking-wider">
                  Mô tả công việc chi tiết (JD)
                </h4>
                <div className="p-4 bg-slate-50 border border-border rounded-lg text-xs sm:text-sm text-text-primary leading-relaxed max-h-[300px] overflow-y-auto whitespace-pre-wrap font-sans">
                  {job.description || 'Không có nội dung mô tả.'}
                </div>
              </div>
            </>
          ) : null}
        </DialogBody>

        <DialogFooter className="flex-wrap sm:flex-nowrap gap-2 justify-between">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSaveJob}
              loading={saving}
              icon={<Bookmark className="w-3.5 h-3.5" />}
            >
              <span>Lưu tin</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRecalculateMatch}
              loading={calculating}
              icon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              <span>Tính lại điểm</span>
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                if (jobId && onTailorResume) {
                  onTailorResume(jobId);
                }
              }}
              icon={<FileText className="w-3.5 h-3.5" />}
            >
              <span>tạo thiết kế hồ sơ</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (jobId && onApplyJob) {
                  onApplyJob(jobId);
                } else {
                  showToast('Tính năng nộp hồ sơ tự động đang sẵn sàng cho công việc này.', 'info');
                }
              }}
              icon={<Send className="w-3.5 h-3.5 text-emerald-600" />}
            >
              <span>Nộp đơn</span>
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
