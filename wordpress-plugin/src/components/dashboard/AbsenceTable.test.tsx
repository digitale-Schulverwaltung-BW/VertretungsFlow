import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect } from 'vitest'
import AbsenceTable from './AbsenceTable'
import type { Absence } from '../../types'

const mockAbsence: Absence = {
  id: 1,
  teacher_id: 1,
  reason: 'sick',
  start_date: '2024-01-15',
  end_date: '2024-01-15',
  start_period: 1,
  end_period: 3,
  status: 'submitted',
  teacher: {
    id: 1,
    username: 'testuser',
    email: 'test@example.com',
    full_name: 'Test Teacher',
    role: 'teacher',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z'
  },
  affected_lessons: [
    {
      date: '2024-01-15',
      period: 1,
      subject: 'Mathematik',
      class_name: '10a'
    },
    {
      date: '2024-01-15',
      period: 2,
      subject: 'Mathematik',
      class_name: '10b'
    }
  ]
}

describe('AbsenceTable', () => {
  it('renders table headers correctly', () => {
    render(<AbsenceTable absences={[mockAbsence]} />)

    expect(screen.getByText('Lehrkraft')).toBeInTheDocument()
    expect(screen.getByText('Zeitraum')).toBeInTheDocument()
    expect(screen.getByText('Grund')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Betroffene Stunden')).toBeInTheDocument()
  })

  it('renders absence data correctly', () => {
    render(<AbsenceTable absences={[mockAbsence]} />)

    // Component renders both card and table view simultaneously
    expect(screen.getAllByText('Test Teacher').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Krank').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Eingereicht').length).toBeGreaterThan(0)
    expect(screen.getAllByText('2').length).toBeGreaterThan(0)
    // Table uses hyphen separator, card uses em-dash – check table cell specifically
    expect(screen.getByText('15.01.2024 - 15.01.2024')).toBeInTheDocument()
  })

  it('shows empty state when no absences', () => {
    render(<AbsenceTable absences={[]} />)

    expect(screen.getByText('Keine Abwesenheiten vorhanden')).toBeInTheDocument()
  })

  it('calls onAbsenceClick when row is clicked', async () => {
    const handleClick = vi.fn()
    const user = userEvent.setup()

    render(<AbsenceTable absences={[mockAbsence]} onAbsenceClick={handleClick} />)

    // Find the table row (not the card view) by locating the <td> with the teacher name
    const teacherElements = screen.getAllByText('Test Teacher')
    const row = teacherElements.map(el => el.closest('tr')).find(Boolean) as HTMLElement
    expect(row).toBeInTheDocument()

    await user.click(row)
    expect(handleClick).toHaveBeenCalledWith(mockAbsence)
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('does not add click handler when onAbsenceClick is not provided', () => {
    render(<AbsenceTable absences={[mockAbsence]} />)

    const teacherElements = screen.getAllByText('Test Teacher')
    const row = teacherElements.map(el => el.closest('tr')).find(Boolean) as HTMLElement
    expect(row).not.toHaveClass('cursor-pointer')
  })

  it('renders correct status badges', () => {
    const absences: Absence[] = [
      { ...mockAbsence, id: 1, status: 'submitted' },
      { ...mockAbsence, id: 2, status: 'approved' },
      { ...mockAbsence, id: 3, status: 'completed' },
      { ...mockAbsence, id: 4, status: 'rejected' },
    ]

    render(<AbsenceTable absences={absences} />)

    // Each status appears in both card and table view
    expect(screen.getAllByText('Eingereicht').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Genehmigt').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Erledigt').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Abgelehnt').length).toBeGreaterThan(0)
  })

  it('renders multiple absences', () => {
    const absences: Absence[] = [
      mockAbsence,
      {
        ...mockAbsence,
        id: 2,
        teacher: {
          ...mockAbsence.teacher,
          full_name: 'Another Teacher'
        },
        reason: 'training',
        status: 'approved'
      }
    ]

    render(<AbsenceTable absences={absences} />)

    expect(screen.getAllByText('Test Teacher').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Another Teacher').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Krank').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Fortbildung').length).toBeGreaterThan(0)
  })

  it('handles absence with no affected lessons', () => {
    const absenceWithoutLessons = {
      ...mockAbsence,
      affected_lessons: []
    }

    render(<AbsenceTable absences={[absenceWithoutLessons]} />)

    expect(screen.getAllByText('0').length).toBeGreaterThan(0)
  })

  it('uses username when full_name is not available', () => {
    const absenceWithoutFullName = {
      ...mockAbsence,
      teacher: {
        ...mockAbsence.teacher,
        full_name: ''
      }
    }

    render(<AbsenceTable absences={[absenceWithoutFullName]} />)

    expect(screen.getAllByText('testuser').length).toBeGreaterThan(0)
  })

  it('only shows the delete button for draft/submitted absences', () => {
    const absences: Absence[] = [
      { ...mockAbsence, id: 1, status: 'draft' },
      { ...mockAbsence, id: 2, status: 'submitted' },
      { ...mockAbsence, id: 3, status: 'approved' },
      { ...mockAbsence, id: 4, status: 'completed' },
      { ...mockAbsence, id: 5, status: 'rejected' },
    ]

    render(<AbsenceTable absences={absences} onDeleteAbsence={vi.fn()} />)

    // Card- und Tabellen-Layout rendern je einen Button pro löschbarer Absenz
    expect(screen.getAllByTitle('Abwesenheit löschen')).toHaveLength(4)
  })
})
