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

class BackendApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: config.backendApiUrl,
      timeout: 10000,
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
}

export const apiClient = new BackendApiClient();
