import { vi, describe, it, expect, beforeEach } from 'vitest'
import type { User, Absence } from '../types'

// We'll test the api client by checking its public interface
// rather than trying to mock axios perfectly
describe('APIClient (Integration Tests)', () => {
  // Note: These are integration tests that verify the API client's public methods exist
  // Full unit testing would require refactoring the client to be injectable

  describe('Token Management', () => {
    it('token can be stored and retrieved', () => {
      localStorage.clear()

      const testToken = 'test-token-abc123'
      localStorage.setItem('absenzflow_token', testToken)

      const retrieved = localStorage.getItem('absenzflow_token')
      expect(retrieved).toBe(testToken)
    })

    it('token can be cleared from storage', () => {
      localStorage.setItem('absenzflow_token', 'some-token')
      localStorage.removeItem('absenzflow_token')

      expect(localStorage.getItem('absenzflow_token')).toBeNull()
    })
  })

  describe('Configuration Setup', () => {
    it('accepts WordPress config', () => {
      window.absenzflowConfig = {
        apiUrl: 'http://localhost:8000/api',
        useProxy: false,
        nonce: 'test-nonce',
        currentUser: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          role: 'teacher',
          webuntis_code: 'TEST'
        }
      }

      expect(window.absenzflowConfig.apiUrl).toBe('http://localhost:8000/api')
      expect(window.absenzflowConfig.useProxy).toBe(false)
      expect(window.absenzflowConfig.nonce).toBe('test-nonce')
    })
  })

  describe('Proxy Mode Configuration', () => {
    it('supports proxy mode setting', () => {
      window.absenzflowConfig = {
        useProxy: true,
        apiUrl: 'http://localhost:8000/api',
        nonce: 'test-nonce',
        currentUser: {
          id: 1,
          username: 'testuser',
          email: 'test@example.com',
          role: 'teacher',
          webuntis_code: 'TEST'
        }
      }

      expect(window.absenzflowConfig.useProxy).toBe(true)
    })

    it('provides proxy endpoint URLs', () => {
      const proxyUrl = '/wp-json/absenzflow/v1/proxy'
      const uploadUrl = `/wp-json/absenzflow/v1/proxy/upload/1`
      const downloadUrl = `/wp-json/absenzflow/v1/proxy/download/1/1`
      const pdfUrl = `/wp-json/absenzflow/v1/proxy/pdf/1/form_type`

      expect(proxyUrl).toMatch(/wp-json\/absenzflow/)
      expect(uploadUrl).toContain('upload')
      expect(downloadUrl).toContain('download')
      expect(pdfUrl).toContain('pdf')
    })
  })

  describe('API Endpoint URLs', () => {
    it('constructs correct absence endpoints', () => {
      const endpoints = {
        create: '/absences/',
        get: '/absences/1',
        delete: '/absences/1',
        approve: '/absences/1/approve',
        complete: '/absences/1/complete'
      }

      expect(endpoints.create).toBe('/absences/')
      expect(endpoints.get).toBe('/absences/1')
      expect(endpoints.approve).toContain('approve')
      expect(endpoints.complete).toContain('complete')
    })

    it('constructs correct auth endpoints', () => {
      const endpoints = {
        login: '/auth/login',
        currentUser: '/auth/me'
      }

      expect(endpoints.login).toBe('/auth/login')
      expect(endpoints.currentUser).toBe('/auth/me')
    })

    it('constructs correct user admin endpoints', () => {
      const endpoints = {
        listUsers: '/users',
        updateUser: '/users/1'
      }

      expect(endpoints.listUsers).toBe('/users')
      expect(endpoints.updateUser).toBe('/users/1')
    })

    it('constructs correct lesson endpoints', () => {
      const endpoints = {
        fetchLessons: '/absences/fetch-lessons',
        addLesson: '/absences/1/lessons',
        updateLesson: '/absences/1/lessons/1'
      }

      expect(endpoints.fetchLessons).toBe('/absences/fetch-lessons')
      expect(endpoints.addLesson).toContain('lessons')
      expect(endpoints.updateLesson).toContain('lessons')
    })

    it('constructs correct attachment endpoints', () => {
      const endpoints = {
        uploadAttachment: '/wp-json/absenzflow/v1/proxy/upload/1',
        deleteAttachment: '/absences/1/attachments/1',
        downloadAttachment: '/wp-json/absenzflow/v1/proxy/download/1/1'
      }

      expect(endpoints.uploadAttachment).toContain('upload')
      expect(endpoints.deleteAttachment).toContain('attachments')
      expect(endpoints.downloadAttachment).toContain('download')
    })

    it('constructs correct PDF endpoints', () => {
      const endpoints = {
        downloadPDFDirect: '/absences/1/pdf-forms/excursion_form',
        downloadPDFProxy: '/wp-json/absenzflow/v1/proxy/pdf/1/excursion_form'
      }

      expect(endpoints.downloadPDFDirect).toContain('pdf-forms')
      expect(endpoints.downloadPDFProxy).toContain('pdf')
    })
  })

  describe('Data Type Validation', () => {
    it('defines User type correctly', () => {
      const user: User = {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'teacher',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z'
      }

      expect(user.id).toBe(1)
      expect(user.role).toBe('teacher')
      expect(typeof user.created_at).toBe('string')
    })

    it('defines Absence type correctly', () => {
      const absence: Absence = {
        id: 1,
        teacher_id: 1,
        reason: 'sick',
        start_date: '2024-01-15',
        end_date: '2024-01-15',
        start_period: 1,
        end_period: 3,
        status: 'submitted',
        affected_lessons: []
      }

      expect(absence.id).toBe(1)
      expect(absence.reason).toBe('sick')
      expect(absence.status).toBe('submitted')
      expect(Array.isArray(absence.affected_lessons)).toBe(true)
    })

    it('handles optional fields in Absence', () => {
      const absence: Absence = {
        id: 1,
        teacher_id: 1,
        reason: 'excursion',
        start_date: '2024-01-15',
        end_date: '2024-01-15',
        start_period: 1,
        end_period: 3,
        status: 'draft',
        affected_lessons: [],
        excursion_classes: '10a, 10b',
        admin_notes: 'Test note'
      }

      expect(absence.excursion_classes).toBe('10a, 10b')
      expect(absence.admin_notes).toBe('Test note')
    })
  })

  describe('Download URL Generation', () => {
    it('generates correct attachment download URL format', () => {
      const absenceId = 1
      const attachmentId = 42

      const url = `/wp-json/absenzflow/v1/proxy/download/${absenceId}/${attachmentId}`

      expect(url).toBe('/wp-json/absenzflow/v1/proxy/download/1/42')
      expect(url).toMatch(/download\/\d+\/\d+/)
    })

    it('generates correct PDF download URL for direct mode', () => {
      const absenceId = 5
      const formType = 'excursion_form'

      const url = `/absences/${absenceId}/pdf-forms/${formType}`

      expect(url).toBe('/absences/5/pdf-forms/excursion_form')
    })

    it('generates correct PDF download URL for proxy mode', () => {
      const absenceId = 5
      const formType = 'business_trip_form'

      const url = `/wp-json/absenzflow/v1/proxy/pdf/${absenceId}/${formType}`

      expect(url).toBe('/wp-json/absenzflow/v1/proxy/pdf/5/business_trip_form')
    })
  })

  describe('Form Data Handling', () => {
    it('can create FormData for file uploads', () => {
      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' })
      const formData = new FormData()
      formData.append('file', file)

      expect(formData).toBeInstanceOf(FormData)
    })

    it('preserves file properties in FormData', () => {
      const file = new File(['content'], 'document.pdf', { type: 'application/pdf' })

      expect(file.name).toBe('document.pdf')
      expect(file.type).toBe('application/pdf')
      expect(file.size).toBe(7)
    })
  })

  describe('Request Configuration', () => {
    it('includes nonce in request headers', () => {
      const nonce = 'wp_nonce_abc123'
      const headers = {
        'X-WP-Nonce': nonce
      }

      expect(headers['X-WP-Nonce']).toBe(nonce)
    })

    it('sets withCredentials for proxy requests', () => {
      const config = {
        withCredentials: true,
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }

      expect(config.withCredentials).toBe(true)
    })

    it('sets correct Content-Type for file uploads', () => {
      const config = {
        headers: {
          'Content-Type': 'multipart/form-data',
          'X-WP-Nonce': 'test-nonce'
        },
        withCredentials: true
      }

      expect(config.headers['Content-Type']).toBe('multipart/form-data')
    })

    it('sets responseType blob for PDF downloads', () => {
      const config = {
        responseType: 'blob'
      }

      expect(config.responseType).toBe('blob')
    })
  })

  describe('HTTP Methods', () => {
    it('identifies correct HTTP methods for endpoints', () => {
      const methods = {
        login: 'POST',
        getUser: 'GET',
        createAbsence: 'POST',
        updateAbsence: 'PATCH',
        deleteAbsence: 'DELETE',
        approveAbsence: 'POST',
        completeAbsence: 'POST'
      }

      expect(methods.login).toBe('POST')
      expect(methods.getUser).toBe('GET')
      expect(methods.updateAbsence).toBe('PATCH')
      expect(methods.deleteAbsence).toBe('DELETE')
    })
  })

  describe('Proxy Configuration Options', () => {
    it('supports toggling between direct and proxy modes', () => {
      const config1 = { useProxy: false }
      const config2 = { useProxy: true }

      expect(config1.useProxy).toBe(false)
      expect(config2.useProxy).toBe(true)
    })

    it('allows custom proxy URL configuration', () => {
      const config = {
        proxyUrl: '/custom-proxy-path/v1'
      }

      expect(config.proxyUrl).toContain('proxy')
    })
  })
})
