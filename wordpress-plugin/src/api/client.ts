/**
 * API Client for AbsenzFlow Backend
 */
import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import type {
  User,
  Absence,
  Lesson,
  LoginResponse,
  FetchLessonsRequest,
  CreateAbsenceRequest,
} from '../types';

// WordPress config interface
interface AbsenzFlowConfig {
  apiUrl: string;
  useProxy?: boolean;
  proxyUrl?: string;
  user?: {
    id: number;
    username: string;
    email: string;
    displayName: string;
    role: string;
  };
}

declare global {
  interface Window {
    absenzflowConfig?: AbsenzFlowConfig;
  }
}

class APIClient {
  private baseURL: string;
  private token: string | null;
  private client: AxiosInstance;
  private useProxy: boolean;
  private proxyURL: string;

  constructor() {
    this.baseURL = 'http://localhost:8000/api';
    this.token = null;
    this.useProxy = false;
    this.proxyURL = '/wp-json/absenzflow/v1/proxy';
    this.client = axios.create({
      baseURL: this.baseURL,
    });

    // Initialize from WordPress config if available
    this.initializeFromConfig();
  }

  /**
   * Initialize from WordPress config
   */
  private initializeFromConfig(): void {
    if (typeof window !== 'undefined' && window.absenzflowConfig) {
      const config = window.absenzflowConfig;
      if (config.apiUrl) {
        this.setBaseURL(config.apiUrl);
      }
      if (config.useProxy) {
        this.useProxy = true;
      }
      if (config.proxyUrl) {
        this.proxyURL = config.proxyUrl;
      }
    }
  }

  /**
   * Set base URL
   */
  setBaseURL(url: string): void {
    this.baseURL = url;
    this.client = axios.create({
      baseURL: this.baseURL,
    });
    if (this.token) {
      this.setToken(this.token);
    }
  }

  /**
   * Enable/disable proxy mode
   */
  setUseProxy(useProxy: boolean): void {
    this.useProxy = useProxy;
  }

  /**
   * Set authentication token
   */
  setToken(token: string | null): void {
    this.token = token;
    if (token) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      localStorage.setItem('absenzflow_token', token);
    } else {
      delete this.client.defaults.headers.common['Authorization'];
      localStorage.removeItem('absenzflow_token');
    }
  }

  /**
   * Get stored token
   */
  getToken(): string | null {
    return this.token || localStorage.getItem('absenzflow_token');
  }

  /**
   * Make request (with proxy support)
   */
  private async request<T>(config: AxiosRequestConfig): Promise<T> {
    if (this.useProxy) {
      // Use WordPress proxy
      const proxyData = {
        method: config.method || 'GET',
        endpoint: config.url,
        body: config.data,
        params: config.params,
        token: this.token,
      };

      const response = await axios.post(this.proxyURL, proxyData, {
        withCredentials: true, // WordPress session cookies for authentication
      });
      return response.data;
    } else {
      // Direct backend call
      const response = await this.client.request<T>(config);
      return response.data;
    }
  }

  /**
   * Login
   */
  async login(username: string, password: string): Promise<LoginResponse> {
    return this.request<LoginResponse>({
      method: 'POST',
      url: '/auth/login',
      data: { username, password },
    });
  }

  /**
   * Get current user
   */
  async getCurrentUser(): Promise<User> {
    return this.request<User>({
      method: 'GET',
      url: '/auth/me',
    });
  }

  /**
   * Create absence
   */
  async createAbsence(data: CreateAbsenceRequest): Promise<Absence> {
    return this.request<Absence>({
      method: 'POST',
      url: '/absences/',  // Trailing slash to avoid 307 redirect
      data,
    });
  }

  /**
   * Get absences
   */
  async getAbsences(params?: Record<string, unknown>): Promise<Absence[]> {
    return this.request<Absence[]>({
      method: 'GET',
      url: '/absences/',  // Trailing slash to avoid 307 redirect
      params,
    });
  }

  /**
   * Get single absence
   */
  async getAbsence(id: number): Promise<Absence> {
    return this.request<Absence>({
      method: 'GET',
      url: `/absences/${id}`,
    });
  }

  /**
   * Fetch lessons from WebUntis
   */
  async fetchLessons(data: FetchLessonsRequest): Promise<Lesson[]> {
    return this.request<Lesson[]>({
      method: 'POST',
      url: '/absences/fetch-lessons',
      data,
    });
  }

  /**
   * Add lesson to absence
   */
  async addLesson(absenceId: number, lessonData: Lesson): Promise<Lesson> {
    return this.request<Lesson>({
      method: 'POST',
      url: `/absences/${absenceId}/lessons`,
      data: lessonData,
    });
  }

  /**
   * Update lesson in absence
   */
  async updateLesson(
    absenceId: number,
    lessonId: number,
    lessonData: Partial<Lesson>
  ): Promise<Lesson> {
    return this.request<Lesson>({
      method: 'PATCH',
      url: `/absences/${absenceId}/lessons/${lessonId}`,
      data: lessonData,
    });
  }

  /**
   * Approve absence (department head)
   */
  async approveAbsence(
    absenceId: number,
    approved: boolean,
    comment?: string
  ): Promise<Absence> {
    return this.request<Absence>({
      method: 'POST',
      url: `/absences/${absenceId}/approve`,
      data: { approved, comment },
    });
  }

  /**
   * Complete absence (planner)
   */
  async completeAbsence(absenceId: number): Promise<Absence> {
    return this.request<Absence>({
      method: 'POST',
      url: `/absences/${absenceId}/complete`,
    });
  }

  /**
   * Get users (admin only)
   */
  async getUsers(params?: Record<string, unknown>): Promise<User[]> {
    return this.request<User[]>({
      method: 'GET',
      url: '/users',
      params,
    });
  }

  /**
   * Update user (admin only)
   */
  async updateUser(userId: number, data: Partial<User>): Promise<User> {
    return this.request<User>({
      method: 'PATCH',
      url: `/users/${userId}`,
      data,
    });
  }
}

// Export singleton instance
const api = new APIClient();
export default api;
