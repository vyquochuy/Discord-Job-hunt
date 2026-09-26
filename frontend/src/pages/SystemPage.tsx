import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { client } from '../api/client';
import * as systemApi from '../api/system.api';
import { PageHeader } from '../components/layout/PageHeader';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { DangerConfirmDialog } from '../components/ui/danger-confirm-dialog';
import {
  Server,
  Activity,
  Trash2,
  RefreshCw,
  Sparkles,
  AlertTriangle,
  Flame,
  ShieldCheck,
  ShieldAlert,
  RotateCcw,
  Save,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

export const SystemPage: React.FC = () => {
  const { currentUser, isSuperuser, openAuthModal } = useAuth();
  const { showToast } = useToast();

  const [apiBaseInput, setApiBaseInput] = useState('');
  const [resolutionSource, setResolutionSource] = useState('');
  const [pinging, setPinging] = useState(false);
  const [healthResult, setHealthResult] = useState<{
    healthy: boolean;
    latencyMs: number;
    service?: string;
    status?: string;
    error?: string;
  } | null>(null);

  // Maintenance & Purge states
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Danger Dialog state
  const [dangerDialogOpen, setDangerDialogOpen] = useState(false);
  const [dangerTarget, setDangerTarget] = useState<{
    scope: string;
    title: string;
    description: string;
  } | null>(null);

  const initSystemState = useCallback(() => {
    setApiBaseInput(client.getBaseUrl());
    setResolutionSource(client.getResolutionSource());
  }, []);

  useEffect(() => {
    initSystemState();
  }, [initSystemState]);

  const handlePingHealth = async () => {
    setPinging(true);
    setHealthResult(null);
    try {
      const res = await systemApi.checkHealth();
      setHealthResult({
        healthy: res.healthy,
        latencyMs: res.latencyMs,
        service: res.data?.service as string | undefined,
        status: res.data?.status as string | undefined,
        error: res.error,
      });

      if (res.healthy) {
        showToast(`Kết nối Backend thành công (${res.latencyMs} ms)`, 'success');
      } else {
        showToast(`Không thể kết nối Backend: ${res.error}`, 'error');
      }
    } catch (err: unknown) {
      const error = err as Error;
      setHealthResult({
        healthy: false,
        latencyMs: 0,
        error: error.message,
      });
      showToast(`Lỗi Ping API: ${error.message}`, 'error');
    } finally {
      setPinging(false);
    }
  };

  const handleSaveApiEndpoint = () => {
    if (!isSuperuser) {
      showToast('Tác vụ này yêu cầu quyền Quản trị viên (Superuser)!', 'warning');
      openAuthModal('login', 'system');
      return;
    }
    const trimmed = apiBaseInput.trim();
    if (!trimmed) {
      showToast('Vui lòng nhập API URL hợp lệ!', 'warning');
      return;
    }
    client.setBaseUrl(trimmed);
    setApiBaseInput(client.getBaseUrl());
    setResolutionSource(client.getResolutionSource());
    showToast(`Đã lưu cấu hình API: ${client.getBaseUrl()}`, 'success');
    handlePingHealth();
  };

  const handleResetApiEndpoint = () => {
    if (!isSuperuser) {
      showToast('Tác vụ này yêu cầu quyền Quản trị viên (Superuser)!', 'warning');
      openAuthModal('login', 'system');
      return;
    }
    client.resetBaseUrl();
    setApiBaseInput(client.getBaseUrl());
    setResolutionSource(client.getResolutionSource());
    showToast(`Đã khôi phục API mặc định: ${client.getBaseUrl()}`, 'info');
    handlePingHealth();
  };

  const handlePreset = (url: string) => {
    setApiBaseInput(url);
    client.setBaseUrl(url);
    setResolutionSource(client.getResolutionSource());
    showToast(`Đã áp dụng cấu hình: ${url}`, 'info');
    handlePingHealth();
  };

  const triggerMaintenancePurge = async (scope: string, label: string) => {
    if (!isSuperuser) {
      showToast('Tác vụ Quản trị yêu cầu tài khoản Quản trị viên (Superuser)!', 'warning');
      openAuthModal('login', 'system');
      return;
    }

    setActionLoading(scope);
    showToast(`Đang thực thi: ${label}...`, 'info');

    try {
      const res = await systemApi.purgeDatabase(scope, true);
      showToast(`Hoàn tất: ${res.message}`, 'success');
    } catch (err: unknown) {
      const error = err as Error;
      showToast(`Thao tác thất bại: ${error.message}`, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const triggerResetDemo = async () => {
    if (!isSuperuser) {
      showToast('Tác vụ Quản trị yêu cầu tài khoản Quản trị viên (Superuser)!', 'warning');
      openAuthModal('login', 'system');
      return;
    }

    setActionLoading('reset_demo');
    showToast('Đang khôi phục toàn bộ hệ thống về trạng thái mẫu ban đầu...', 'info');

    try {
      const res = await systemApi.resetDemo();
      showToast(`Khôi phục thành công: ${res.message}`, 'success');
    } catch (err: unknown) {
      const error = err as Error;
      showToast(`Lỗi reset demo: ${error.message}`, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const openDangerConfirm = (scope: string, title: string, description: string) => {
    if (!isSuperuser) {
      showToast('Tác vụ Xóa cơ sở dữ liệu yêu cầu quyền Quản trị viên (Superuser)!', 'warning');
      openAuthModal('login', 'system');
      return;
    }
    setDangerTarget({ scope, title, description });
    setDangerDialogOpen(true);
  };

  const executeDangerPurge = async () => {
    if (!dangerTarget) return;
    setActionLoading(dangerTarget.scope);
    try {
      const res = await systemApi.purgeDatabase(dangerTarget.scope, true);
      showToast(`Đã hoàn tất dọn dẹp cơ sở dữ liệu: ${res.message}`, 'success');
    } catch (err: unknown) {
      const error = err as Error;
      showToast(`Lỗi xóa database: ${error.message}`, 'error');
    } finally {
      setActionLoading(null);
      setDangerTarget(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Hệ thống & Cơ sở dữ liệu"
        description="Quản trị backend API endpoint, dọn dẹp bộ nhớ đệm và các tệp tin tạm (PDF, LaTeX) trên máy chủ."
        badge={
          isSuperuser ? (
            <Badge variant="purple" icon={<ShieldCheck className="w-3 h-3" />}>
              Superuser Authenticated
            </Badge>
          ) : (
            <Badge variant="warning" icon={<ShieldAlert className="w-3 h-3" />}>
              Admin Access Required
            </Badge>
          )
        }
      />

      {/* Superuser Status Banner */}
      {!isSuperuser && (
        <Card className="p-4 border-l-4 border-l-amber-500 bg-amber-50/50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center flex-shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-900">Yêu cầu quyền Quản trị viên (Superuser)</div>
              <p className="text-xs text-slate-600 mt-0.5">
                {currentUser
                  ? 'Tài khoản hiện tại không có quyền Superuser. Toàn bộ tính năng cấu hình và dọn dẹp hệ thống đã bị khóa.'
                  : 'Bạn chưa đăng nhập. Vui lòng đăng nhập tài khoản Quản trị viên để thực hiện các thao tác hệ thống.'}
              </p>
            </div>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => openAuthModal('login', 'system')}
            className="flex-shrink-0"
          >
            {currentUser ? 'Đổi tài khoản Admin' : 'Đăng nhập Admin'}
          </Button>
        </Card>
      )}

      {/* SECTION 1: Infrastructure */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Server className="w-4 h-4 text-primary" />
          <h2 className="text-sm sm:text-base font-bold text-text-primary uppercase tracking-wider">
            1. Hạ tầng & Cấu hình Máy chủ (Infrastructure)
          </h2>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <CardTitle>Cấu hình Backend API Base URL</CardTitle>
              <div className="flex items-center gap-2">
                <span className="text-xs text-text-muted">Nguồn:</span>
                <Badge variant="primary">{resolutionSource}</Badge>
              </div>
            </div>
            <CardDescription>
              Hỗ trợ triển khai Cloudflare Pages / Vercel kết nối tới Cloud Backend API (Render, Koyeb) hoặc máy chủ nội bộ.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-4">
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
              <Input
                value={apiBaseInput}
                onChange={(e) => setApiBaseInput(e.target.value)}
                disabled={!isSuperuser}
                placeholder="http://localhost:8000/api/v1 hoặc https://job-hunt-api.onrender.com/api/v1"
                className="font-mono text-xs sm:text-sm flex-1"
              />
              <Button
                variant="primary"
                size="md"
                onClick={handleSaveApiEndpoint}
                disabled={!isSuperuser}
                icon={<Save className="w-3.5 h-3.5" />}
              >
                <span>Lưu URL</span>
              </Button>
              <Button
                variant="outline"
                size="md"
                onClick={handleResetApiEndpoint}
                disabled={!isSuperuser}
                icon={<RotateCcw className="w-3.5 h-3.5" />}
              >
                <span>Mặc định</span>
              </Button>
            </div>

            {/* Presets */}
            <div className="flex items-center gap-2 flex-wrap text-xs text-text-muted">
              <span>Gợi ý cấu hình nhanh:</span>
              <button
                type="button"
                disabled={!isSuperuser}
                onClick={() => handlePreset('/api/v1')}
                className="px-2 py-0.5 rounded border border-border bg-slate-50 hover:bg-slate-100 text-slate-700 font-mono disabled:opacity-50"
              >
                /api/v1 (Same-Origin)
              </button>
              <button
                type="button"
                disabled={!isSuperuser}
                onClick={() => handlePreset('http://localhost:8000/api/v1')}
                className="px-2 py-0.5 rounded border border-border bg-slate-50 hover:bg-slate-100 text-slate-700 font-mono disabled:opacity-50"
              >
                http://localhost:8000/api/v1 (Localhost)
              </button>
            </div>

            {/* Health Result Box */}
            {healthResult && (
              <div
                className={`p-4 rounded-lg border text-xs sm:text-sm ${
                  healthResult.healthy
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    : 'bg-red-50 border-red-200 text-red-900'
                }`}
              >
                <div className="flex items-center gap-2 font-semibold mb-2">
                  {healthResult.healthy ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>Kết nối Online thành công (200 OK)</span>
                    </>
                  ) : (
                    <>
                      <XCircle className="w-4 h-4 text-red-600" />
                      <span>Không thể liên lạc với máy chủ Backend</span>
                    </>
                  )}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div>
                    <span className="text-slate-500 block">Độ trễ (Latency):</span>
                    <span className="font-bold">{healthResult.latencyMs} ms</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Dịch vụ:</span>
                    <span className="font-bold">{healthResult.service || 'job-hunt-backend'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Liveness:</span>
                    <span className="font-bold">{healthResult.status || 'ok'}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Trạng thái:</span>
                    <span className="font-bold">{healthResult.healthy ? 'Sẵn sàng' : 'Lỗi kết nối'}</span>
                  </div>
                </div>

                {healthResult.error && (
                  <p className="mt-2 text-xs text-red-700 bg-white/70 p-2 rounded border border-red-200">
                    {healthResult.error}
                  </p>
                )}
              </div>
            )}
          </CardContent>

          <CardFooter className="justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePingHealth}
              loading={pinging}
              icon={<Activity className="w-3.5 h-3.5" />}
            >
              <span>Kiểm tra kết nối (Ping Health)</span>
            </Button>
          </CardFooter>
        </Card>
      </div>

      {/* SECTION 2: Maintenance */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <RefreshCw className="w-4 h-4 text-primary" />
          <h2 className="text-sm sm:text-base font-bold text-text-primary uppercase tracking-wider">
            2. Bảo trì & Làm sạch Dữ liệu (Maintenance)
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Card: Tailoring Cache */}
          <Card className="flex flex-col justify-between">
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-sm sm:text-base">Dọn dẹp Hồ sơ tạo thiết kế</CardTitle>
                <Badge variant="warning">tailoring_only</Badge>
              </div>
              <CardDescription>
                Xóa toàn bộ bản CV tạo thiết kế, Cover Letter, Evidence Map và các tệp tin PDF/TeX trên ổ đĩa.{' '}
                <strong>Giữ nguyên tin tuyển dụng và hồ sơ ứng viên.</strong>
              </CardDescription>
            </CardHeader>
            <CardFooter className="justify-end">
              <Button
                variant="outline"
                size="sm"
                disabled={!isSuperuser}
                loading={actionLoading === 'tailoring_only'}
                onClick={() => triggerMaintenancePurge('tailoring_only', 'Dọn dẹp Tailoring Cache')}
                icon={<Trash2 className="w-3.5 h-3.5 text-amber-600" />}
              >
                <span>Dọn dẹp Tailoring Cache</span>
              </Button>
            </CardFooter>
          </Card>

          {/* Card: Reset Matching Scores */}
          <Card className="flex flex-col justify-between">
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-sm sm:text-base">Đặt lại Điểm phù hợp (Matches)</CardTitle>
                <Badge variant="primary">matches_only</Badge>
              </div>
              <CardDescription>
                Xóa bảng điểm 7 chỉ số để hệ thống tính toán lại từ đầu khi chạy tiến trình quét hoặc khi người dùng mở tin tuyển dụng.
              </CardDescription>
            </CardHeader>
            <CardFooter className="justify-end">
              <Button
                variant="outline"
                size="sm"
                disabled={!isSuperuser}
                loading={actionLoading === 'matches_only'}
                onClick={() => triggerMaintenancePurge('matches_only', 'Đặt lại điểm Matching')}
                icon={<RefreshCw className="w-3.5 h-3.5 text-primary" />}
              >
                <span>Đặt lại Điểm Matching</span>
              </Button>
            </CardFooter>
          </Card>

          {/* Card: Jobs & Tailoring */}
          <Card className="flex flex-col justify-between">
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-sm sm:text-base">Xóa Dữ liệu Việc làm & Hồ sơ</CardTitle>
                <Badge variant="danger">jobs_and_tailoring</Badge>
              </div>
              <CardDescription>
                Xóa toàn bộ tin tuyển dụng, điểm tương thích, CV tạo thiết kế và thư xin việc.{' '}
                <strong>Giữ nguyên Hồ sơ ứng viên và Từ điển kỹ năng chuẩn.</strong>
              </CardDescription>
            </CardHeader>
            <CardFooter className="justify-end">
              <Button
                variant="danger"
                size="sm"
                disabled={!isSuperuser}
                loading={actionLoading === 'jobs_and_tailoring'}
                onClick={() =>
                  openDangerConfirm(
                    'jobs_and_tailoring',
                    'Xóa Tin tuyển dụng & Cache',
                    'Thao tác này sẽ xóa toàn bộ danh sách việc làm đã cào, điểm tương thích 7 chỉ số và các bản CV đã tạo.'
                  )
                }
                icon={<AlertTriangle className="w-3.5 h-3.5" />}
              >
                <span>Xóa Tin việc làm & Cache</span>
              </Button>
            </CardFooter>
          </Card>

          {/* Card: Reset Demo */}
          <Card className="flex flex-col justify-between">
            <CardHeader>
              <div className="flex items-center justify-between gap-2">
                <CardTitle className="text-sm sm:text-base">Khôi phục Dữ liệu mẫu Demo</CardTitle>
                <Badge variant="success">Re-seed All</Badge>
              </div>
              <CardDescription>
                Làm trống toàn bộ dữ liệu, nạp lại Từ điển Canonical Skills (180+ kỹ năng) và đồng bộ lại Hồ sơ từ thư mục context.example/.
              </CardDescription>
            </CardHeader>
            <CardFooter className="justify-end">
              <Button
                variant="outline"
                size="sm"
                disabled={!isSuperuser}
                loading={actionLoading === 'reset_demo'}
                onClick={triggerResetDemo}
                icon={<Sparkles className="w-3.5 h-3.5 text-emerald-600" />}
              >
                <span>Khôi phục Dữ liệu mẫu</span>
              </Button>
            </CardFooter>
          </Card>
        </div>
      </div>

      {/* SECTION 3: Danger Zone */}
      <div className="space-y-3 pt-4 border-t border-border">
        <div className="flex items-center gap-2 text-danger">
          <Flame className="w-5 h-5" />
          <h2 className="text-sm sm:text-base font-bold uppercase tracking-wider">
            3. Khu vực Nguy hiểm (Danger Zone)
          </h2>
        </div>

        <Card className="border-2 border-danger/60 bg-red-50/20">
          <CardHeader>
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-danger flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-danger flex-shrink-0" />
                <span>Xóa sạch toàn bộ Cơ sở dữ liệu (Wipe All Data)</span>
              </CardTitle>
              <Badge variant="danger">Scope: all (Critical)</Badge>
            </div>
            <CardDescription className="text-red-900/80 leading-relaxed mt-1">
              Thao tác này sẽ làm rỗng hoàn toàn tất cả các bảng dữ liệu trong PostgreSQL: Jobs, Candidates, Resumes, Applications, Skills. Thao tác có hiệu lực ngay lập tức và <strong>hoàn toàn không thể khôi phục</strong>.
            </CardDescription>
          </CardHeader>

          <CardFooter className="justify-end bg-red-50/50 border-t border-red-200">
            <Button
              variant="critical"
              size="sm"
              disabled={!isSuperuser}
              onClick={() =>
                openDangerConfirm(
                  'all',
                  'LÀM TRỐNG TOÀN BỘ CƠ SỞ DỮ LIỆU',
                  'Bạn đang chuẩn bị xóa sạch toàn bộ dữ liệu ứng viên, việc làm, hồ sơ và đơn ứng tuyển trên toàn hệ thống.'
                )
              }
              icon={<Flame className="w-4 h-4" />}
            >
              <span>Xóa sạch Database (Purge All)</span>
            </Button>
          </CardFooter>
        </Card>
      </div>

      {/* Danger Confirmation Dialog */}
      {dangerTarget && (
        <DangerConfirmDialog
          open={dangerDialogOpen}
          onOpenChange={setDangerDialogOpen}
          title={dangerTarget.title}
          description={dangerTarget.description}
          confirmationKeyword="DELETE"
          confirmLabel="Xác nhận xóa vĩnh viễn"
          onConfirm={executeDangerPurge}
          loading={actionLoading === dangerTarget.scope}
        />
      )}
    </div>
  );
};
