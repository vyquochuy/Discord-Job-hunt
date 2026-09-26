import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import * as resumeApi from '../api/resume.api';
import * as jobsApi from '../api/jobs.api';
import { TailoredResume, TailoredResumeSummary } from '../types/resume';
import { JobDetail } from '../types/job';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../components/ui/tabs';
import { EmptyState } from '../components/ui/empty-state';
import {
  formatDate,
  getCompanyMonogram,
  getSourceBadgeInfo,
  convertMarkdownToCleanEmail,
} from '../utils/formatters';
import {
  FileText,
  Download,
  Copy,
  Mail,
  Trash2,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  ArrowLeft,
  ShieldCheck,
  Loader2,
  Plus,
  Eye,
  Code,
} from 'lucide-react';

export interface ResumePageProps {
  resumeId?: string | null;
  onSelectResumeId: (id: string | null) => void;
  onNavigateToJobs: () => void;
  onOpenJobDetail: (jobId: string) => void;
}

export const ResumePage: React.FC<ResumePageProps> = ({
  resumeId,
  onSelectResumeId,
  onNavigateToJobs,
  onOpenJobDetail,
}) => {
  const { isAuthenticated, openAuthModal, currentUser } = useAuth();
  const { showToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [resumes, setResumes] = useState<TailoredResumeSummary[]>([]);
  const [activeResume, setActiveResume] = useState<TailoredResume | null>(null);
  const [activeJob, setActiveJob] = useState<JobDetail | null>(null);

  // Workspace sub-tabs
  const [workspaceTab, setWorkspaceTab] = useState<'preview' | 'latex' | 'evidence' | 'coverletter'>('preview');
  const [latexDraft, setLatexDraft] = useState('');
  const [savingLatex, setSavingLatex] = useState(false);

  // Fetch Resume Hub List
  const fetchResumeHub = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const list = await resumeApi.getTailoredResumes();
      setResumes(list || []);
    } catch (err: unknown) {
      const e = err as Error;
      showToast(`Không thể tải kho lưu trữ CV: ${e.message}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, showToast]);

  // Fetch Specific Resume for Workspace
  const fetchResumeDetail = useCallback(async (id: string) => {
    setLoading(true);
    try {
      const res = await resumeApi.getTailoredResumeById(id);
      setActiveResume(res);
      setLatexDraft(res.latex_source || '');

      // Load Job detail for header banner
      if (res.job_id) {
        try {
          const job = await jobsApi.getJobDetail(res.job_id);
          setActiveJob(job);
        } catch (_) {}
      }
    } catch (err: unknown) {
      const e = err as Error;
      showToast(`Không thể tải không gian làm việc CV: ${e.message}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [showToast]);

  useEffect(() => {
    if (resumeId) {
      fetchResumeDetail(resumeId);
    } else {
      setActiveResume(null);
      setActiveJob(null);
      fetchResumeHub();
    }
  }, [resumeId, fetchResumeHub, fetchResumeDetail]);

  const handleDeleteResume = async (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!confirm('Bạn có chắc chắn muốn xóa bản CV tạo thiết kế này?')) return;

    try {
      showToast('Đang xóa bản CV...', 'info');
      await resumeApi.deleteTailoredResumeById(id);
      showToast('Đã xóa thành công bản CV!', 'success');
      if (resumeId === id) {
        onSelectResumeId(null);
      } else {
        fetchResumeHub();
      }
    } catch (err: unknown) {
      const error = err as Error;
      showToast(`Lỗi xóa CV: ${error.message}`, 'error');
    }
  };

  const handleSaveAndRecompile = async () => {
    if (!activeResume) return;
    setSavingLatex(true);
    try {
      showToast('Đang lưu và biên dịch lại PDF...', 'info');
      const updated = await resumeApi.updateResumeLatex(activeResume.id, latexDraft);
      setActiveResume(updated);
      showToast('Đã lưu và biên dịch lại PDF thành công!', 'success');
      setWorkspaceTab('preview');
    } catch (err: unknown) {
      const e = err as Error;
      showToast(`Lỗi biên dịch LaTeX: ${e.message}`, 'error');
    } finally {
      setSavingLatex(false);
    }
  };

  const handleCopyLatex = () => {
    navigator.clipboard.writeText(latexDraft);
    showToast('Đã sao chép mã nguồn LaTeX vào Clipboard!', 'success');
  };

  const handleCopyCleanEmail = () => {
    if (!activeResume?.cover_letter?.content_markdown) return;
    const { body } = convertMarkdownToCleanEmail(
      activeResume.cover_letter.content_markdown,
      currentUser?.full_name || '',
      activeResume.target_title || '',
      activeResume.cover_letter.company_name || ''
    );
    navigator.clipboard.writeText(body);
    showToast('Đã sao chép nội dung thư sạch (sẵn sàng dán trực tiếp vào Email)!', 'success');
  };

  const handleOpenMailClient = () => {
    if (!activeResume?.cover_letter?.content_markdown) return;
    const { subject, body } = convertMarkdownToCleanEmail(
      activeResume.cover_letter.content_markdown,
      currentUser?.full_name || '',
      activeResume.target_title || '',
      activeResume.cover_letter.company_name || ''
    );
    const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.open(mailto, '_blank');
  };

  if (!isAuthenticated) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Hồ sơ tạo thiết kế"
          description="Không gian biên dịch CV chuẩn ATS, đối soát Evidence Map và Cover Letter."
        />
        <EmptyState
          icon={<FileText className="w-6 h-6 text-primary" />}
          title="Yêu cầu Đăng nhập"
          description="Vui lòng đăng nhập tài khoản để quản lý các bản CV đã tối ưu riêng biệt cho từng tin tuyển dụng."
          action={
            <Button
              variant="primary"
              size="sm"
              onClick={() => openAuthModal('login', 'resume')}
            >
              Đăng nhập ngay
            </Button>
          }
        />
      </div>
    );
  }

  // View 1: Specific Resume Workspace
  if (activeResume) {
    const pdfUrl = resumeApi.getResumePdfUrl(activeResume.id, false);
    const pdfDownloadUrl = resumeApi.getResumePdfUrl(activeResume.id, true);
    const jobTitle = activeJob?.title || activeResume.target_title || 'Vị trí Ứng tuyển';
    const companyName = activeJob?.company_name || activeResume.cover_letter?.company_name || 'Công ty Tuyển dụng';
    const monogram = getCompanyMonogram(companyName);
    const sourceInfo = getSourceBadgeInfo(activeJob?.source);

    return (
      <div className="space-y-6">
        {/* Workspace Header Banner */}
        <Card className="p-4 sm:p-5 border-l-4 border-l-primary bg-gradient-to-br from-white to-slate-50">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-start gap-3.5 min-w-0 flex-1">
              <div className="w-12 h-12 rounded-lg bg-primary text-white text-sm font-bold flex items-center justify-center flex-shrink-0 shadow-subtle">
                {monogram}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-base sm:text-lg font-bold text-text-primary truncate">
                    {jobTitle}
                  </h2>
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${sourceInfo.colorClass}`}>
                    {sourceInfo.label}
                  </span>
                  <Badge variant="success" icon={<ShieldCheck className="w-3 h-3" />}>
                    {Math.round(activeResume.provenance_score * 100)}% Provenance
                  </Badge>
                </div>
                <div className="text-xs sm:text-sm font-semibold text-primary mt-1">
                  {companyName} • {activeJob?.location || 'Việt Nam'}
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 flex-wrap flex-shrink-0">
              <Button
                variant="outline"
                size="xs"
                onClick={() => onSelectResumeId(null)}
                icon={<ArrowLeft className="w-3.5 h-3.5" />}
              >
                <span>Kho lưu trữ CV</span>
              </Button>
              {activeResume.job_id && (
                <Button
                  variant="outline"
                  size="xs"
                  onClick={() => onOpenJobDetail(activeResume.job_id)}
                  icon={<ExternalLink className="w-3.5 h-3.5" />}
                >
                  <span>Xem JD</span>
                </Button>
              )}
              <a
                href={pdfDownloadUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 h-7 px-2.5 text-xs font-medium rounded-md bg-primary text-white hover:bg-primary-hover shadow-subtle"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Tải PDF CV</span>
              </a>
            </div>
          </div>
        </Card>

        {/* Workspace Navigation Tabs */}
        <div className="space-y-4">
          <Tabs value={workspaceTab} onValueChange={(v: string) => setWorkspaceTab(v as typeof workspaceTab)}>
            <TabsList className="w-full sm:w-auto grid grid-cols-4 sm:inline-flex">
              <TabsTrigger value="preview" className="gap-1.5 text-xs sm:text-sm">
                <Eye className="w-3.5 h-3.5" />
                <span>Bản xem PDF</span>
              </TabsTrigger>
              <TabsTrigger value="latex" className="gap-1.5 text-xs sm:text-sm">
                <Code className="w-3.5 h-3.5" />
                <span>Mã LaTeX</span>
              </TabsTrigger>
              <TabsTrigger value="evidence" className="gap-1.5 text-xs sm:text-sm">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Evidence Map</span>
              </TabsTrigger>
              <TabsTrigger value="coverletter" className="gap-1.5 text-xs sm:text-sm">
                <Mail className="w-3.5 h-3.5" />
                <span>Cover Letter</span>
              </TabsTrigger>
            </TabsList>

            {/* Tab 1: PDF Preview */}
            <TabsContent value="preview" className="mt-4">
              <Card className="p-0 overflow-hidden bg-slate-100 flex flex-col items-center">
                <div className="w-full h-11 px-4 bg-white border-b border-border flex items-center justify-between text-xs text-text-secondary">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-text-primary">Bản in chuẩn ATS 1 Trang</span>
                    <span className="text-text-muted">• pdflatex Engine</span>
                  </div>
                  <a
                    href={pdfDownloadUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline font-medium inline-flex items-center gap-1"
                  >
                    <span>Mở tệp gốc</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="w-full h-[680px]">
                  <iframe
                    src={pdfUrl}
                    title="Bản xem trước PDF CV"
                    className="w-full h-full border-none"
                  />
                </div>
              </Card>
            </TabsContent>

            {/* Tab 2: LaTeX Code Editor */}
            <TabsContent value="latex" className="mt-4 space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div className="text-xs text-text-secondary">
                  Bạn có thể chỉnh sửa trực tiếp mã nguồn LaTeX bên dưới và nhấn{' '}
                  <strong>Lưu & Biên dịch</strong> để cập nhật lại tệp PDF.
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="xs" onClick={handleCopyLatex} icon={<Copy className="w-3.5 h-3.5" />}>
                    <span>Sao chép TeX</span>
                  </Button>
                  <Button
                    variant="primary"
                    size="xs"
                    onClick={handleSaveAndRecompile}
                    loading={savingLatex}
                    icon={<RefreshCw className="w-3.5 h-3.5" />}
                  >
                    <span>Lưu & Biên dịch PDF</span>
                  </Button>
                </div>
              </div>

              <textarea
                rows={22}
                value={latexDraft}
                onChange={(e) => setLatexDraft(e.target.value)}
                className="w-full p-4 font-mono text-xs sm:text-sm bg-slate-900 text-slate-100 rounded-lg focus:outline-none focus:ring-1 focus:ring-primary leading-relaxed shadow-inner"
                spellCheck={false}
              />
            </TabsContent>

            {/* Tab 3: Evidence Map */}
            <TabsContent value="evidence" className="mt-4 space-y-3">
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-900 leading-relaxed">
                <strong>Bảo chứng Fact-Checking:</strong> Mọi bullet point và claim trong CV đều được đối soát với
                hồ sơ gốc của ứng viên để đảm bảo <strong>không có ảo giác (Zero Hallucination)</strong>.
              </div>

              {activeResume.evidence_items && activeResume.evidence_items.length > 0 ? (
                <div className="border border-border rounded-lg overflow-x-auto bg-white shadow-card">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-border text-text-secondary uppercase font-semibold">
                      <tr>
                        <th className="p-3">Phần mục</th>
                        <th className="p-3">Nội dung Claim trong CV</th>
                        <th className="p-3">Bằng chứng gốc (Fact)</th>
                        <th className="p-3 text-right">Độ khớp</th>
                        <th className="p-3 text-center">Trạng thái</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {activeResume.evidence_items.map((item, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/50">
                          <td className="p-3 font-semibold text-text-primary whitespace-nowrap">
                            {item.section}
                          </td>
                          <td className="p-3 max-w-xs text-slate-700 leading-relaxed font-sans">
                            {item.claim_text}
                          </td>
                          <td className="p-3 max-w-xs text-text-muted leading-relaxed font-sans">
                            {item.original_fact}
                          </td>
                          <td className="p-3 text-right font-mono font-bold text-slate-700 whitespace-nowrap">
                            {Math.round((item.similarity_score || 1) * 100)}%
                          </td>
                          <td className="p-3 text-center whitespace-nowrap">
                            {item.is_verified ? (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                                <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                                Xác thực
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                                Cần lưu ý
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <EmptyState
                  title="Chưa có dữ liệu Evidence Map chi tiết"
                  description="Bản CV này được biên dịch theo cấu trúc chuẩn xác hoặc chưa phát sinh claim phức tạp."
                />
              )}
            </TabsContent>

            {/* Tab 4: Cover Letter */}
            <TabsContent value="coverletter" className="mt-4 space-y-4">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <span className="text-xs text-text-secondary">
                  Thư xin việc được cá nhân hóa đồng nhất với tin tuyển dụng của công ty.
                </span>
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="xs" onClick={handleCopyCleanEmail} icon={<Copy className="w-3.5 h-3.5" />}>
                    <span>Sao chép thư sạch</span>
                  </Button>
                  <Button variant="primary" size="xs" onClick={handleOpenMailClient} icon={<Mail className="w-3.5 h-3.5" />}>
                    <span>Gửi qua Mail Client</span>
                  </Button>
                </div>
              </div>

              {activeResume.cover_letter?.content_markdown ? (
                <Card className="p-5 sm:p-6 bg-white font-sans text-xs sm:text-sm text-text-primary leading-relaxed whitespace-pre-wrap">
                  {activeResume.cover_letter.content_markdown}
                </Card>
              ) : (
                <EmptyState
                  title="Chưa có Thư xin việc (Cover Letter)"
                  description="Thư xin việc sẽ tự động sinh khi bạn thực hiện tái tạo hồ sơ với tùy chọn Cover Letter."
                />
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    );
  }

  // View 2: Resume Hub Grid List
  return (
    <div className="space-y-6">
      <PageHeader
        title="Kho lưu trữ Hồ sơ tạo thiết kế (Resume Hub)"
        description={`Toàn bộ ${resumes.length} bản CV LaTeX và PDF đã được tối ưu hóa riêng biệt theo từng tin tuyển dụng.`}
        actions={
          <Button variant="primary" size="sm" onClick={onNavigateToJobs} icon={<Plus className="w-3.5 h-3.5" />}>
            <span>Tạo thêm CV từ việc làm</span>
          </Button>
        }
      />

      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center gap-3 text-text-muted">
          <Loader2 className="w-7 h-7 text-primary animate-spin" />
          <p className="text-sm font-medium">Đang tải danh sách hồ sơ tạo thiết kế...</p>
        </div>
      ) : resumes.length === 0 ? (
        <EmptyState
          icon={<FileText className="w-6 h-6 text-slate-400" />}
          title="Bạn chưa có bản CV tạo thiết kế nào"
          description="Hãy chọn một công việc trong mục Khám phá việc làm và nhấn 'tạo thiết kế hồ sơ' để hệ thống tự động sinh bản CV LaTeX ATS tối ưu."
          action={
            <Button variant="primary" size="sm" onClick={onNavigateToJobs}>
              Khám phá việc làm ngay
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {resumes.map((item) => {
            const pdfDownloadUrl = resumeApi.getResumePdfUrl(item.id, true);
            const title = item.target_title || item.job?.title || 'Vị trí Ứng tuyển';
            const company = item.job?.company_name || 'Công ty Tuyển dụng';
            const monogram = getCompanyMonogram(company);

            return (
              <Card
                key={item.id}
                hoverable
                onClick={() => onSelectResumeId(item.id)}
                className="p-4 sm:p-5 flex flex-col justify-between cursor-pointer transition-all"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-start gap-3 min-w-0 flex-1">
                      <div className="w-10 h-10 rounded-lg bg-primary-50 text-primary font-bold text-xs flex items-center justify-center flex-shrink-0 border border-primary-200">
                        {monogram}
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-sm font-semibold text-text-primary hover:text-primary transition-colors truncate">
                          {title}
                        </h3>
                        <p className="text-xs text-text-secondary font-medium truncate mt-0.5">
                          {company}
                        </p>
                      </div>
                    </div>

                    <Badge variant="success" className="text-[10px] py-0">
                      {Math.round(item.provenance_score * 100)}% Provenance
                    </Badge>
                  </div>

                  {item.matched_skills && item.matched_skills.length > 0 && (
                    <div className="flex items-center gap-1.5 flex-wrap mb-4">
                      {item.matched_skills.slice(0, 4).map((s, idx) => (
                        <span
                          key={idx}
                          className="text-[10px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium border border-slate-200"
                        >
                          {s}
                        </span>
                      ))}
                      {item.matched_skills.length > 4 && (
                        <span className="text-[10px] text-text-muted">
                          +{item.matched_skills.length - 4} kỹ năng
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <div className="pt-3 border-t border-border flex items-center justify-between gap-2 mt-auto">
                  <span className="text-[11px] text-text-muted">
                    {formatDate(item.created_at)}
                  </span>

                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="primary"
                      size="xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectResumeId(item.id);
                      }}
                      className="text-xs"
                    >
                      Mở Workspace
                    </Button>
                    <a
                      href={pdfDownloadUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="p-1.5 rounded border border-border text-slate-500 hover:text-primary hover:bg-slate-50 transition-colors"
                      title="Tải PDF"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>
                    <button
                      onClick={(e) => handleDeleteResume(item.id, e)}
                      className="p-1.5 rounded border border-border text-slate-400 hover:text-danger hover:bg-red-50 transition-colors"
                      title="Xóa CV"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
};
