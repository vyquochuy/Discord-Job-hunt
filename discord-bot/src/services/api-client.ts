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

class BackendApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: config.backendApiUrl,
      timeout: 5000,
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Secret': config.internalApiSecret,
      },
    });
  }

  /**
   * Gọi kiểm tra sức khỏe hệ thống Backend FastAPI, DB & Redis
   */
  public async getHealth(): Promise<{ success: boolean; data?: HealthCheckResponse; error?: string; latencyMs: number }> {
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
      const errorMsg = err.response?.data?.detail || err.message || 'Không thể kết nối tới Backend API';
      return {
        success: false,
        data: err.response?.data,
        error: errorMsg,
        latencyMs,
      };
    }
  }
}

export const apiClient = new BackendApiClient();
