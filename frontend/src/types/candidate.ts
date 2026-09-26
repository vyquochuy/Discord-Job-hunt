export interface CandidateProfile {
  id?: string;
  user_id?: string;
  full_name: string;
  headline?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  summary?: string | null;
  target_roles: string[];
  target_locations: string[];
  skills?: Array<{ name: string; category?: string; years_of_experience?: number }>;
  experiences?: Array<{ company: string; role: string; start_date?: string; end_date?: string; description?: string }>;
  projects?: Array<{ name: string; role?: string; tech_stack?: string[]; description?: string }>;
  education?: Array<{ institution: string; degree?: string; field_of_study?: string }>;
}

export interface SyncProfileResponse {
  skills_imported: number;
  experiences_imported: number;
  projects_imported: number;
  message?: string;
}
