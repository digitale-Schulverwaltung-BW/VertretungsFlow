/**
 * API Client for AbsenzFlow Backend
 */
import axios, { AxiosInstance } from 'axios';
import type {
  User,
  Absence,
  Lesson,
  LoginResponse,
  FetchLessonsRequest,
  CreateAbsenceRequest,
} from '../types';

class APIClient {
  private baseURL: string;
  private token: string | null;
  private client: AxiosInstance;

  constructor() {
    this.baseURL = 'http://localhost:8000/api';
    this.token = null;
    this.client = axios.create({
      baseURL: this.baseURL,
    });
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
   * Login
   */
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await this.client.post<LoginResponse>('/auth/login', {
      username,
      password,
    });
    return response.data;
  }

  /**
   * Get current user
   */
  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/auth/me');
    return response.data;
  }

  /**
   * Create absence
   */
  async createAbsence(data: CreateAbsenceRequest): Promise<Absence> {
    const response = await this.client.post<Absence>('/absences', data);
    return response.data;
  }

  /**
   * Get absences
   */
  async getAbsences(params?: Record<string, unknown>): Promise<Absence[]> {
    const response = await this.client.get<Absence[]>('/absences', { params });
    return response.data;
  }

  /**
   * Get single absence
   */
  async getAbsence(id: number): Promise<Absence> {
    const response = await this.client.get<Absence>(`/absences/${id}`);
    return response.data;
  }

  /**
   * Fetch lessons from WebUntis
   */
  async fetchLessons(data: FetchLessonsRequest): Promise<Lesson[]> {
    const response = await this.client.post<Lesson[]>('/absences/fetch-lessons', data);
    return response.data;
  }

  /**
   * Add lesson to absence
   */
  async addLesson(absenceId: number, lessonData: Lesson): Promise<Lesson> {
    const response = await this.client.post<Lesson>(
      `/absences/${absenceId}/lessons`,
      lessonData
    );
    return response.data;
  }

  /**
   * Update lesson in absence
   */
  async updateLesson(
    absenceId: number,
    lessonId: number,
    lessonData: Partial<Lesson>
  ): Promise<Lesson> {
    const response = await this.client.patch<Lesson>(
      `/absences/${absenceId}/lessons/${lessonId}`,
      lessonData
    );
    return response.data;
  }

  /**
   * Approve absence (department head)
   */
  async approveAbsence(
    absenceId: number,
    approved: boolean,
    comment?: string
  ): Promise<Absence> {
    const response = await this.client.post<Absence>(
      `/absences/${absenceId}/approve`,
      { approved, comment }
    );
    return response.data;
  }

  /**
   * Complete absence (planner)
   */
  async completeAbsence(absenceId: number): Promise<Absence> {
    const response = await this.client.post<Absence>(
      `/absences/${absenceId}/complete`
    );
    return response.data;
  }

  /**
   * Get users (admin only)
   */
  async getUsers(params?: Record<string, unknown>): Promise<User[]> {
    const response = await this.client.get<User[]>('/users', { params });
    return response.data;
  }

  /**
   * Update user (admin only)
   */
  async updateUser(userId: number, data: Partial<User>): Promise<User> {
    const response = await this.client.patch<User>(`/users/${userId}`, data);
    return response.data;
  }
}

// Export singleton instance
const api = new APIClient();
export default api;
