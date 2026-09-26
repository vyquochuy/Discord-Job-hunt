import React, { useEffect, useState, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import * as applicationsApi from '../api/applications.api';
import { Application, ApplicationStatus } from '../types/application';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { EmptyState } from '../components/ui/empty-state';
import { formatDate } from '../utils/formatters';
import { Send, LogIn, Clock, Mail, Loader2 } from 'lucide-react';

const STATUS_OPTIONS: ApplicationStatus[] = [
  'DRAFT',
  'READY',
  'SENT',
  'INTERVIEW',
  'OFFER',
  'REJECTED',
];

export const ApplicationsPage: React.FC = () => {
  const { isAuthenticated, openAuthModal } = useAuth();
  const { showToast } = useToast();

  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchApplications = useCallback(async () => {
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const list = await applicationsApi.getApplications(1, 50);
      setApplications(list || []);
    } catch (err: unknown) {
      const e = err as Error;
      showToast(`Không thể tải đơn ứng tuyển: ${e.message}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated, showToast]);

  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  const handleStatusChange = async (appId: string, newStatus: ApplicationStatus) => {
    setUpdatingId(appId);
    try {
      await applicationsApi.updateApplicationStatus(appId, newStatus);
      setApplications((prev) =>
        prev.map((app) => (app.id === appId ? { ...app, status: newStatus } : app))
      );
      showToast(`Đã cập nhật trạng thái sang ${newStatus}!`, 'success');
    } catch (err: unknown) {
      const e = err as Error;
      showToast(`Không thể cập nhật trạng thái: ${e.message}`, 'error');
    } finally {
      setUpdatingId(null);
    }
  };

  const getStatusBadge = (status: ApplicationStatus) => {
    switch (status) {
      case 'SENT':
        return <Badge variant="success">Đã gửi (SENT)</Badge>;
      case 'INTERVIEW':
        return <Badge variant="warning">Phỏng vấn (INTERVIEW)</Badge>;
      case 'OFFER':
        return <Badge variant="purple">Offer (OFFER)</Badge>;
      case 'REJECTED':
        return <Badge variant="danger">Từ chối (REJECTED)</Badge>;
      case 'READY':
        return <Badge variant="primary">Sẵn sàng (READY)</Badge>;
      case 'DRAFT':
      default:
        return <Badge variant="slate">Bản nháp (DRAFT)</Badge>;
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Quản lý đơn nộp"
          description="Theo dõi hành trình ứng tuyển và trạng thái phản hồi từ nhà tuyển dụng."
        />
        <EmptyState
          icon={<Send className="w-6 h-6 text-primary" />}
          title="Yêu cầu Đăng nhập"
          description="Đăng nhập để theo dõi trạng thái, nhật ký gửi thư và quản lý danh sách các công việc bạn đã nộp đơn."
          action={
            <Button variant="primary" size="sm" onClick={() => openAuthModal('login', 'applications')}>
              <LogIn className="w-3.5 h-3.5" />
              <span>Đăng nhập ngay</span>
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Quản lý đơn nộp"
        description={`Tổng số ${applications.length} vị trí đã được nộp hoặc lên lịch theo dõi.`}
      />

      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center gap-3 text-text-muted">
          <Loader2 className="w-7 h-7 text-primary animate-spin" />
          <p className="text-sm font-medium">Đang tải danh sách đơn ứng tuyển...</p>
        </div>
      ) : applications.length === 0 ? (
        <EmptyState
          icon={<Send className="w-6 h-6 text-slate-400" />}
          title="Chưa có đơn ứng tuyển nào được ghi nhận"
          description="Khi bạn nộp đơn hoặc chuẩn bị hồ sơ ứng tuyển từ các tin việc làm, lịch sử sẽ xuất hiện tại đây."
        />
      ) : (
        <>
          {/* Desktop Table View (>= 768px) */}
          <div className="hidden md:block bg-surface border border-border rounded-lg shadow-card overflow-hidden">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-slate-50 border-b border-border text-text-secondary uppercase text-[11px] font-semibold">
                <tr>
                  <th className="p-4">Vị trí / Tiêu đề</th>
                  <th className="p-4">Kênh nộp</th>
                  <th className="p-4">Người nhận</th>
                  <th className="p-4">Trạng thái hiện tại</th>
                  <th className="p-4">Thời gian</th>
                  <th className="p-4 text-right">Chuyển trạng thái</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {applications.map((app) => (
                  <tr key={app.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="p-4 font-semibold text-text-primary">
                      {app.subject || 'Đơn ứng tuyển công việc'}
                    </td>
                    <td className="p-4 text-text-secondary whitespace-nowrap">
                      <span className="font-mono text-xs">{app.channel || 'EMAIL'}</span>
                    </td>
                    <td className="p-4 text-text-secondary max-w-xs truncate">
                      {app.recipient_email || '—'}
                    </td>
                    <td className="p-4 whitespace-nowrap">{getStatusBadge(app.status)}</td>
                    <td className="p-4 text-text-muted text-xs whitespace-nowrap">
                      {formatDate(app.sent_at || app.created_at)}
                    </td>
                    <td className="p-4 text-right whitespace-nowrap">
                      <select
                        value={app.status}
                        disabled={updatingId === app.id}
                        onChange={(e) => handleStatusChange(app.id, e.target.value as ApplicationStatus)}
                        className="bg-white border border-border rounded px-2.5 py-1 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer disabled:opacity-50"
                      >
                        {STATUS_OPTIONS.map((st) => (
                          <option key={st} value={st}>
                            {st}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile Card View (< 768px) */}
          <div className="md:hidden space-y-3">
            {applications.map((app) => (
              <Card key={app.id} className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-sm font-semibold text-text-primary">
                    {app.subject || 'Đơn ứng tuyển công việc'}
                  </h4>
                  {getStatusBadge(app.status)}
                </div>

                <div className="space-y-1.5 text-xs text-text-secondary">
                  {app.recipient_email && (
                    <div className="flex items-center gap-1.5 text-text-muted">
                      <Mail className="w-3.5 h-3.5 text-slate-400" />
                      <span className="truncate">{app.recipient_email}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1.5 text-text-muted">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span>Nộp lúc: {formatDate(app.sent_at || app.created_at)}</span>
                  </div>
                </div>

                <div className="pt-2.5 border-t border-border flex items-center justify-between gap-3">
                  <span className="text-xs font-medium text-text-secondary">Cập nhật:</span>
                  <select
                    value={app.status}
                    disabled={updatingId === app.id}
                    onChange={(e) => handleStatusChange(app.id, e.target.value as ApplicationStatus)}
                    className="bg-white border border-border rounded px-3 py-1.5 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer disabled:opacity-50 flex-1 max-w-[160px]"
                  >
                    {STATUS_OPTIONS.map((st) => (
                      <option key={st} value={st}>
                        {st}
                      </option>
                    ))}
                  </select>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
};
