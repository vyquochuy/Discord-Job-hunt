export type Eligibility = 'ELIGIBLE' | 'BORDERLINE' | 'INELIGIBLE';
export type RecommendationCategory = 'TOP_CHOICE' | 'STRONG_FIT' | 'BORDERLINE' | 'STRETCH' | 'NOT_RECOMMENDED' | string;

export interface MatchSignal {
  name: string;
  score: number;
  weight?: number;
  confidence?: string;
  reason?: string;
  evidence?: Array<{ text: string; source: string; confidence?: number }>;
}

export interface JobMatch {
  id: string;
  job_id: string;
  candidate_id: string;
  score: number;
  eligibility: Eligibility;
  eligibility_reasons?: string[];
  recommendation: RecommendationCategory;
  is_passed_hard_filters?: boolean;
  matched_skills: string[];
  missing_required_skills?: string[];
  missing_preferred_skills?: string[];
  warnings?: string[];
  explanation_text?: string;
  signals?: Record<string, number | { score: number; name?: string }> | MatchSignal[];
  created_at?: string;
}

export interface TopRecommendation {
  job_id: string;
  title: string;
  company_name: string;
  location?: string | null;
  work_mode?: string;
  level?: string;
  min_salary?: number | null;
  max_salary?: number | null;
  salary_currency?: string | null;
  score: number;
  eligibility: Eligibility;
  recommendation: RecommendationCategory;
  matched_skills: string[];
  missing_required_skills?: string[];
  source?: string | null;
  source_url?: string | null;
  posted_at?: string | null;
}
