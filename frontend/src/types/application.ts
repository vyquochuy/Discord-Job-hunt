export type ApplicationStatus = 'DRAFT' | 'READY' | 'SENT' | 'INTERVIEW' | 'OFFER' | 'REJECTED';
export type ApplicationChannel = 'EMAIL' | 'PLATFORM' | 'DIRECT' | 'OTHER';

export interface Application {
  id: string;
  user_id?: string;
  candidate_id?: string;
  job_id: string;
  tailored_resume_id?: string | null;
  status: ApplicationStatus;
  channel: ApplicationChannel;
  recipient_email?: string | null;
  subject?: string | null;
  body?: string | null;
  notes?: string | null;
  sent_at?: string | null;
  created_at: string;
  updated_at?: string;
}
