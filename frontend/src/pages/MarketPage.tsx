import React, { useEffect, useMemo, useState } from 'react';
import { Activity, BarChart3, Database, RefreshCw, TrendingUp } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Card, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import * as marketApi from '../api/market.api';
import { MarketAnalytics } from '../types/market';

export const MarketPage: React.FC = () => {
  const [data, setData] = useState<MarketAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = () => {
    setLoading(true);
    setError(false);
    marketApi.getMarketAnalytics().then(setData).catch(() => setError(true)).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const maxSource = useMemo(() => Math.max(...(data?.sources.map((item) => item.jobs) ?? []), 1), [data]);
  const maxSkill = useMemo(() => Math.max(...(data?.top_skills.map((item) => item.jobs) ?? []), 1), [data]);

  return (
    <div className="space-y-5 sm:space-y-6">
      <PageHeader
        title="Thị trường IT Việt Nam"
        description="Tín hiệu tổng hợp từ dữ liệu ingestion, tách biệt với hồ sơ và workflow ứng tuyển cá nhân."
        badge={<span className="rounded-md bg-primary-50 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-primary-700">Market intelligence</span>}
        actions={<Button variant="outline" size="sm" onClick={load} disabled={loading}><RefreshCw className={loading ? 'w-3.5 h-3.5 animate-spin' : 'w-3.5 h-3.5'} /> Cập nhật</Button>}
      />

      {error && (
        <Card className="border-danger-200 bg-danger-50 p-4 text-sm text-danger-700">
          Không thể tải dữ liệu thị trường. Kiểm tra kết nối backend và thử lại.
        </Card>
      )}

      {loading && !data ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((item) => <div key={item} className="h-28 animate-pulse rounded-[14px] bg-surface" />)}
        </div>
      ) : data ? (
        <>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Metric icon={<Database />} label="Tin đang hoạt động" value={data.total_active_jobs.toLocaleString('vi-VN')} detail={`${data.sources.length} nguồn dữ liệu`} tone="blue" />
            <Metric icon={<Activity />} label="Tin đã hết hạn" value={data.total_expired_jobs.toLocaleString('vi-VN')} detail="Lịch sử được bảo toàn" tone="violet" />
            <Metric icon={<TrendingUp />} label="Lương cao nhất" value={formatSalary(data.salary.max)} detail={`Trung bình max: ${formatSalary(data.salary.average_max)}`} tone="cyan" />
            <Metric icon={<BarChart3 />} label="Kỹ năng đã chuẩn hóa" value={data.top_skills.length.toLocaleString('vi-VN')} detail="Top nhu cầu hiện tại" tone="green" />
          </div>

          <div className="grid gap-4 xl:grid-cols-[1.25fr_1fr]">
            <Card>
              <CardHeader>
                <CardTitle>Phân bổ theo nguồn</CardTitle>
                <p className="mt-1 text-xs text-text-secondary">Số job active đã chuẩn hóa từ pipeline ingestion.</p>
              </CardHeader>
              <div className="space-y-4 px-5 pb-5">
                {data.sources.length === 0 ? <Empty /> : data.sources.map((item, index) => (
                  <div key={item.source}>
                    <div className="mb-1.5 flex items-center justify-between text-xs">
                      <span className="font-semibold text-text-primary">{item.source}</span>
                      <span className="text-text-secondary">{item.jobs.toLocaleString('vi-VN')}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-surface-muted"><div className={`app-chart-bar h-full rounded-full ${['bg-primary-500', 'bg-violet-500', 'bg-cyan-500', 'bg-success-600'][index % 4]}`} style={{ width: `${(item.jobs / maxSource) * 100}%` }} /></div>
                  </div>
                ))}
              </div>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Kỹ năng được săn đón</CardTitle>
                <p className="mt-1 text-xs text-text-secondary">Xếp hạng theo số lượng job có liên kết kỹ năng.</p>
              </CardHeader>
              <div className="space-y-3 px-5 pb-5">
                {data.top_skills.length === 0 ? <Empty /> : data.top_skills.slice(0, 8).map((item, index) => (
                  <div key={item.skill} className="grid grid-cols-[24px_1fr_42px] items-center gap-2 text-xs">
                    <span className="text-[10px] font-bold text-text-muted">{String(index + 1).padStart(2, '0')}</span>
                    <div><div className="mb-1 flex justify-between"><span className="font-medium">{item.skill}</span><span className="text-text-secondary">{item.jobs}</span></div><div className="app-progress-track h-1.5 rounded-full"><div className="app-chart-bar h-full rounded-full bg-primary" style={{ width: `${(item.jobs / maxSkill) * 100}%` }} /></div></div>
                    <span className="text-right text-[10px] text-text-muted">{Math.round((item.jobs / maxSkill) * 100)}%</span>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <Card className="app-hero-card border-primary-100 bg-gradient-to-br from-primary-50 to-surface">
            <div className="flex flex-col gap-2 p-5 sm:flex-row sm:items-center sm:justify-between"><div><div className="mb-1 text-[10px] font-bold uppercase tracking-[.14em] text-primary">Data provenance</div><h2 className="font-display text-base font-bold">Một lớp dữ liệu chung cho toàn hệ thống</h2><p className="mt-1 text-xs text-text-secondary">Dashboard chỉ hiển thị aggregate công khai; không đọc candidate profile và không thay đổi matching cá nhân.</p></div><div className="rounded-lg bg-surface-2 px-3 py-2 text-xs font-medium text-text-secondary shadow-sm">{data.total_active_jobs.toLocaleString('vi-VN')} active records</div></div>
          </Card>
        </>
      ) : null}
    </div>
  );
};

function Metric({ icon, label, value, detail, tone }: { icon: React.ReactNode; label: string; value: string; detail: string; tone: 'blue' | 'violet' | 'cyan' | 'green' }) {
  const styles = { blue: 'bg-primary-50 text-primary-600', violet: 'bg-violet-50 text-violet-600', cyan: 'bg-cyan-50 text-cyan-600', green: 'bg-success-50 text-success-600' };
  return <Card className="app-stat-card relative flex min-h-[106px] items-start gap-3 overflow-hidden p-4"><div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${styles[tone]}`}>{React.cloneElement(icon as React.ReactElement, { className: 'h-4 w-4' })}</div><div><div className="text-xs text-text-secondary">{label}</div><div className="mt-1 font-display text-2xl font-bold tracking-tight">{value}</div><div className="mt-1 text-[10px] text-success-600">{detail}</div></div></Card>;
}

function Empty() { return <div className="rounded-lg border border-dashed border-border p-5 text-center text-xs text-text-secondary">Chưa có dữ liệu aggregate.</div>; }
function formatSalary(value: number | null) { return value == null ? '—' : `${value.toLocaleString('vi-VN')} đ`; }
