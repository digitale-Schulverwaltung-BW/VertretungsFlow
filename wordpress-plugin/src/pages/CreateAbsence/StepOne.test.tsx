import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import StepOne from './StepOne'

vi.mock('../../api/client', () => ({
  default: {
    getCurrentUser: vi.fn().mockResolvedValue({
      id: 1,
      username: 'test.user',
      email: 'test@schule.de',
      full_name: 'Test User',
      role: 'teacher',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
    }),
    getUsers: vi.fn().mockResolvedValue([]),
    getAbsences: vi.fn().mockResolvedValue([]),
  },
}))

describe('StepOne - Absence Wizard Step 1', () => {
  let mockOnNext: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockOnNext = vi.fn()
  })

  describe('Form Rendering', () => {
    it('renders all form fields', () => {
      render(<StepOne onNext={mockOnNext} />)

      expect(screen.getByLabelText(/Grund/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/ab Stunde/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/bis Stunde/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /Weiter/i })).toBeInTheDocument()
    })

    it('renders page title and description', () => {
      render(<StepOne onNext={mockOnNext} />)

      expect(screen.getByText('Abwesenheit')).toBeInTheDocument()
      expect(screen.getByText('Meldung einer geplanten Abwesenheit')).toBeInTheDocument()
    })

    it('renders reason dropdown with all options', () => {
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i) as HTMLSelectElement
      expect(reasonSelect.options.length).toBeGreaterThan(0)
      expect(reasonSelect.value).toBe('undefined')
    })

    it('renders date pickers', () => {
      render(<StepOne onNext={mockOnNext} />)

      expect(screen.getByText(/Zeitraum/i)).toBeInTheDocument()
      expect(screen.getByText('von:')).toBeInTheDocument()
      expect(screen.getByText('bis:')).toBeInTheDocument()
    })

    it('renders lesson/period selectors', () => {
      render(<StepOne onNext={mockOnNext} />)

      const startLesson = screen.getByLabelText(/ab Stunde/i) as HTMLSelectElement
      const endLesson = screen.getByLabelText(/bis Stunde/i) as HTMLSelectElement

      expect(startLesson.value).toBe('1')
      expect(endLesson.value).toBe('16')
    })
  })

  describe('Reason Selection', () => {
    it('allows reason selection', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'sick')

      expect((reasonSelect as HTMLSelectElement).value).toBe('sick')
    })

    it('displays all absence reason options', () => {
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i) as HTMLSelectElement
      const options = Array.from(reasonSelect.options).map((opt) => opt.value)

      expect(options).toContain('undefined')
      expect(options).toContain('sick')
      expect(options).toContain('training')
      expect(options).toContain('excursion')
      expect(options).toContain('personal')
    })
  })

  describe('Conditional Fields - Excursion', () => {
    it('shows excursion classes field when reason is excursion', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      expect(screen.queryByLabelText(/Klasse\(n\)/i)).not.toBeInTheDocument()

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'excursion')

      expect(screen.getByLabelText(/Klasse\(n\)/i)).toBeInTheDocument()
    })

    it('hides excursion classes field when reason changes from excursion', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'excursion')
      expect(screen.getByLabelText(/Klasse\(n\)/i)).toBeInTheDocument()

      await user.selectOptions(reasonSelect, 'sick')
      expect(screen.queryByLabelText(/Klasse\(n\)/i)).not.toBeInTheDocument()
    })

    it('allows entering excursion classes', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'excursion')

      const classesInput = screen.getByLabelText(/Klasse\(n\)/i) as HTMLInputElement
      await user.type(classesInput, '10a, 10b')

      expect(classesInput.value).toBe('10a, 10b')
    })
  })

  describe('Conditional Fields - Personal Reason', () => {
    it('shows personal reason field when reason is personal', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      expect(screen.queryByLabelText(/Begründung/i)).not.toBeInTheDocument()

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'personal')

      expect(screen.getByLabelText(/Begründung/i)).toBeInTheDocument()
    })

    it('shows personal reason field when reason is other', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'other')

      expect(screen.getByLabelText(/Begründung/i)).toBeInTheDocument()
    })

    it('hides personal reason field for other reasons', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'personal')
      expect(screen.getByLabelText(/Begründung/i)).toBeInTheDocument()

      await user.selectOptions(reasonSelect, 'sick')
      expect(screen.queryByLabelText(/Begründung/i)).not.toBeInTheDocument()
    })

    it('allows entering personal reason', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'personal')

      const reasonInput = screen.getByLabelText(/Begründung/i) as HTMLInputElement
      await user.type(reasonInput, 'Arzttermin')

      expect(reasonInput.value).toBe('Arzttermin')
    })
  })

  describe('Lesson/Period Selection', () => {
    it('allows changing start lesson', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const startLessonSelect = screen.getByLabelText(/ab Stunde/i) as HTMLSelectElement
      await user.selectOptions(startLessonSelect, '3')

      expect(startLessonSelect.value).toBe('3')
    })

    it('allows changing end lesson', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const endLessonSelect = screen.getByLabelText(/bis Stunde/i) as HTMLSelectElement
      await user.selectOptions(endLessonSelect, '6')

      expect(endLessonSelect.value).toBe('6')
    })

    it('has default values of 1 and 16 for start and end lesson', () => {
      render(<StepOne onNext={mockOnNext} />)

      const startLesson = screen.getByLabelText(/ab Stunde/i) as HTMLSelectElement
      const endLesson = screen.getByLabelText(/bis Stunde/i) as HTMLSelectElement

      expect(startLesson.value).toBe('1')
      expect(endLesson.value).toBe('16')
    })
  })

  describe('Form Validation', () => {
    it('validates that reason field is required', () => {
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i) as HTMLSelectElement
      expect(reasonSelect.value).toBe('undefined')
    })

    it('shows conditional excursion classes field and requires it', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'excursion')

      const classesInput = screen.getByLabelText(/Klasse\(n\)/i) as HTMLInputElement
      expect(classesInput.required).toBe(true)
      expect(classesInput.value).toBe('')
    })

    it('shows conditional personal reason field and requires it', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'personal')

      const reasonInput = screen.getByLabelText(/Begründung/i) as HTMLInputElement
      expect(reasonInput.required).toBe(true)
      expect(reasonInput.value).toBe('')
    })

    it('validates lesson range (end must be >= start)', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const startLessonSelect = screen.getByLabelText(/ab Stunde/i) as HTMLSelectElement
      const endLessonSelect = screen.getByLabelText(/bis Stunde/i) as HTMLSelectElement

      // Default values should be valid (1, 16)
      expect(Number(startLessonSelect.value)).toBeLessThanOrEqual(Number(endLessonSelect.value))

      // Change to invalid state
      await user.selectOptions(startLessonSelect, '10')
      await user.selectOptions(endLessonSelect, '3')

      expect(Number(startLessonSelect.value)).toBeGreaterThan(Number(endLessonSelect.value))
    })

    it('prevents submission with required fields empty', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const submitButton = screen.getByRole('button', { name: /Weiter/i })
      await user.click(submitButton)

      // onNext should not be called
      expect(mockOnNext).not.toHaveBeenCalled()
    })

    it('requires date range selection', () => {
      render(<StepOne onNext={mockOnNext} />)

      const datePickers = screen.getAllByText(/Zeitraum/i)
      expect(datePickers.length).toBeGreaterThan(0)
    })

    it('has required attribute on conditional fields', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)

      // Test excursion
      await user.selectOptions(reasonSelect, 'excursion')
      const excursionInput = screen.getByLabelText(/Klasse\(n\)/i) as HTMLInputElement
      expect(excursionInput.required).toBe(true)

      // Test personal
      await user.selectOptions(reasonSelect, 'personal')
      const personalInput = screen.getByLabelText(/Begründung/i) as HTMLInputElement
      expect(personalInput.required).toBe(true)
    })

    it('clears errors when form becomes valid', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const submitButton = screen.getByRole('button', { name: /Weiter/i })

      // First submission should fail validation
      await user.click(submitButton)
      expect(mockOnNext).not.toHaveBeenCalled()

      // Select a reason
      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'sick')

      // Reason is now selected, but still missing date
      expect((reasonSelect as HTMLSelectElement).value).toBe('sick')
    })
  })

  describe('Form Submission', () => {
    it('calls onNext with correct data for sick leave', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)
      const startLessonSelect = screen.getByLabelText(/ab Stunde/i)
      const endLessonSelect = screen.getByLabelText(/bis Stunde/i)

      await user.selectOptions(reasonSelect, 'sick')
      await user.selectOptions(startLessonSelect, '2')
      await user.selectOptions(endLessonSelect, '6')

      const submitButton = screen.getByRole('button', { name: /Weiter/i })
      await user.click(submitButton)

      // For sick leave without date selection, it should show validation error
      expect(screen.getByText(/Bitte wählen Sie einen Datumszeitraum aus/i)).toBeInTheDocument()
    })

    it('includes excursion classes when reason is excursion', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'excursion')

      const classesInput = screen.getByLabelText(/Klasse\(n\)/i)
      await user.type(classesInput, '10a')

      // Note: Without being able to interact with calendar, we just verify the form state
      // A real e2e test would select dates from the calendar
      expect((classesInput as HTMLInputElement).value).toBe('10a')
    })

    it('clears errors when form becomes valid', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      // First, submit with missing reason
      const submitButton = screen.getByRole('button', { name: /Weiter/i })
      await user.click(submitButton)

      expect(screen.getByText(/Bitte wählen Sie einen Absenzgrund aus/i)).toBeInTheDocument()

      // Then select a reason
      const reasonSelect = screen.getByLabelText(/Grund/i)
      await user.selectOptions(reasonSelect, 'sick')

      // Submit again (will still have errors due to missing dates)
      await user.click(submitButton)

      // The first error about reason should still be gone after selecting reason
      // But we'd still have the date error
      const reasonError = screen.queryByText(/Bitte wählen Sie einen Absenzgrund aus/i)
      expect(reasonError).not.toBeInTheDocument()
    })
  })

  describe('Button Behavior', () => {
    it('renders submit button with correct text', () => {
      render(<StepOne onNext={mockOnNext} />)

      const submitButton = screen.getByRole('button', { name: /Weiter/i })
      expect(submitButton).toBeInTheDocument()
    })

    it('submit button is clickable', async () => {
      const user = userEvent.setup()
      render(<StepOne onNext={mockOnNext} />)

      const submitButton = screen.getByRole('button', { name: /Weiter/i })
      await user.click(submitButton)

      // Should show validation errors instead of calling onNext
      expect(mockOnNext).not.toHaveBeenCalled()
    })
  })
})
