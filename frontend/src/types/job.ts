export type WorkMode = 'REMOTE' | 'HYBRID' | 'ONSITE';
export type JobLevel = 'INTERN' | 'FRESHER' | 'JUNIOR' | 'MID' | 'SENIOR' | 'UNKNOWN';
export type JobStatus = 'ACTIVE' | 'EXPIRED' | 'CLOSED';

export interface JobSkill {
  id: string;
  skill_id: string;
  canonical_name: string;
  category: string;
  is_required: boolean;
  confidence: number;
  source: string;
}

export interface Job {
  id: string;
  raw_job_id?: string;
  title: string;
  normalized_title?: string;
  company_name: string;
  normalized_company?: string;
  location?: string | null;
  work_mode: WorkMode;
  level: JobLevel;
  min_salary?: number | null;
  max_salary?: number | null;
  salary_currency?: string | null;
  is_salary_negotiable?: boolean;
  contact_email?: string | null;
  apply_url?: string | null;
  status: JobStatus;
  source?: string | null;
  source_url?: string | null;
  posted_at?: string | null;
  created_at?: string;
  updated_at?: string;
  description?: string;
  description_raw?: string;
}

export interface JobDetail extends Job {
  description: string;
  requirements_summary?: string | null;
  benefits_summary?: string | null;
  skills: JobSkill[];
}

export interface JobListResponse {
  items: Job[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobFilterParams {
  keyword?: string;
  work_mode?: string;
  level?: string;
  location?: string;
  source?: string;
  page?: number;
  page_size?: number;
}
