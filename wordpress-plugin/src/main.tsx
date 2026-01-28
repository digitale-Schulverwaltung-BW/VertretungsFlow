import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// WordPress stellt Config via absenzflowConfig bereit
declare global {
  interface Window {
    absenzflowConfig: {
      apiUrl: string
      nonce: string
      user: {
        id: number
        username: string
        email: string
        displayName: string
        role: string
      }
    }
  }
}

// Root Element
const rootElement = document.getElementById('absenzflow-root')

if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
}
