import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// WordPress stellt Config via vertretungsflowConfig bereit
declare global {
  interface Window {
    vertretungsflowConfig: {
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
const rootElement = document.getElementById('vertretungsflow-root')

if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  )
}
