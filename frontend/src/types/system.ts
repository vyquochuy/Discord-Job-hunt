export interface HealthResponse {
  healthy: boolean;
  status: number;
  latencyMs: number;
  data?: {
    status?: string;
    service?: string;
    environment?: string;
    database?: string;
    [key: string]: unknown;
  };
  error?: string;
}

export interface ReadinessResponse {
  ready: boolean;
  status: number;
  latencyMs: number;
  data?: unknown;
  error?: string;
}

export interface PurgeResponse {
  message: string;
  scope: string;
  records_deleted?: number;
}

export interface ResetDemoResponse {
  message: string;
  status: string;
}
