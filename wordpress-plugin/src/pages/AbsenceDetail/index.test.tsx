import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AbsenceDetail from './index'
import type { Absence, User } from '../../types'

// Mock API client
vi.mock('../../api/client', () => ({
  default: {
    getAbsence: vi.fn(),
    getCurrentUser: vi.fn(),
    getAbsences: vi.fn(),
    approveAbsence: vi.fn(),
    completeAbsence: vi.fn(),
    deleteAbsence: vi.fn(),
    getAttachmentDownloadUrl: vi.fn((absenceId, attachmentId) =>
      `/wp-json/absenzflow/v1/proxy/download/${absenceId}/${attachmentId}`
    ),
  },
}))

import api from '../../api/client'

// Test fixtures
const mockTeacher: User = {
  id: 1,
  username: 'jdoe',
  email: 'jdoe@school.com',
  full_name: 'John Doe',
  role: 'teacher',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
}

// Test fixtures for Phase 2-7 (will be used in future tests)
/* eslint-disable @typescript-eslint/no-unused-vars */
const mockAdmin: User = {
  id: 2,
  username: 'admin',
  email: 'admin@school.com',
  full_name: 'Admin User',
  role: 'admin',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
}

const mockPlanner: User = {
  id: 3,
  username: 'planner',
  email: 'planner@school.com',
  full_name: 'Planner User',
  role: 'planner',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
}

const mockDeptHead: User = {
  id: 4,
  username: 'depthead',
  email: 'depthead@school.com',
  full_name: 'Dept Head User',
  role: 'dept_head',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
}

const mockAbsence: Absence = {
  id: 1,
  teacher_id: 1,
  teacher: mockTeacher,
  reason: 'sick',
  start_date: '2024-02-15',
  end_date: '2024-02-15',
  start_period: 1,
  end_period: 3,
  status: 'submitted',
  created_at: '2024-02-10T10:00:00Z',
  affected_lessons: [
    {
      id: 1,
      absence_id: 1,
      date: '2024-02-15',
      period: 1,
      end_period: 2,
      subject: 'Mathematik',
      class_name: '10a',
      can_be_canceled: false,
      notes: 'Test notes',
    },
  ],
  attachments: [
    {
      id: 1,
      absence_id: 1,
      filename: 'test.pdf',
      file_size: 1024,
      uploaded_at: '2024-02-10T10:30:00Z',
    },
  ],
}

const mockAbsenceWithExcursion: Absence = {
  ...mockAbsence,
  id: 2,
  reason: 'excursion',
  excursion_classes: '10a, 10b',
}

const mockAbsenceWithPersonalReason: Absence = {
  ...mockAbsence,
  id: 3,
  reason: 'personal',
  personal_reason: 'Arzttermin',
}

const mockAbsenceWithAdminNotes: Absence = {
  ...mockAbsence,
  id: 4,
  admin_notes: 'Please approve ASAP',
}

const mockApprovedAbsence: Absence = {
  ...mockAbsence,
  id: 5,
  status: 'approved',
  approved_at: '2024-02-11T14:00:00Z',
}

const mockCompletedAbsence: Absence = {
  ...mockAbsence,
  id: 6,
  status: 'completed',
  approved_at: '2024-02-11T14:00:00Z',
  completed_at: '2024-02-12T16:00:00Z',
}
/* eslint-enable @typescript-eslint/no-unused-vars */

// Helper function to render component with router
const renderWithRouter = (absenceId: string = '1') => {
  return render(
    <MemoryRouter initialEntries={[`/absence/${absenceId}`]}>
      <Routes>
        <Route path="/absence/:id" element={<AbsenceDetail />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('AbsenceDetail - Phase 1: Basic Rendering & States', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Setup default window config
    window.absenzflowConfig = {
      apiUrl: 'http://localhost:8000/api',
      useProxy: true,
      nonce: 'test-nonce',
      deptHeadsCanComplete: false,
      currentUser: mockTeacher,
    }
  })

  describe('Loading State', () => {
    it('displays loading spinner and message', () => {
      // Mock API to return pending promise (never resolves)
      vi.mocked(api.getAbsence).mockImplementation(() => new Promise(() => {}))
      vi.mocked(api.getCurrentUser).mockImplementation(() => new Promise(() => {}))
      vi.mocked(api.getAbsences).mockImplementation(() => new Promise(() => {}))

      renderWithRouter('1')

      expect(screen.getByText('Lädt Abwesenheit...')).toBeInTheDocument()
      const spinner = document.querySelector('.animate-spin')
      expect(spinner).toBeInTheDocument()
    })
  })

  describe('Error States', () => {
    it('displays error message when API call fails', async () => {
      vi.mocked(api.getAbsence).mockRejectedValue(new Error('Network error'))
      vi.mocked(api.getCurrentUser).mockResolvedValue(mockTeacher)
      vi.mocked(api.getAbsences).mockResolvedValue([])

      renderWithRouter('1')

      await waitFor(() => {
        expect(screen.getByText(/Network error/i)).toBeInTheDocument()
      })

      // Check for "Zurück zum Dashboard" button
      expect(screen.getByRole('button', { name: /Zurück zum Dashboard/i })).toBeInTheDocument()
    })

    it('displays error when absence ID is missing', async () => {
      render(
        <MemoryRouter initialEntries={['/absence/']}>
          <Routes>
            <Route path="/absence/:id?" element={<AbsenceDetail />} />
          </Routes>
        </MemoryRouter>
      )

      await waitFor(() => {
        expect(screen.getByText(/Keine Abwesenheits-ID angegeben/i)).toBeInTheDocument()
      })
    })

    it('displays "Abwesenheit nicht gefunden" when absence is null', async () => {
      vi.mocked(api.getAbsence).mockResolvedValue(null as any)
      vi.mocked(api.getCurrentUser).mockResolvedValue(mockTeacher)
      vi.mocked(api.getAbsences).mockResolvedValue([])

      renderWithRouter('999')

      await waitFor(() => {
        expect(screen.getByText(/Abwesenheit nicht gefunden/i)).toBeInTheDocument()
      })
    })

    it('renders "Zurück zum Dashboard" button in error state', async () => {
      vi.mocked(api.getAbsence).mockRejectedValue(new Error('Error'))
      vi.mocked(api.getCurrentUser).mockResolvedValue(mockTeacher)
      vi.mocked(api.getAbsences).mockResolvedValue([])

      renderWithRouter('1')

      await waitFor(() => {
        const backButton = screen.getByRole('button', { name: /Zurück zum Dashboard/i })
        expect(backButton).toBeInTheDocument()
      })
    })
  })

  describe('Successful Data Load', () => {
    it('renders main content when data loads successfully', async () => {
      vi.mocked(api.getAbsence).mockResolvedValue(mockAbsence)
      vi.mocked(api.getCurrentUser).mockResolvedValue(mockTeacher)
      vi.mocked(api.getAbsences).mockResolvedValue([mockAbsence])

      renderWithRouter('1')

      await waitFor(() => {
        expect(screen.getByText('Abwesenheit Details')).toBeInTheDocument()
      })

      // Should not show loading or error
      expect(screen.queryByText('Lädt Abwesenheit...')).not.toBeInTheDocument()
      expect(screen.queryByText(/Fehler/i)).not.toBeInTheDocument()
    })

    it('displays page title "Abwesenheit Details"', async () => {
      vi.mocked(api.getAbsence).mockResolvedValue(mockAbsence)
      vi.mocked(api.getCurrentUser).mockResolvedValue(mockTeacher)
      vi.mocked(api.getAbsences).mockResolvedValue([mockAbsence])

      renderWithRouter('1')

      await waitFor(() => {
        expect(screen.getByText('Abwesenheit Details')).toBeInTheDocument()
      })
    })

    it('displays "Zurück zum Dashboard" button in header', async () => {
      vi.mocked(api.getAbsence).mockResolvedValue(mockAbsence)
      vi.mocked(api.getCurrentUser).mockResolvedValue(mockTeacher)
      vi.mocked(api.getAbsences).mockResolvedValue([mockAbsence])

      renderWithRouter('1')

      await waitFor(() => {
        const backButtons = screen.getAllByText(/Zurück zum Dashboard/i)
        expect(backButtons.length).toBeGreaterThan(0)
      })
    })

    it('calls API methods with correct parameters', async () => {
      vi.mocked(api.getAbsence).mockResolvedValue(mockAbsence)
      vi.mocked(api.getCurrentUser).mockResolvedValue(mockTeacher)
      vi.mocked(api.getAbsences).mockResolvedValue([mockAbsence])

      renderWithRouter('1')

      await waitFor(() => {
        expect(api.getAbsence).toHaveBeenCalledWith(1)
        expect(api.getCurrentUser).toHaveBeenCalled()
        expect(api.getAbsences).toHaveBeenCalled()
      })
    })
  })

  describe('Loading State Transitions', () => {
    it('transitions from loading to success state', async () => {
      vi.mocked(api.getAbsence).mockResolvedValue(mockAbsence)
      vi.mocked(api.getCurrentUser).mockResolvedValue(mockTeacher)
      vi.mocked(api.getAbsences).mockResolvedValue([mockAbsence])

      renderWithRouter('1')

      // Initially shows loading
      expect(screen.getByText('Lädt Abwesenheit...')).toBeInTheDocument()

      // Then shows content
      await waitFor(() => {
        expect(screen.queryByText('Lädt Abwesenheit...')).not.toBeInTheDocument()
        expect(screen.getByText('Abwesenheit Details')).toBeInTheDocument()
      })
    })

    it('transitions from loading to error state', async () => {
      vi.mocked(api.getAbsence).mockRejectedValue(new Error('API Error'))
      vi.mocked(api.getCurrentUser).mockResolvedValue(mockTeacher)
      vi.mocked(api.getAbsences).mockResolvedValue([])

      renderWithRouter('1')

      // Initially shows loading
      expect(screen.getByText('Lädt Abwesenheit...')).toBeInTheDocument()

      // Then shows error
      await waitFor(() => {
        expect(screen.queryByText('Lädt Abwesenheit...')).not.toBeInTheDocument()
        expect(screen.getByText(/API Error/i)).toBeInTheDocument()
      })
    })
  })
})

describe('AbsenceDetail - Unerledigt-Navigation & Rückmeldung', () => {
  const list = (statuses: Array<[number, Absence['status']]>): Absence[] =>
    statuses.map(([id, status]) => ({ ...mockAbsence, id, status }))

  beforeEach(() => {
    vi.clearAllMocks()
    window.absenzflowConfig = {
      apiUrl: 'http://localhost:8000/api',
      useProxy: true,
      nonce: 'test-nonce',
      deptHeadsCanComplete: false,
      currentUser: mockPlanner,
    }
  })

  const setup = (current: number, all: Array<[number, Absence['status']]>, user: User = mockPlanner) => {
    const absences = list(all)
    vi.mocked(api.getAbsence).mockResolvedValue(absences.find(a => a.id === current)!)
    vi.mocked(api.getCurrentUser).mockResolvedValue(user)
    vi.mocked(api.getAbsences).mockResolvedValue(absences)
    return renderWithRouter(String(current))
  }

  it('hides unresolved-navigation for teachers', async () => {
    setup(1, [[1, 'submitted'], [2, 'submitted']], mockTeacher)
    await waitFor(() => expect(screen.getByText('Abwesenheit Details')).toBeInTheDocument())
    expect(screen.queryByText(/Unerledigt/)).not.toBeInTheDocument()
  })

  it('jumps to next unresolved absence, skipping completed/rejected', async () => {
    setup(1, [[1, 'submitted'], [2, 'completed'], [3, 'rejected'], [4, 'approved']])
    await waitFor(() => expect(screen.getByText('1 / 4')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /Unerledigt ⇥/ }))

    await waitFor(() => expect(api.getAbsence).toHaveBeenCalledWith(4))
  })

  it('jumps to previous unresolved absence', async () => {
    setup(4, [[1, 'approved'], [2, 'completed'], [3, 'completed'], [4, 'submitted']])
    await waitFor(() => expect(screen.getByText('4 / 4')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /⇤ Unerledigt/ }))

    await waitFor(() => expect(api.getAbsence).toHaveBeenCalledWith(1))
  })

  it('disables jump buttons when no unresolved absence in that direction', async () => {
    setup(2, [[1, 'completed'], [2, 'submitted'], [3, 'completed']])
    await waitFor(() => expect(screen.getByText('2 / 3')).toBeInTheDocument())

    expect(screen.getByRole('button', { name: /Unerledigt ⇥/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /⇤ Unerledigt/ })).toBeDisabled()
  })

  it('sends feedback with "Als erledigt markieren"', async () => {
    vi.mocked(api.completeAbsence).mockResolvedValue(mockCompletedAbsence)
    setup(1, [[1, 'approved']])
    const textarea = await screen.findByLabelText(/Rückmeldung an die Lehrkraft/)

    fireEvent.change(textarea, { target: { value: '  Vertretung: Hr. X ' } })
    fireEvent.click(screen.getByRole('button', { name: /Als erledigt markieren/ }))

    await waitFor(() => expect(api.completeAbsence).toHaveBeenCalledWith(1, 'Vertretung: Hr. X'))
  })

  it('sends feedback on rejection but not on approval', async () => {
    vi.mocked(api.approveAbsence).mockResolvedValue(mockAbsence)
    setup(1, [[1, 'submitted']])
    const textarea = await screen.findByLabelText(/Rückmeldung an die Lehrkraft/)

    fireEvent.change(textarea, { target: { value: 'Zu kurzfristig' } })
    fireEvent.click(screen.getByRole('button', { name: /Genehmigen/ }))
    await waitFor(() => expect(api.approveAbsence).toHaveBeenCalledWith(1, true, undefined))

    fireEvent.change(textarea, { target: { value: 'Zu kurzfristig' } })
    fireEvent.click(screen.getByRole('button', { name: /Ablehnen/ }))
    await waitFor(() => expect(api.approveAbsence).toHaveBeenCalledWith(1, false, 'Zu kurzfristig'))
  })

  it('sends undefined when feedback is empty', async () => {
    vi.mocked(api.completeAbsence).mockResolvedValue(mockCompletedAbsence)
    setup(1, [[1, 'approved']])

    fireEvent.click(await screen.findByRole('button', { name: /Als erledigt markieren/ }))

    await waitFor(() => expect(api.completeAbsence).toHaveBeenCalledWith(1, undefined))
  })
})
