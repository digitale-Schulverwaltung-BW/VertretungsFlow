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
global.window.absenzflowConfig = {
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
