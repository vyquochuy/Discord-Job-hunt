import type { ReactNode } from 'react';
import { Card, CardHeader, CardTitle } from '../../components/ui/card';
import type { MarketMeta, TrendPoint, Emerging } from '../../types/market';

export const number = (value: number | null | undefined) => value == null ? '—' : value.toLocaleString('vi-VN', { maximumFractionDigits: 1 });
export const percent = (value: number) => `${number(value * 100)}%`;
export const money = (value: number | null | undefined) => value == null ? '—' : `${number(value)} VND`;
export function Panel({ title, children }: { title: string; children: ReactNode }) {
  return <Card className="mb-4 min-w-0 break-inside-avoid"><CardHeader><CardTitle>{title}</CardTitle></CardHeader><div className="space-y-3 px-5 pb-5">{children}</div></Card>;
}
export function Empty() { return <p className="rounded-md border border-dashed border-border p-4 text-sm text-text-secondary">Chưa đủ dữ liệu cho phân tích này.</p>; }
export function Notice({ meta }: { meta: MarketMeta }) {
  const labels = { ok: 'Có dữ liệu', insufficient: 'Mẫu chưa đủ', empty: 'Không có dữ liệu', unavailable: 'Chưa khả dụng' };
  return <Card className="space-y-2 p-4 text-sm text-text-secondary" role="status"><p className="font-semibold text-text-primary">{labels[meta.status]} · N={number(meta.sample_size)} / {number(meta.total_jobs)} tin · Độ phủ {percent(meta.coverage)}</p><p className="text-xs">Cập nhật: <time dateTime={meta.generated_at}>{meta.generated_at}</time></p>{meta.notes.length > 0 && <details><summary className="cursor-pointer text-primary">Lưu ý dữ liệu ({meta.notes.length})</summary><ul className="mt-2 list-disc space-y-1 pl-4">{meta.notes.map((note, i) => <li key={i}>{note}</li>)}</ul></details>}</Card>;
}
export function Stats({ items }: { items: Array<[string, ReactNode]> }) {
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{items.map(([label, value]) => <Card key={label} className="p-4"><p className="text-xs text-text-secondary">{label}</p><p className="mt-2 break-words font-display text-2xl font-bold leading-tight tabular-nums sm:text-3xl">{value}</p></Card>)}</div>;
}
export function Bars({ title, items, onSelect, initialLimit }: { title: string; items: Array<{ label: string; value: number; key?: string; detail?: string }>; onSelect?: (key: string) => void; initialLimit?: number }) {
  const max = Math.max(1, ...items.map(i => i.value));
  const renderItems = (entries: typeof items) => <ul className="space-y-3">{entries.map((item, index) => <li key={`${item.key ?? item.label}-${index}`}><div className="mb-1 flex items-start justify-between gap-3 text-xs">{onSelect ? <button type="button" className="text-left font-semibold text-primary underline underline-offset-2 focus-visible:outline-primary" onClick={() => onSelect(item.key ?? item.label)}>{item.label}</button> : <span>{item.label}</span>}<span className="shrink-0 text-text-secondary">{number(item.value)}{item.detail ? ` · ${item.detail}` : ''}</span></div><div className="h-2 rounded-full bg-surface-muted" aria-hidden="true"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(0, item.value / max * 100)}%` }} /></div></li>)}</ul>;
  const limit = initialLimit ?? items.length;
  return <Panel title={title}>{items.length ? <>{renderItems(items.slice(0, limit))}{items.length > limit && <details className="group"><summary className="cursor-pointer text-sm font-medium text-primary"><span className="group-open:hidden">Xem tất cả ({items.length} nhóm)</span><span className="hidden group-open:inline">Thu gọn</span></summary><div className="mt-3">{renderItems(items.slice(limit))}</div></details>}</> : <Empty />}</Panel>;
}
export function Trend({ title, points }: { title: string; points: TrendPoint[] }) {
  const max = Math.max(1, ...points.map(p => p.jobs));
  const peak = points.reduce<TrendPoint | null>((best, p) => !best || p.jobs > best.jobs ? p : best, null);
  const coords = points.map((p, i) => `${64 + i / Math.max(1, points.length - 1) * 716},${160 - p.jobs / max * 136}`).join(' ');
  return <Panel title={title}>{points.length ? <><svg viewBox="0 0 800 190" className="w-full text-primary" role="img" aria-label={`${title}: ${points.length} mốc, cao nhất ${number(peak?.jobs)} tin. Bảng số liệu bên dưới.`}>{[0, max / 2, max].map((tick, i) => <g key={i}><line x1="64" y1={160 - tick / max * 136} x2="780" y2={160 - tick / max * 136} stroke="currentColor" opacity=".2" /><text x="56" y={164 - tick / max * 136} textAnchor="end" fontSize="11" fill="currentColor">{number(tick)}</text></g>)}<text x="56" y="12" textAnchor="end" fontSize="11" fill="currentColor">Tin</text><polyline points={coords} fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />{points.map((p, i) => <circle key={`${p.bucket}-${i}`} cx={64 + i / Math.max(1, points.length - 1) * 716} cy={160 - p.jobs / max * 136} r={p === peak ? 5 : 2.5} fill="currentColor"><title>{`${p.label}: ${number(p.jobs)} tin`}</title></circle>)}<text x="64" y="184" fontSize="11" fill="currentColor">{points[0].label}</text><text x="780" y="184" textAnchor="end" fontSize="11" fill="currentColor">{points[points.length - 1].label}</text></svg><p className="text-xs text-text-secondary">Đỉnh: {peak?.label} · {number(peak?.jobs)} tin (trục dọc: số tin)</p><details><summary className="cursor-pointer text-xs text-primary">Bảng số liệu theo thời gian</summary><Table rows={points} columns={[['Thời gian', p => p.bucket], ['Số tin', p => number(p.jobs)]]} /></details></> : <Empty />}</Panel>;
}
export function Histogram({ title, items }: { title: string; items: Array<{ label: string; value: number }> }) {
  const max = Math.max(1, ...items.map(i => i.value));
  return <Panel title={title}>{items.length ? <><p className="text-xs text-text-secondary">Trục dọc: số tin · Trục ngang: khoảng midpoint VND</p><div className="overflow-x-auto"><div className="flex min-w-full items-end gap-2 border-b border-border pt-5" style={{ minWidth: `${items.length * 88}px` }}>{items.map((item, i) => <div key={`${item.label}-${i}`} className="flex min-w-0 flex-1 flex-col items-center text-center text-xs"><span className="font-semibold tabular-nums">{number(item.value)}</span><div className="mt-1 w-full rounded-t-sm bg-primary" style={{ height: `${item.value / max * 120}px` }} aria-hidden="true" /><span className="min-h-12 w-full break-words pt-2 text-text-secondary">{item.label}</span></div>)}</div></div><details><summary className="cursor-pointer text-xs text-primary">Bảng phân bố</summary><Table rows={items} columns={[[ 'Khoảng midpoint VND', i => i.label ], ['Số tin', i => number(i.value)]]} /></details></> : <Empty />}</Panel>;
}
export function Donut({ title, items, onSelect }: { title: string; items: Array<{ label: string; value: number; key?: string }>; onSelect?: (key: string) => void }) {
  const total = items.reduce((sum, item) => sum + item.value, 0);
  const colors = ['rgb(var(--primary-rgb))', 'rgb(var(--violet-rgb))', 'rgb(var(--success-rgb))', 'rgb(var(--warning-rgb))', 'rgb(var(--danger-rgb))', 'rgb(var(--cyan-rgb))', 'rgb(var(--text-muted-rgb))', 'rgb(var(--violet-700-rgb))'];
  let offset = 0;
  return <Panel title={title}>{total > 0 ? <div className="flex flex-wrap items-center justify-center gap-6"><svg viewBox="0 0 160 160" className="w-40 shrink-0" role="img" aria-label={`${title}: ${number(total)} tin; xem số liệu bên cạnh`}><circle cx="80" cy="80" r="58" fill="none" stroke="rgb(var(--surface-muted-rgb) / .15)" strokeWidth="20" />{items.map((item, index) => {
    const share = item.value / total * 100;
    const start = offset;
    offset += share;
    return <circle key={item.key ?? item.label} cx="80" cy="80" r="58" pathLength="100" fill="none" stroke={colors[index % colors.length]} strokeWidth="20" strokeDasharray={`${share} ${100 - share}`} strokeDashoffset={-start} transform="rotate(-90 80 80)"><title>{`${item.label}: ${number(item.value)} · ${percent(item.value / total)}`}</title></circle>;
  })}<text x="80" y="80" textAnchor="middle" dominantBaseline="middle" fill="currentColor" fontSize="20" fontWeight="700">{number(total)}</text></svg><ul className="min-w-0 flex-[1_1_16rem] space-y-3">{items.map((item, index) => <li key={item.key ?? item.label} className="flex items-center gap-2 text-sm"><span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: colors[index % colors.length] }} aria-hidden="true" />{onSelect ? <Drill onClick={() => onSelect(item.key ?? item.label)}>{item.label}</Drill> : item.label}<span className="ml-auto whitespace-nowrap tabular-nums">{number(item.value)} · {percent(item.value / total)}</span></li>)}</ul></div> : <Empty />}</Panel>;
}
export function Table<T>({ rows, columns }: { rows: T[]; columns: Array<[string, (row: T) => ReactNode]> }) {
  if (!rows.length) return <Empty />;
  return <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead><tr>{columns.map(([label]) => <th scope="col" key={label} className="border-b border-border p-2 font-semibold text-text-secondary">{label}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{columns.map(([label, render]) => <td key={label} className="border-b border-border p-2 align-top">{render(row)}</td>)}</tr>)}</tbody></table></div>;
}
export function EmergingPanel({ data }: { data: Emerging }) {
  return <Panel title="Thay đổi tỷ trọng giữa hai nửa thời gian (không phải dự báo)">{!data.available ? <p className="text-sm text-text-secondary">{data.reason}</p> : <><p className="text-xs text-text-secondary">Mốc phân chia: {data.midpoint}. Chỉ hiển thị thay đổi có đủ mẫu theo quy tắc backend.</p><Table rows={data.items} columns={[[ 'Kỹ năng / vị trí', i => i.skill ?? i.title ], ['N trước / sau', i => `${i.earlier_jobs} / ${i.recent_jobs}`], ['Tỷ trọng trước → sau', i => `${percent(i.earlier_share)} → ${percent(i.recent_share)}`], ['Chênh lệch', i => `${number(i.delta * 100)} điểm %`]]} /></>}</Panel>;
}
export function Drill({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return <button type="button" onClick={onClick} className="text-left font-medium text-primary underline underline-offset-2 focus-visible:outline-primary">{children}</button>;
}
