export interface EvidenceMapItem {
  id?: string;
  section: string;
  bullet_index?: number;
  claim_text: string;
  source_entity_type: string;
  source_entity_id?: string | null;
  original_fact: string;
  is_verified: boolean;
  similarity_score: number;
  notes?: string | null;
}

export interface CoverLetter {
  id: string;
  tailored_resume_id: string;
  candidate_id: string;
  job_id: string;
  recipient_name?: string | null;
  company_name: string;
  salutation: string;
  hook_statement?: string | null;
  content_markdown: string;
  key_alignments: string[];
  created_at?: string;
}

export interface TailoredResume {
  id: string;
  candidate_id: string;
  job_id: string;
  version: number;
  target_title: string;
  summary_objective?: string | null;
  latex_source: string;
  pdf_path?: string | null;
  provenance_score: number;
  is_provenance_verified: boolean;
  matched_skills: string[];
  highlighted_projects: string[];
  status: string;
  compilation_error?: string | null;
  created_at: string;
  updated_at?: string;
  evidence_items?: EvidenceMapItem[];
  cover_letter?: CoverLetter | null;
  job?: {
    id: string;
    title: string;
    company_name: string;
    location?: string | null;
    work_mode?: string | null;
    level?: string | null;
    min_salary?: number | null;
    max_salary?: number | null;
    salary_currency?: string | null;
    apply_url?: string | null;
  } | null;
}

export interface TailoredResumeSummary {
  id: string;
  job_id: string;
  target_title: string;
  provenance_score: number;
  is_provenance_verified: boolean;
  status: string;
  pdf_path?: string | null;
  matched_skills: string[];
  created_at: string;
  job?: {
    id: string;
    title: string;
    company_name: string;
    location?: string | null;
    work_mode?: string | null;
    level?: string | null;
  } | null;
}
