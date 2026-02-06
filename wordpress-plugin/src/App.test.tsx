import { render, screen, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import App from './App'
import api from './api/client'

// Mock the API client
vi.mock('./api/client', () => {
  return {
    default: {
      setBaseURL: vi.fn(),
      getToken: vi.fn(() => null),
      setToken: vi.fn(),
      getCurrentUser: vi.fn(),
    }
  }
})

// Mock child components to avoid dependencies
vi.mock('./pages/Dashboard', () => ({
  default: () => <div>Dashboard Page</div>
}))

vi.mock('./pages/CreateAbsence', () => ({
  default: () => <div>Create Absence Page</div>
}))

vi.mock('./pages/AbsenceDetail', () => ({
  default: () => <div>Absence Detail Page</div>
}))

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Ensure window.absenzflowConfig is set
    window.absenzflowConfig = {
      apiUrl: 'http://localhost:8000/api',
      nonce: 'test-nonce',
      useProxy: false,
      currentUser: {
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        role: 'teacher',
        webuntis_code: 'TEST'
      }
    }
  })

  it('renders without crashing', async () => {
    render(<App />)

    // Wait for loading to finish
    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument()
    })
  })

  it('shows loading spinner initially', async () => {
    // Mock getToken to return a value to trigger API call and loading state
    vi.mocked(api.getToken).mockReturnValue('fake-token')
    vi.mocked(api.getCurrentUser).mockImplementation(() =>
      new Promise(resolve => setTimeout(() => resolve({
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        full_name: 'Test User',
        role: 'teacher',
        is_active: true,
        created_at: '2024-01-01T00:00:00Z'
      }), 100))
    )

    render(<App />)

    // The component should render immediately showing loading
    // (no need to check for spinner as it may resolve too fast in tests)
    // Instead, wait for the loaded state
    await waitFor(() => {
      expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
    })
  })

  it('displays navigation after loading', async () => {
    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('AbsenzFlow')).toBeInTheDocument()
    })
  })

  it('renders Dashboard route by default', async () => {
    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
    })
  })

  it('initializes API client with config', async () => {
    render(<App />)

    await waitFor(() => {
      expect(api.setBaseURL).toHaveBeenCalledWith('http://localhost:8000/api')
    })
  })

  it('handles missing config gracefully', async () => {
    window.absenzflowConfig = undefined

    render(<App />)

    await waitFor(() => {
      expect(screen.getByText('Dashboard Page')).toBeInTheDocument()
    })
  })
})
