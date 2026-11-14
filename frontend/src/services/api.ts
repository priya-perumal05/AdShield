import type {
  BackendHealth,
  TextAnalysisRequest,
  TextAnalysisResponse,
  ImageAnalysisResponse,
  UrlAnalysisRequest,
  UrlAnalysisResponse,
} from '../types';

/**
 * Resolves the API base URL based on the environment:
 * - In local development (VITE_API_BASE_URL empty or unset): defaults to '/api'
 *   which leverages the Vite development server reverse proxy configured in vite.config.ts.
 * - In production (VITE_API_BASE_URL set, e.g. on Vercel): uses the deployed backend URL
 *   (e.g., https://adshield-backend.onrender.com) and ensures the '/api' prefix is present.
 */
export const getApiBaseUrl = (): string => {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || '').trim();
  if (!envUrl) {
    return '/api';
  }
  const cleanUrl = envUrl.replace(/\/+$/, '');
  return cleanUrl.endsWith('/api') ? cleanUrl : `${cleanUrl}/api`;
};

const API_BASE = getApiBaseUrl();

export class ApiError extends Error {
  statusCode: number;
  constructor(message: string, statusCode: number = 500) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
  }
}

export const apiService = {
  /**
   * Fetches backend health and subsystem statuses
   */
  async checkHealth(): Promise<BackendHealth> {
    try {
      const response = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      });
      if (!response.ok) {
        throw new ApiError(`Health check failed with status: ${response.status}`, response.status);
      }
      return await response.json();
    } catch (err: unknown) {
      if (err instanceof ApiError) throw err;
      throw new ApiError('Unable to connect to AdShield backend server. Please verify the backend service is running and accessible.');
    }
  },

  /**
   * Submits advertisement copy for text and NLP threat analysis
   */
  async analyzeText(data: TextAnalysisRequest): Promise<TextAnalysisResponse> {
    const response = await fetch(`${API_BASE}/analyze/text`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(data),
    });

    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const msg = body?.detail || `Text analysis failed with status: ${response.status}`;
      throw new ApiError(msg, response.status);
    }
    return body;
  },

  /**
   * Submits advertisement image for OCR and Gemini Vision analysis
   */
  async analyzeImage(file: File, sourceContext?: string): Promise<ImageAnalysisResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (sourceContext) {
      formData.append('source_context', sourceContext);
    }

    const response = await fetch(`${API_BASE}/analyze/image`, {
      method: 'POST',
      body: formData,
    });

    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const msg = body?.detail || `Image analysis failed with status: ${response.status}`;
      throw new ApiError(msg, response.status);
    }
    return body;
  },

  /**
   * Submits advertisement destination URL for structural and Safe Browsing checks
   */
  async analyzeUrl(data: UrlAnalysisRequest): Promise<UrlAnalysisResponse> {
    const response = await fetch(`${API_BASE}/analyze/url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(data),
    });

    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const msg = body?.detail || `URL analysis failed with status: ${response.status}`;
      throw new ApiError(msg, response.status);
    }
    return body;
  },
};
