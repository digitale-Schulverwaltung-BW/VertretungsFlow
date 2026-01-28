/**
 * TypeScript Types for AbsenzFlow
 */

export type UserRole = 'teacher' | 'dept_head' | 'planner' | 'admin';

export type AbsenceStatus = 'draft' | 'submitted' | 'approved' | 'completed' | 'rejected';

export type AbsenceReason =
  | 'training'    // Fortbildung
  | 'exam'        // Prüfung
  | 'excursion'   // Exkursion
  | 'sick'        // Krank
  | 'personal'    // Privat
  | 'official'    // Dienstlich
  | 'other';      // Sonstiges

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Lesson {
  id?: number;
  date: string;
  period: number;
  subject: string;
  class_name: string;
  room?: string;
  notes?: string;
  can_be_canceled?: boolean;
}

export interface Absence {
  id?: number;
  teacher_id: number;
  reason: AbsenceReason;
  start_date: string;
  end_date: string;
  start_period: number;
  end_period: number;
  status: AbsenceStatus;
  approved_by?: number;
  approved_at?: string;
  completed_at?: string;
  created_at?: string;
  updated_at?: string;
  affected_lessons?: Lesson[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface FetchLessonsRequest {
  start_date: string;
  end_date: string;
  start_period: number;
  end_period: number;
}

export interface CreateAbsenceRequest {
  reason: AbsenceReason;
  start_date: string;
  end_date: string;
  start_period: number;
  end_period: number;
  affected_lessons: Array<{
    date: string;
    period: number;
    subject: string;
    class_name: string;
    room?: string;
    notes?: string;
    can_be_canceled?: boolean;
  }>;
}

export interface WordPressConfig {
  apiUrl: string;
  user: {
    username: string;
    displayName: string;
    role: UserRole;
  };
}

declare global {
  interface Window {
    absenzflowConfig: WordPressConfig;
  }
}
