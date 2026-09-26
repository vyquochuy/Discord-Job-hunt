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
import { Badge } from '../ui/badge';
import { Zap, Play, RotateCcw, CheckCircle2, Loader2 } from 'lucide-react';

export interface JobScannerModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onScanCompleted?: () => void;
}

export const JobScannerModal: React.FC<JobScannerModalProps> = ({
  open,
  onOpenChange,
  onScanCompleted,
}) => {
  const { currentUser, isSuperuser, openAuthModal } = useAuth();
  const { showToast } = useToast();

  const [mode, setMode] = useState<string>('20');
  const [customLimit, setCustomLimit] = useState(150);
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState<{
    total_sources: number;
    total_collected: number;
    total_standardized: number;
    total_matches_created: number;
    elapsedSeconds: number;
  } | null>(null);

  const handleStartScan = async () => {
    if (!currentUser) {
      showToast('Tính năng Quét tin tuyển dụng yêu cầu tài khoản Quản trị viên (Superuser)!', 'warning');
      openAuthModal('login');
      return;
    }
    if (!isSuperuser) {
      showToast('Bạn đang đăng nhập tài khoản Ứng viên. Tác vụ Quét tin chỉ dành riêng cho Quản trị viên!', 'warning');
      return;
    }

    let limit = 20;
    if (mode === 'custom') {
      limit = Math.max(1, Math.min(500, customLimit));
    } else {
      limit = parseInt(mode, 10) || 20;
    }

    setScanning(true);
    setResult(null);
    const startTime = Date.now();
    showToast(`Bắt đầu quét dữ liệu đa nguồn (${limit} tin/nguồn)...`, 'info');

    try {
      const summary = await jobsApi.triggerDailyBatch(limit);
      const elapsed = (Date.now() - startTime) / 1000;
      setResult({
        total_sources: summary.total_sources,
        total_collected: summary.total_collected,
        total_standardized: summary.total_standardized,
        total_matches_created: summary.total_matches_created,
        elapsedSeconds: Math.round(elapsed * 10) / 10,
      });
      showToast(
        `Quét hoàn tất: +${summary.total_collected} tin mới, chuẩn hóa ${summary.total_standardized} tin!`,
        'success'
      );
      if (onScanCompleted) {
        onScanCompleted();
      }
    } catch (err: unknown) {
      const error = err as Error;
      showToast(`Quét tin thất bại: ${error.message}`, 'error');
    } finally {
      setScanning(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(val) => !scanning && onOpenChange(val)}>
      <DialogContent size="md">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-primary-50 text-primary flex items-center justify-center flex-shrink-0">
              <Zap className="w-5 h-5 text-primary" />
            </div>
            <div>
              <DialogTitle>Quét tin tuyển dụng đa nguồn</DialogTitle>
              <DialogDescription>
                Thu thập tự động từ ITViec, TopCV, CareerLink, Remotive; xử lý trùng lặp và tính điểm phù hợp.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <DialogBody className="space-y-4">
          <div className="space-y-2.5">
            {/* Mode 1 */}
            <label
              className={`flex items-start gap-3 p-3.5 rounded-lg border cursor-pointer transition-colors ${
                mode === '20' ? 'bg-primary-50/50 border-primary-300' : 'bg-white border-border hover:bg-slate-50'
              }`}
            >
              <input
                type="radio"
                name="scan-mode"
                value="20"
                checked={mode === '20'}
                onChange={() => setMode('20')}
                className="mt-1"
                disabled={scanning}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-text-primary">
                    Quét nhanh hàng ngày (Daily Fast Scan)
                  </span>
                  <Badge variant="primary">~5 - 10s</Badge>
                </div>
                <p className="text-xs text-text-secondary mt-1 leading-relaxed">
                  Thu thập khoảng <strong>20 tin/nguồn</strong>. Tối ưu quét mỗi sáng cho tin đăng trong 24h–48h qua.
                </p>
              </div>
            </label>

            {/* Mode 2 */}
            <label
              className={`flex items-start gap-3 p-3.5 rounded-lg border cursor-pointer transition-colors ${
                mode === '80' ? 'bg-primary-50/50 border-primary-300' : 'bg-white border-border hover:bg-slate-50'
              }`}
            >
              <input
                type="radio"
                name="scan-mode"
                value="80"
                checked={mode === '80'}
                onChange={() => setMode('80')}
                className="mt-1"
                disabled={scanning}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-text-primary">
                    Quét mở rộng (Standard Scan)
                  </span>
                  <Badge variant="success">~15 - 25s</Badge>
                </div>
                <p className="text-xs text-text-secondary mt-1 leading-relaxed">
                  Thu thập khoảng <strong>80 tin/nguồn</strong> (4–5 trang) còn hạn nộp trong 1–2 tuần qua.
                </p>
              </div>
            </label>

            {/* Mode 3 */}
            <label
              className={`flex items-start gap-3 p-3.5 rounded-lg border cursor-pointer transition-colors ${
                mode === '200' ? 'bg-primary-50/50 border-primary-300' : 'bg-white border-border hover:bg-slate-50'
              }`}
            >
              <input
                type="radio"
                name="scan-mode"
                value="200"
                checked={mode === '200'}
                onChange={() => setMode('200')}
                className="mt-1"
                disabled={scanning}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-text-primary">
                    Quét toàn diện 30 ngày (Deep Scan)
                  </span>
                  <Badge variant="purple">~40 - 60s</Badge>
                </div>
                <p className="text-xs text-text-secondary mt-1 leading-relaxed">
                  Thu thập lên tới <strong>200 tin/nguồn</strong> (10–15 trang) vét tối đa toàn bộ tin IT đang mở.
                </p>
              </div>
            </label>

            {/* Mode 4: Custom */}
            <label
              className={`flex items-start gap-3 p-3.5 rounded-lg border cursor-pointer transition-colors ${
                mode === 'custom' ? 'bg-primary-50/50 border-primary-300' : 'bg-white border-border hover:bg-slate-50'
              }`}
            >
              <input
                type="radio"
                name="scan-mode"
                value="custom"
                checked={mode === 'custom'}
                onChange={() => setMode('custom')}
                className="mt-1"
                disabled={scanning}
              />
              <div className="flex-1 min-w-0">
                <span className="text-sm font-semibold text-text-primary block">
                  Tùy chỉnh số lượng tin (Custom Limit)
                </span>
                {mode === 'custom' && (
                  <div className="mt-2.5 flex items-center gap-2">
                    <input
                      type="number"
                      min={1}
                      max={500}
                      value={customLimit}
                      onChange={(e) => setCustomLimit(parseInt(e.target.value, 10) || 50)}
                      disabled={scanning}
                      className="w-24 h-8 px-2.5 bg-white border border-border rounded text-sm text-text-primary focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <span className="text-xs text-text-secondary">tin cho mỗi nguồn (1 - 500)</span>
                  </div>
                )}
              </div>
            </label>
          </div>

          {/* Scanning Progress indicator */}
          {scanning && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3">
              <Loader2 className="w-5 h-5 text-primary animate-spin flex-shrink-0" />
              <div className="min-w-0">
                <p className="text-xs sm:text-sm font-semibold text-primary">
                  Hệ thống đang thu thập và tính điểm 7 chỉ số...
                </p>
                <p className="text-[11px] text-text-secondary mt-0.5">
                  Đang cào dữ liệu qua ITViec, TopCV, CareerLink, Remotive. Vui lòng giữ tab này mở.
                </p>
              </div>
            </div>
          )}

          {/* Result Summary */}
          {result && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg space-y-2">
              <div className="flex items-center gap-2 text-emerald-800 font-semibold text-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Hoàn tất chu kỳ quét trong {result.elapsedSeconds}s</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-emerald-900 pt-1">
                <div className="bg-white/70 p-2 rounded border border-emerald-200">
                  <div className="text-text-muted text-[10px]">Cổng dữ liệu</div>
                  <div className="font-bold text-sm">{result.total_sources} nguồn</div>
                </div>
                <div className="bg-white/70 p-2 rounded border border-emerald-200">
                  <div className="text-text-muted text-[10px]">Thu thập gốc</div>
                  <div className="font-bold text-sm">+{result.total_collected}</div>
                </div>
                <div className="bg-white/70 p-2 rounded border border-emerald-200">
                  <div className="text-text-muted text-[10px]">Chuẩn hóa</div>
                  <div className="font-bold text-sm">+{result.total_standardized}</div>
                </div>
                <div className="bg-white/70 p-2 rounded border border-emerald-200">
                  <div className="text-text-muted text-[10px]">Tính điểm Match</div>
                  <div className="font-bold text-sm">+{result.total_matches_created}</div>
                </div>
              </div>
            </div>
          )}
        </DialogBody>

        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={scanning}>
            Đóng
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleStartScan}
            loading={scanning}
            icon={result ? <RotateCcw className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          >
            <span>{result ? 'Quét lại' : 'Bắt đầu quét dữ liệu'}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
