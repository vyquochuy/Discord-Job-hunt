export interface MarketAnalytics {
  total_active_jobs: number;
  total_expired_jobs: number;
  sources: Array<{ source: string; jobs: number }>;
  top_skills: Array<{ skill: string; jobs: number }>;
  salary: { min: number | null; average_max: number | null; max: number | null };
}
