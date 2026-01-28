/**
 * Main App Component
 */
import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import api from './api/client';

// Components
import Navigation from './components/Navigation';
import LoginForm from './components/LoginForm';

// Pages
import Dashboard from './pages/Dashboard';
import CreateAbsence from './pages/CreateAbsence';
import AbsenceList from './pages/AbsenceList';
import AbsenceDetail from './pages/AbsenceDetail';
import PlannerView from './pages/PlannerView';

/**
 * Main App Component
 */
const App = ({ config }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Initialize API client with config
  useEffect(() => {
    api.setBaseURL(config.apiUrl);
    checkAuthentication();
  }, [config.apiUrl]);
  
  /**
   * Check if user is authenticated
   */
  const checkAuthentication = async () => {
    const token = localStorage.getItem('absenzflow_token');
    
    if (token) {
      try {
        api.setToken(token);
        const userData = await api.getCurrentUser();
        setUser(userData);
        setIsAuthenticated(true);
      } catch (error) {
        console.error('Authentication check failed:', error);
        localStorage.removeItem('absenzflow_token');
        setIsAuthenticated(false);
      }
    }
    
    setLoading(false);
  };
  
  /**
   * Handle login
   */
  const handleLogin = async (username, password) => {
    try {
      const response = await api.login(username, password);
      localStorage.setItem('absenzflow_token', response.access_token);
      api.setToken(response.access_token);
      
      const userData = await api.getCurrentUser();
      setUser(userData);
      setIsAuthenticated(true);
      
      return { success: true };
    } catch (error) {
      console.error('Login failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login fehlgeschlagen' 
      };
    }
  };
  
  /**
   * Handle logout
   */
  const handleLogout = () => {
    localStorage.removeItem('absenzflow_token');
    api.setToken(null);
    setUser(null);
    setIsAuthenticated(false);
  };
  
  // Show loading spinner
  if (loading) {
    return (
      <div className="absenzflow-loading">
        <div className="spinner"></div>
        <p>Lädt...</p>
      </div>
    );
  }
  
  // Show login form if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="absenzflow-container">
        <div className="absenzflow-login-wrapper">
          <h1>AbsenzFlow</h1>
          <p>Bitte melden Sie sich an</p>
          <LoginForm onLogin={handleLogin} />
        </div>
      </div>
    );
  }
  
  // Main app with routing
  return (
    <Router>
      <div className="absenzflow-container">
        <Navigation user={user} onLogout={handleLogout} />
        
        <main className="absenzflow-main">
          <Routes>
            <Route path="/" element={<Dashboard user={user} />} />
            <Route path="/create" element={<CreateAbsence user={user} />} />
            <Route path="/absences" element={<AbsenceList user={user} />} />
            <Route path="/absences/:id" element={<AbsenceDetail user={user} />} />
            <Route path="/planner" element={<PlannerView user={user} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
