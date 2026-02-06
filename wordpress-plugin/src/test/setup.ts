import '@testing-library/jest-dom'
import { expect, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers)

// Cleanup after each test
afterEach(() => {
  cleanup()
})

// Mock window.absenzflowConfig for tests
if (typeof window !== 'undefined') {
  window.absenzflowConfig = {
    apiUrl: 'http://localhost:8000/api',
    nonce: 'test-nonce',
    useProxy: false,
    user: {
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      displayName: 'Test User',
      role: 'teacher'
    }
  }
}
