/**
 * AbsenzFlow WordPress Plugin - React App Entry Point
 */
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/main.css';

// Wait for DOM to be ready
document.addEventListener('DOMContentLoaded', () => {
  const rootElement = document.getElementById('absenzflow-root');
  
  if (rootElement) {
    const root = ReactDOM.createRoot(rootElement);
    
    // Get configuration from WordPress
    const config = window.absenzflowConfig || {
      apiUrl: 'http://localhost:8000/api/v1',
      currentUser: {
        username: '',
        email: '',
        displayName: 'Guest',
      },
    };
    
    root.render(
      <React.StrictMode>
        <App config={config} />
      </React.StrictMode>
    );
  }
});
