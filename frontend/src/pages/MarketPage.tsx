import { useState } from 'react';
import { ChevronDown, SlidersHorizontal } from 'lucide-react';
import type { ReactNode } from 'react';
import { RefreshCw } from 'lucide-react';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Select } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { getMarketFilters, getMarketTab } from '../api/market.api';
import type { FilterOption, Granularity, MarketFilters, MarketQuery, MarketResponses, MarketTab, SkillsOptions } from '../types/market';
import { useMarketQuery } from './market/useMarketQuery';
import { Notice } from './market/MarketCharts';
import { OverviewPanel, HiringPanel, SalaryPanel, SkillsPanel, RolesPanel, GeographyPanel, EmployersPanel, InsightsPanel } from './market/MarketPanels';

const tabs: Array<[MarketTab, string]> = [
  ['overview', 'Tổng quan'], ['hiring-trends', 'Xu hướng'], ['salaries', 'Lương'],
  ['skills', 'Kỹ năng'], ['roles', 'Vai trò'], ['geography', 'Địa lý'],
  ['employers', 'Nhà tuyển dụng'], ['insights', 'Nhận định'],
];
const filterFields = [
  ['category', 'Nhóm nghề (derived)', 'categories'], ['level', 'Cấp bậc', 'levels'],
  ['location', 'Địa điểm', 'locations'], ['region', 'Vùng (derived)', 'regions'],
  ['source', 'Nguồn', 'sources'], ['work_mode', 'Hình thức làm việc', 'work_modes'], ['skill', 'Kỹ năng', 'skills'],
] as const;
export function MarketPage() {
  const [tab, setTab] = useState<MarketTab>('overview');
  const [filters, setFilters] = useState<MarketFilters>({ include_expired: false });
  const [revision, setRevision] = useState(0);
  const [granularity, setGranularity] = useState<Granularity>('auto');
  const [skills, setSkills] = useState<SkillsOptions>({ limit: 25 });
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const catalog = useMarketQuery(`catalog:${revision}`, signal => getMarketFilters(signal));
  const update = (key: keyof MarketFilters, value: string) => setFilters(current => ({ ...current, [key]: value || undefined }));
  const invalidDates = !!(filters.date_from && filters.date_to && filters.date_from > filters.date_to);
  const query: MarketQuery = { ...filters, ...(tab === 'hiring-trends' ? { granularity } : {}), ...(tab === 'skills' ? skills : {}) };
  const options = (items: FilterOption[] = [], selected?: string) => [{ value: '', label: 'Tất cả' }, ...items.map(i => ({ value: i.value, label: `${i.label} (${i.jobs})` })), ...(selected && !items.some(i => i.value === selected) ? [{ value: selected, label: selected }] : [])];
  const renderTab = () => {
    const props = { query, revision };
    switch (tab) {
      case 'overview': return <MarketView {...props} tab="overview">{data => <OverviewPanel data={data} drill={update} />}</MarketView>;
      case 'hiring-trends': return <MarketView {...props} tab="hiring-trends">{data => <HiringPanel data={data} drill={update} />}</MarketView>;
      case 'salaries': return <MarketView {...props} tab="salaries">{data => <SalaryPanel data={data} drill={update} />}</MarketView>;
      case 'skills': return <MarketView {...props} tab="skills">{data => <SkillsPanel data={data} drill={update} />}</MarketView>;
      case 'roles': return <MarketView {...props} tab="roles">{data => <RolesPanel data={data} drill={update} />}</MarketView>;
      case 'geography': return <MarketView {...props} tab="geography">{data => <GeographyPanel data={data} drill={update} />}</MarketView>;
      case 'employers': return <MarketView {...props} tab="employers">{data => <EmployersPanel data={data} drill={update} />}</MarketView>;
      case 'insights': return <MarketView {...props} tab="insights">{data => <InsightsPanel data={data} />}</MarketView>;
    }
  };
  return <div className="space-y-5 sm:space-y-6">
    <PageHeader title="Thị trường IT Việt Nam" description="8 góc nhìn từ dữ liệu tuyển dụng đã thu thập; không đại diện toàn bộ thị trường Việt Nam." actions={<Button variant="outline" size="sm" onClick={() => setRevision(r => r + 1)}><RefreshCw className="h-3.5 w-3.5" />Cập nhật</Button>} />
    <Card className="p-4">
      <details className="group/filters">
        <summary className="cursor-pointer text-sm font-medium text-primary">Bộ lọc thị trường</summary>
        <div className="mt-4 space-y-4">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Input type="date" label="Từ ngày đăng" value={filters.date_from ?? ''} max={filters.date_to || undefined} onChange={e => update('date_from', e.target.value)} />
        <Input type="date" label="Đến ngày đăng" value={filters.date_to ?? ''} min={filters.date_from || undefined} onChange={e => update('date_to', e.target.value)} />
        {filterFields.filter(([field]) => field === 'category' || field === 'location').map(([field, , catalogField]) => <Select key={field} label={field === 'category' ? 'Nhóm nghề suy luận' : 'Địa điểm'} value={filters[field] ?? ''} options={options(catalog.data?.[catalogField], filters[field])} onChange={e => update(field, e.target.value)} />)}
      </div>
      <button type="button" className="inline-flex items-center gap-2 text-sm font-medium text-primary" aria-expanded={advancedOpen} aria-controls="market-advanced-filters" onClick={() => setAdvancedOpen(open => !open)}><SlidersHorizontal className="h-4 w-4" />Bộ lọc nâng cao <ChevronDown className={`h-4 w-4 ${advancedOpen ? 'rotate-180' : ''}`} /></button>
      <div id="market-advanced-filters" hidden={!advancedOpen} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {filterFields.filter(([field]) => field !== 'category' && field !== 'location').map(([field, label, catalogField]) => <Select key={field} label={field === 'region' ? 'Vùng' : label} value={filters[field] ?? ''} options={options(catalog.data?.[catalogField], filters[field])} onChange={e => update(field, e.target.value)} />)}
          <Input label="Tên công ty chuẩn hóa (chính xác)" value={filters.company ?? ''} maxLength={200} onChange={e => update('company', e.target.value)} />
        </div>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={!!filters.include_expired} onChange={e => setFilters(f => ({ ...f, include_expired: e.target.checked }))} />Bao gồm tin hết hạn</label>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs"><Button variant="ghost" size="sm" onClick={() => { setFilters({ include_expired: false }); setSkills({ limit: 25 }); }}>Xóa bộ lọc</Button><span className="text-text-secondary">Mặc định chỉ tin đang hoạt động · bộ lọc áp dụng cho mọi tab</span></div>
      <div className="flex flex-wrap gap-2">{filterFields.filter(([field]) => !!filters[field]).map(([field, label, catalogField]) => <Button key={field} variant="outline" size="sm" onClick={() => update(field, '')} aria-label={`Xóa bộ lọc ${label}: ${filters[field]}`}>{label.replace(' (derived)', '')}: {catalog.data?.[catalogField]?.find(item => item.value === filters[field])?.label ?? filters[field]} ×</Button>)}{filters.company && <Button variant="outline" size="sm" onClick={() => update('company', '')}>Công ty: {filters.company} ×</Button>}{filters.include_expired && <Button variant="outline" size="sm" onClick={() => setFilters(f => ({ ...f, include_expired: false }))}>Bao gồm tin hết hạn ×</Button>}</div>
      {catalog.error && <p role="alert" className="text-xs text-danger-700">Danh mục bộ lọc: {catalog.error} <button className="underline" onClick={() => setRevision(r => r + 1)}>Thử lại</button></p>}
        </div>
      </details>
      {invalidDates && <p role="alert" className="mt-3 text-sm text-danger-700">Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.</p>}
    </Card>
    <Tabs value={tab} onValueChange={value => setTab(value as MarketTab)}>
      <div className="overflow-x-auto pb-1"><TabsList aria-label="Market intelligence views">{tabs.map(([value, label]) => <TabsTrigger key={value} value={value}>{label}</TabsTrigger>)}</TabsList></div>
      {tabs.map(([value]) => <TabsContent key={value} value={value} className="space-y-4">
        {tab === value && <>
          {tab === 'hiring-trends' && <div className="max-w-xs"><Select label="Độ chi tiết thời gian" value={granularity} onChange={e => setGranularity(e.target.value as Granularity)} options={['auto', 'day', 'week', 'month'].map(v => ({ value: v, label: v }))} /></div>}
          {tab === 'skills' && <div className="grid gap-3 sm:grid-cols-3"><Input label="Tìm kỹ năng trong bảng" value={skills.search ?? ''} maxLength={80} onChange={e => setSkills(s => ({ ...s, search: e.target.value }))} /><Select label="Nhóm kỹ năng" value={skills.skill_category ?? ''} options={[{ value: '', label: 'Tất cả' }, ...['LANGUAGE', 'FRAMEWORK', 'DATABASE', 'CLOUD', 'TOOL', 'CONCEPT', 'OTHER'].map(v => ({ value: v, label: v }))]} onChange={e => setSkills(s => ({ ...s, skill_category: e.target.value }))} /><Select label="Số kỹ năng tối đa" value={String(skills.limit ?? 25)} options={[10, 25, 50, 100].map(n => ({ value: String(n), label: String(n) }))} onChange={e => setSkills(s => ({ ...s, limit: Number(e.target.value) }))} /></div>}
          {!invalidDates && renderTab()}
        </>}
      </TabsContent>)}
    </Tabs>
  </div>;
}
function MarketView<K extends MarketTab>({ tab, query, revision, children }: { tab: K; query: MarketQuery; revision: number; children: (data: MarketResponses[K]) => ReactNode }) {
  const [retry, setRetry] = useState(0);
  const key = `${tab}:${revision}:${retry}:${JSON.stringify(query)}`;
  const state = useMarketQuery(key, signal => getMarketTab(tab, query, signal));
  if (state.error) return <Card className="space-y-3 p-5" role="alert"><p className="text-sm text-danger-700">{state.error}</p><Button variant="outline" size="sm" onClick={() => setRetry(r => r + 1)}>Thử lại</Button></Card>;
  if (!state.data) return <p role="status" className="p-5 text-sm text-text-secondary">Đang tải dữ liệu thị trường…</p>;
  return <>{children(state.data)}<Notice meta={state.data.meta} /></>;
}
