/**
 * API Client for AbsenzFlow Backend
 */
import axios from 'axios';

class APIClient {
  constructor() {
    this.baseURL = 'http://localhost:8000/api/v1';
    this.token = null;
    this.client = axios.create();
  }
  
  /**
   * Set base URL
   */
  setBaseURL(url) {
    this.baseURL = url;
    this.client = axios.create({
      baseURL: this.baseURL,
    });
  }
  
  /**
   * Set authentication token
   */
  setToken(token) {
    this.token = token;
    if (token) {
      this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete this.client.defaults.headers.common['Authorization'];
    }
  }
  
  /**
   * Login
   */
  async login(username, password) {
    const response = await this.client.post('/auth/login', {
      username,
      password,
    });
    return response.data;
  }
  
  /**
   * Get current user
   */
  async getCurrentUser() {
    const response = await this.client.get('/auth/me');
    return response.data;
  }
  
  /**
   * Create absence
   */
  async createAbsence(data) {
    const response = await this.client.post('/absences', data);
    return response.data;
  }
  
  /**
   * Get absences
   */
  async getAbsences(params = {}) {
    const response = await this.client.get('/absences', { params });
    return response.data;
  }
  
  /**
   * Get single absence
   */
  async getAbsence(id) {
    const response = await this.client.get(`/absences/${id}`);
    return response.data;
  }
  
  /**
   * Fetch lessons from WebUntis
   */
  async fetchLessons(data) {
    const response = await this.client.post('/absences/fetch-lessons', data);
    return response.data;
  }
  
  /**
   * Add lesson to absence
   */
  async addLesson(absenceId, lessonData) {
    const response = await this.client.post(`/absences/${absenceId}/lessons`, lessonData);
    return response.data;
  }
  
  /**
   * Update lesson in absence
   */
  async updateLesson(absenceId, lessonId, lessonData) {
    const response = await this.client.patch(`/absences/${absenceId}/lessons/${lessonId}`, lessonData);
    return response.data;
  }
  
  /**
   * Approve absence (department head)
   */
  async approveAbsence(absenceId, approved, comment = null) {
    const response = await this.client.post(`/absences/${absenceId}/approve`, {
      approved,
      comment,
    });
    return response.data;
  }
  
  /**
   * Complete absence (planner)
   */
  async completeAbsence(absenceId) {
    const response = await this.client.post(`/absences/${absenceId}/complete`);
    return response.data;
  }
  
  /**
   * Get users (admin only)
   */
  async getUsers(params = {}) {
    const response = await this.client.get('/users', { params });
    return response.data;
  }
  
  /**
   * Update user (admin only)
   */
  async updateUser(userId, data) {
    const response = await this.client.patch(`/users/${userId}`, data);
    return response.data;
  }
}

// Export singleton instance
const api = new APIClient();
export default api;
