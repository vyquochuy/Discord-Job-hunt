import axios, { AxiosInstance } from 'axios';
import { config } from '../config';

export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: number;
  version: string;
  environment: string;
  components: {
    api: string;
    database: string;
    redis: string;
  };
  latencyMs?: number;
}

export interface CandidateSkill {
  id: string;
  category: string;
  name: string;
  proficiency?: string | null;
}

export interface CandidateProject {
  id: string;
  name: string;
  role?: string | null;
  summary?: string | null;
  period?: string | null;
  repository_url?: string | null;
  demo_url?: string | null;
  technologies: string[];
  evidence_points: Array<{ title: string; detail: string }>;
  order: number;
}

export interface CandidateExperience {
  id: string;
  company: string;
  role: string;
  period?: string | null;
  location?: string | null;
  description?: string | null;
  achievements: string[];
  order: number;
}

export interface CandidateCertification {
  id: string;
  name: string;
  issuer?: string | null;
  issue_year?: number | null;
  credential_url?: string | null;
}

export interface CandidateDetail {
  id: string;
  full_name: string;
  headline?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  github_url?: string | null;
  linkedin_url?: string | null;
  portfolio_url?: string | null;
  summary?: string | null;
  education: Array<{
    institution: string;
    degree?: string;
    field?: string;
    graduation_year?: number;
    gpa?: string;
    coursework?: string[];
  }>;
  target_roles: string[];
  target_locations: string[];
  preferences: {
    employment_types?: string[];
    remote?: boolean | string;
    minimum_salary?: number | null;
    currency?: string;
  };
  skills: CandidateSkill[];
  experiences: CandidateExperience[];
  projects: CandidateProject[];
  certifications: CandidateCertification[];
  created_at: string;
  updated_at: string;
}

export interface CandidateUpdateInput {
  full_name?: string;
  headline?: string;
  location?: string;
  summary?: string;
  target_roles?: string[];
  target_locations?: string[];
}

export interface CandidateSyncResult {
  success: boolean;
  candidate_id: string;
  full_name: string;
  skills_count: number;
  projects_count: number;
  experiences_count: number;
  certifications_count: number;
  message: string;
}

// ============================================================================
// Job Intelligence & Matching Interfaces (Phase 2 & Phase 3)
// ============================================================================

export interface JobItem {
  id: string;
  raw_job_id: string;
  title: string;
  normalized_title: string;
  company_name: string;
  normalized_company: string;
  location?: string | null;
  normalized_location?: string | null;
  work_mode: 'ONSITE' | 'HYBRID' | 'REMOTE';
  level: 'INTERN' | 'FRESHER' | 'JUNIOR' | 'MID' | 'SENIOR' | 'LEAD' | 'MANAGER' | 'UNKNOWN';
  min_salary?: number | null;
  max_salary?: number | null;
  salary_currency?: string | null;
  is_salary_negotiable: boolean;
  status: 'ACTIVE' | 'EXPIRED' | 'MERGED';
  source?: string | null;
  source_url?: string | null;
  posted_at?: string | null;
  created_at: string;
}



export interface JobSkillDetail {
  id: string;
  skill_id: string;
  canonical_name: string;
  category: string;
  is_required: boolean;
  confidence: number;
  source: string;
}

export interface JobDetail extends JobItem {
  description: string;
  requirements_summary?: string | null;
  benefits_summary?: string | null;
  dedup_signature?: string | null;
  raw_job?: {
    source: string;
    source_url: string;
    source_job_id?: string | null;
  } | null;
  skills: JobSkillDetail[];
}

export interface JobListResponse {
  items: JobItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface EvidenceItem {
  source_type: string;
  source_id?: string | null;
  title: string;
  excerpt: string;
}

export interface MatchSignal {
  name: string;
  score: number;
  weight: number;
  confidence: 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT_EVIDENCE';
  evidence_status?: 'NOT_REQUIRED' | 'SUPPORTED' | 'INSUFFICIENT_EVIDENCE' | 'MISMATCH';
  reason: string;
  evidence?: EvidenceItem[];
}


export interface HardFilterResult {
  filter: string;
  status: 'PASS' | 'FAIL' | 'UNKNOWN';
  reason: string;
}

export interface JobMatchDetail {
  id: string;
  job_id: string;
  candidate_id: string;
  score: number;
  eligibility: 'ELIGIBLE' | 'BLOCKED' | 'UNCERTAIN';
  eligibility_reasons: string[];
  recommendation: 'STRONG_MATCH' | 'GOOD_MATCH' | 'WEAK_MATCH' | 'POOR_MATCH' | 'DO_NOT_APPLY' | 'REVIEW_REQUIRED';
  is_passed_hard_filters: boolean;
  hard_filter_results: HardFilterResult[];
  matched_skills: string[];
  missing_required_skills: string[];
  missing_preferred_skills: string[];
  signals: MatchSignal[];
  warnings?: string[];
  explanation?: string | null;
  scoring_version: string;
  taxonomy_version: string;

  candidate_snapshot?: Record<string, any>;
  job_snapshot?: Record<string, any>;
  created_at: string;
  updated_at: string;
}


export interface TopRecommendationItem {
  job_id: string;
  title: string;
  company_name: string;
  location?: string | null;
  work_mode: string;
  level: string;
  min_salary?: number | null;
  max_salary?: number | null;
  salary_currency?: string | null;
  score: number;
  eligibility: string;
  recommendation: string;
  matched_skills: string[];
  missing_required_skills: string[];
  source?: string | null;
  source_url?: string | null;
  posted_at?: string | null;
}


export interface JobCollectResult {
  status: string;
  source: string;
  report: {
    total_fetched: number;
    created: number;
    unchanged: number;
    duplicates_detected: number;
    errors: number;
  };
}

class BackendApiClient {


  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: config.backendApiUrl,
      timeout: 15000,
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Secret': config.internalApiSecret,
      },
    });
  }

  /**
   * Gọi kiểm tra sức khỏe hệ thống Backend FastAPI, DB & Redis
   */
  public async getHealth(): Promise<{
    success: boolean;
    data?: HealthCheckResponse;
    error?: string;
    latencyMs: number;
  }> {
    const startTime = Date.now();
    try {
      const response = await this.client.get<HealthCheckResponse>('/health');
      const latencyMs = Date.now() - startTime;
      return {
        success: response.status === 200,
        data: response.data,
        latencyMs,
      };
    } catch (err: any) {
      const latencyMs = Date.now() - startTime;
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        'Không thể kết nối tới Backend API';
      return {
        success: false,
        data: err.response?.data,
        error: errorMsg,
        latencyMs,
      };
    }
  }

  /**
   * Lấy chi tiết hồ sơ ứng viên
   */
  public async getProfile(): Promise<{
    success: boolean;
    data?: CandidateDetail;
    error?: string;
  }> {
    try {
      const response = await this.client.get<CandidateDetail>('/api/v1/profile');
      return {
        success: response.status === 200,
        data: response.data,
      };
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        'Lỗi khi lấy thông tin hồ sơ ứng viên';
      return {
        success: false,
        error: errorMsg,
      };
    }
  }

  /**
   * Cập nhật thông tin hồ sơ ứng viên
   */
  public async updateProfile(
    input: CandidateUpdateInput
  ): Promise<{
    success: boolean;
    data?: CandidateDetail;
    error?: string;
  }> {
    try {
      const response = await this.client.put<CandidateDetail>(
        '/api/v1/profile',
        input
      );
      return {
        success: response.status === 200,
        data: response.data,
      };
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        'Lỗi khi cập nhật thông tin hồ sơ';
      return {
        success: false,
        error: errorMsg,
      };
    }
  }

  /**
   * Kích hoạt đồng bộ hóa hồ sơ từ context/
   */
  public async syncProfile(): Promise<{
    success: boolean;
    data?: CandidateSyncResult;
    error?: string;
  }> {
    try {
      const response = await this.client.post<CandidateSyncResult>(
        '/api/v1/profile/sync'
      );
      return {
        success: response.status === 200,
        data: response.data,
      };
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        'Lỗi khi đồng bộ hóa hồ sơ ứng viên';
      return {
        success: false,
        error: errorMsg,
      };
    }
  }

  // ==========================================================================
  // Jobs API Client
  // ==========================================================================

  /**
   * Lấy danh sách tin tuyển dụng có hỗ trợ tìm kiếm và lọc
   */
  public async getJobs(params?: {
    keyword?: string;
    work_mode?: string;
    level?: string;
    location?: string;
    page?: number;
    page_size?: number;
  }): Promise<{
    success: boolean;
    data?: JobListResponse;
    error?: string;
  }> {
    try {
      const response = await this.client.get<JobListResponse>('/api/v1/jobs', {
        params,
      });
      return {
        success: response.status === 200,
        data: response.data,
      };
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        'Lỗi khi lấy danh sách tin tuyển dụng';
      return {
        success: false,
        error: errorMsg,
      };
    }
  }

  /**
   * Lấy chi tiết một tin tuyển dụng
   */
  public async getJobDetail(jobId: string): Promise<{
    success: boolean;
    data?: JobDetail;
    error?: string;
  }> {
    try {
      const response = await this.client.get<JobDetail>(`/api/v1/jobs/${jobId}`);
      return {
        success: response.status === 200,
        data: response.data,
      };
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        `Lỗi khi lấy chi tiết tin tuyển dụng ${jobId}`;
      return {
        success: false,
        error: errorMsg,
      };
    }
  }


  /**
   * Kích hoạt thu thập tin tuyển dụng từ các nguồn
   */

  public async collectJobs(
    source: string = 'mock',
    limit: number = 5
  ): Promise<{
    success: boolean;
    data?: JobCollectResult;
    error?: string;
  }> {
    try {
      const response = await this.client.post<JobCollectResult>(
        '/api/v1/jobs/collect',
        null,
        {
          params: { source, limit },
        }
      );
      return {
        success: response.status === 200,
        data: response.data,
      };
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        `Lỗi khi thu thập tin tuyển dụng từ nguồn ${source}`;
      return {
        success: false,
        error: errorMsg,
      };
    }
  }

  // ==========================================================================
  // Match & Intelligence API Client
  // ==========================================================================


  /**
   * Lấy kết quả phân tích match của 1 tin tuyển dụng
   */
  public async getJobMatch(jobId: string): Promise<{
    success: boolean;
    data?: JobMatchDetail;
    error?: string;
  }> {
    try {
      const response = await this.client.get<JobMatchDetail>(
        `/api/v1/matches/${jobId}`
      );
      return {
        success: response.status === 200,
        data: response.data,
      };
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        `Lỗi khi lấy phân tích match cho job ${jobId}`;
      return {
        success: false,
        error: errorMsg,
      };
    }
  }

  /**
   * Kích hoạt tính toán lại phân tích match cho 1 tin tuyển dụng
   */
  public async calculateMatch(
    jobId: string,
    forceRefresh: boolean = true
  ): Promise<{
    success: boolean;
    data?: JobMatchDetail;
    error?: string;
  }> {
    try {
      const response = await this.client.post<JobMatchDetail>(
        `/api/v1/matches/calculate/${jobId}?force_refresh=${forceRefresh}`
      );
      return {
        success: response.status === 200,
        data: response.data,
      };
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        `Lỗi khi tính toán match cho job ${jobId}`;
      return {
        success: false,
        error: errorMsg,
      };
    }
  }

  /**
   * Lấy danh sách công việc đề xuất hàng đầu (Top Recommendations)
   */
  public async getTopRecommendations(
    limit: number = 5,
    minScore: number = 60.0
  ): Promise<{
    success: boolean;
    data?: TopRecommendationItem[];
    error?: string;
  }> {
    try {
      const response = await this.client.get<TopRecommendationItem[]>(
        '/api/v1/matches/recommendations/top',
        {
          params: { limit, min_score: minScore },
        }
      );
      return {
        success: response.status === 200,
        data: response.data,
      };
    } catch (err: any) {
      const errorMsg =
        err.response?.data?.detail ||
        err.message ||
        'Lỗi khi lấy danh sách việc làm đề xuất';
      return {
        success: false,
        error: errorMsg,
      };
    }
  }
}

export const apiClient = new BackendApiClient();
