import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import * as jobsApi from '../../api/jobs.api';
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../ui/tabs';
import { Input } from '../ui/input';
import { FilePlus, FileText, Link as LinkIcon, CheckCircle2, Play } from 'lucide-react';

export interface ManualIngestModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onIngestCompleted?: () => void;
}

export const ManualIngestModal: React.FC<ManualIngestModalProps> = ({
  open,
  onOpenChange,
  onIngestCompleted,
}) => {
  const { currentUser, openAuthModal } = useAuth();
  const { showToast } = useToast();

  const [tab, setTab] = useState<'text' | 'url'>('text');
  const [rawText, setRawText] = useState('');
  const [url, setUrl] = useState('');
  const [autoMatch, setAutoMatch] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    title: string;
    company: string;
    skillsCount: number;
    jobId: string;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) {
      showToast('Vui lòng đăng nhập để nạp mô tả công việc (JD) thủ công!', 'warning');
      openAuthModal('login');
      return;
    }

    if (tab === 'text' && rawText.trim().length < 30) {
      showToast('Nội dung JD quá ngắn (cần tối thiểu 30 ký tự để trích xuất).', 'warning');
      return;
    }

    if (tab === 'url') {
      const trimmedUrl = url.trim();
      if (!trimmedUrl.startsWith('http://') && !trimmedUrl.startsWith('https://')) {
        showToast('Đường dẫn URL không hợp lệ (cần bắt đầu bằng http:// hoặc https://).', 'warning');
        return;
      }
    }

    setLoading(true);
    setResult(null);

    try {
      const payload: jobsApi.ManualIngestPayload = {
        auto_match: autoMatch,
      };
      if (tab === 'text') {
        payload.raw_text = rawText.trim();
      } else {
        payload.source_url = url.trim();
      }

      const res = await jobsApi.ingestManualJob(payload);
      const skillsCount = res.job.description ? 5 : 0;
      setResult({
        title: res.job.title,
        company: res.job.company_name,
        skillsCount,
        jobId: res.job.id,
      });

      showToast(`Đã nạp và chuẩn hóa thành công: ${res.job.title}!`, 'success');
      if (onIngestCompleted) {
        onIngestCompleted();
      }
    } catch (err: unknown) {
      const error = err as Error;
      showToast(`Nạp JD thất bại: ${error.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setRawText('');
    setUrl('');
    setResult(null);
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(val) => {
        if (!loading) {
          onOpenChange(val);
          if (!val) handleReset();
        }
      }}
    >
      <DialogContent size="lg">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary-50 text-primary flex items-center justify-center flex-shrink-0">
              <FilePlus className="w-5 h-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Nhập tin tuyển dụng thủ công</DialogTitle>
              <DialogDescription>
                Trích xuất thông tin tự động từ văn bản bài đăng hoặc đường dẫn URL tuyển dụng trực tiếp.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <DialogBody className="space-y-4">
            <Tabs value={tab} onValueChange={(v) => setTab(v as 'text' | 'url')}>
              <TabsList className="w-full grid grid-cols-2">
                <TabsTrigger value="text" className="gap-2">
                  <FileText className="w-3.5 h-3.5" />
                  <span>Dán nội dung JD thô</span>
                </TabsTrigger>
                <TabsTrigger value="url" className="gap-2">
                  <LinkIcon className="w-3.5 h-3.5" />
                  <span>Nhập liên kết (URL)</span>
                </TabsTrigger>
              </TabsList>

              {/* Tab 1: Raw Text */}
              <TabsContent value="text" className="space-y-2 mt-3">
                <label htmlFor="raw-text-input" className="block text-xs font-semibold text-text-primary">
                  Nội dung bài đăng tuyển dụng <span className="text-danger">*</span>
                </label>
                <textarea
                  id="raw-text-input"
                  rows={8}
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder={`Ví dụ:
[Tuyển dụng] Senior Backend Developer (Python / Go)
Công ty: Tech Global Solution
Địa điểm: TP. Hồ Chí Minh / Hybrid
Mức lương: $1,500 - $2,500
Yêu cầu:
- 3+ năm kinh nghiệm Python (FastAPI/Django) hoặc Golang
- Thành thạo PostgreSQL, Redis, Docker
- Tiếng Anh giao tiếp tốt`}
                  className="w-full p-3 bg-white border border-border rounded-md text-xs sm:text-sm font-mono leading-relaxed placeholder:text-text-muted/60 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  required
                />
              </TabsContent>

              {/* Tab 2: URL */}
              <TabsContent value="url" className="space-y-2 mt-3">
                <Input
                  type="url"
                  label="Đường dẫn trang tuyển dụng trực tiếp (URL)"
                  placeholder="https://topcv.vn/viec-lam/... hoặc https://company.com/careers/job-123"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required={tab === 'url'}
                  helperText="Hệ thống sẽ tự động quét mã nguồn trang, trích xuất chức danh, công ty, kỹ năng và mức lương."
                />
              </TabsContent>
            </Tabs>

            {/* Checkbox option */}
            <div className="p-3 bg-slate-50 border border-border rounded-md">
              <label className="flex items-center gap-2.5 text-xs sm:text-sm text-text-primary cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={autoMatch}
                  onChange={(e) => setAutoMatch(e.target.checked)}
                  className="w-4 h-4 rounded text-primary focus:ring-primary"
                />
                <span className="font-medium">
                  Tự động tính điểm phù hợp 7 chỉ số tất định ngay sau khi nạp
                </span>
              </label>
            </div>

            {/* Success notification */}
            {result && (
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-lg flex items-start gap-2.5 text-xs sm:text-sm text-emerald-900">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold">
                    Đã nạp công việc: {result.title} — {result.company}
                  </div>
                  <div className="text-xs text-emerald-700 mt-0.5">
                    Hệ thống đã lưu vào cơ sở dữ liệu và sẵn sàng phân tích tương thích.
                  </div>
                </div>
              </div>
            )}
          </DialogBody>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Đóng
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={loading}
              icon={<Play className="w-3.5 h-3.5" />}
            >
              <span>Phân tích & Nạp JD</span>
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
