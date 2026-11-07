// Legacy endpoint retained for existing consumers.
export interface MarketAnalytics {
  total_active_jobs: number;
  total_expired_jobs: number;
  sources: Array<{ source: string; jobs: number }>;
  top_skills: Array<{ skill: string; jobs: number }>;
  salary: { min: number | null; average_max: number | null; max: number | null };
}
export type MarketStatus = 'ok' | 'insufficient' | 'empty' | 'unavailable';
export interface MarketFilters {
  date_from?: string; date_to?: string; category?: string; level?: string;
  location?: string; region?: string; source?: string; work_mode?: string;
  skill?: string; company?: string; include_expired?: boolean;
}
export type Granularity = 'auto' | 'day' | 'week' | 'month';
export interface SkillsOptions { search?: string; skill_category?: string; limit?: number }
export interface MarketMeta {
  generated_at: string; filters: MarketFilters; total_jobs: number; sample_size: number;
  coverage: number; status: MarketStatus; notes: string[];
}
export interface FilterOption { value: string; label: string; jobs: number }
export interface MarketFilterCatalog {
  date_range: { min: string | null; max: string | null };
  levels: FilterOption[]; categories: FilterOption[]; locations: FilterOption[];
  regions: FilterOption[]; sources: FilterOption[]; work_modes: FilterOption[];
  skills: FilterOption[]; total_jobs: number; generated_at: string;
}
export interface Distribution { value: string; label: string; jobs: number; share: number }
export interface TrendPoint { bucket: string; label: string; jobs: number }
export interface Percentiles {
  sample_size: number; min: number | null; max: number | null; mean: number | null;
  median: number | null; p25: number | null; p75: number | null;
}
export interface SalaryGroup extends Percentiles {
  key: string; label: string; jobs: number; salary_sample?: number; estimated: boolean; status: MarketStatus;
}
export interface DataQuality {
  salary_coverage: { with_salary: number; total: number; ratio: number; negotiable: number };
  missing_level: number; missing_location: number; missing_posted_at: number;
  date_range: { min: string | null; max: string | null; days: number };
  bulk_spikes: Array<{ date: string; jobs: number; ratio: number; median_jobs: number }>;
}
export interface OverviewResponse {
  meta: MarketMeta;
  totals: { jobs: number; active: number; expired: number; companies: number; locations: number; skills: number; sources: number };
  recent: { reference_date: string; last_7_days: number; previous_7_days: number; change_pct: number | null; last_30_days: number };
  distributions: Record<'categories' | 'levels' | 'regions' | 'sources' | 'work_modes', Distribution[]>;
  data_quality: DataQuality; sparkline: TrendPoint[];
}
export interface HiringTrendsResponse {
  meta: MarketMeta; series: TrendPoint[];
  stacked: Array<{ bucket: string; label: string; values: Record<string, number> }>;
  sources: Distribution[]; categories: Distribution[]; levels: Distribution[]; work_modes: Distribution[];
  summary: { total_jobs: number; bucket_count: number; avg_per_bucket: number; peak: TrendPoint | null; latest: TrendPoint | null; granularity: Granularity; previous_period: { start: string; end: string; jobs: number; change_pct: number | null } | null };
  caveats: string[];
}
export interface SalaryResponse {
  meta: MarketMeta;
  coverage: { with_salary: number; total: number; ratio: number; negotiable: number; unknown_currency: number; missing: number };
  native: Array<Percentiles & { currency: string; jobs: number; estimated: boolean; status: MarketStatus }>;
  normalized_vnd: Percentiles & { currency: string; fx_rate: number; fx_source: string; usd_jobs: number; estimated: boolean; status: MarketStatus };
  by_level: SalaryGroup[]; by_category: SalaryGroup[]; by_region: SalaryGroup[]; by_source: SalaryGroup[];
  histogram: Array<{ label: string; min: number | null; max: number | null; count: number }>;
  top_companies: SalaryGroup[]; notes: string[];
}
export interface EmergingItem { skill?: string; title?: string; recent_jobs: number; earlier_jobs: number; recent_share: number; earlier_share: number; delta: number }
export interface Emerging { available: boolean; reason: string | null; midpoint?: string; items: EmergingItem[] }
export interface SkillItem { skill: string; category: string; jobs: number; share: number; rank: number }
export interface SkillsResponse {
  meta: MarketMeta; jobs_with_skills: number; unique_skills: number; top_skills: SkillItem[];
  by_category: Array<{ category: string; label: string; jobs: number; skills: SkillItem[] }>;
  cooccurrence: Array<{ a: string; b: string; jobs: number; lift: number }>;
  by_level: Array<{ skill: string; total: number; levels: Record<string, number> }>; emerging: Emerging;
}
export interface RoleTitle { title: string; jobs: number; share: number; level_mix: Record<string, number>; median_salary_vnd: number | null; salary_sample: number; category: string }
export interface RolesResponse {
  meta: MarketMeta; top_titles: RoleTitle[];
  by_category: Array<{ category: string; label: string; jobs: number; share: number; top_titles: string[]; median_salary_vnd: number | null; salary_sample: number }>;
  role_families: Array<{ family: string; jobs: number; share: number; examples: string[] }>;
  title_level_matrix: Array<{ title: string; total: number; levels: Record<string, number> }>; emerging: Emerging;
}
export interface GeoItem { jobs: number; share: number; companies: number; median_salary_vnd: number | null; salary_sample: number }
export interface GeographyResponse {
  meta: MarketMeta; regions: Array<GeoItem & { region: string; label: string; top_categories: string[] }>;
  cities: Array<GeoItem & { location: string }>;
  by_category: Array<{ category: string; label: string; total: number; regions: Record<string, number> }>;
  remote_share: { remote: number; hybrid: number; onsite: number; remote_ratio: number; flexible_ratio: number };
  salary_by_region: SalaryGroup[];
}
export interface EmployerItem { company: string; jobs: number; share: number; locations: string[]; categories: string[]; median_salary_vnd: number | null; salary_sample: number; latest_post: string | null; first_post: string | null }
export interface EmployersResponse {
  meta: MarketMeta; top_employers: EmployerItem[];
  concentration: { total_companies: number; top10_share: number; top20_share: number; hhi: number; repeat_hirers: number };
  by_category: Array<{ category: string; label: string; total: number; employers: Array<{ company: string; jobs: number; share: number }> }>;
  new_entrants: EmployerItem[];
}
export interface InsightsResponse {
  meta: MarketMeta; disclaimer: string;
  insights: Array<{ id: string; title: string; detail: string; severity: string; category: string; confidence: string; evidence: Record<string, unknown> }>;
  methodology: string[]; data_quality: DataQuality;
}
export interface MarketResponses {
  overview: OverviewResponse; 'hiring-trends': HiringTrendsResponse; salaries: SalaryResponse;
  skills: SkillsResponse; roles: RolesResponse; geography: GeographyResponse; employers: EmployersResponse; insights: InsightsResponse;
}
export type MarketTab = keyof MarketResponses;
export type MarketQuery = MarketFilters & SkillsOptions & { granularity?: Granularity };
