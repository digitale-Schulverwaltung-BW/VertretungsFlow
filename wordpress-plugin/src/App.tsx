import React, { useEffect, useState } from 'react';
import { HashRouter, Routes, Route, Link, Navigate } from 'react-router-dom';
import api from './api/client';
import Dashboard from './pages/Dashboard';
import CreateAbsence from './pages/CreateAbsence';
import AbsenceDetail from './pages/AbsenceDetail';
import type { User } from './types';

const Navigation: React.FC<{ user: User | null }> = ({ user }) => {
  const config = window.absenzflowConfig;
  const logoUrl = config?.pluginUrl ? `${config.pluginUrl}assets/logo.png` : '';

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <Link to="/" className="flex items-center px-2 py-2 text-gray-900">
              {logoUrl ? (
                <img src={logoUrl} alt="AbsenzFlow" className="h-[30px]" />
              ) : (
                <span className="text-xl font-bold">AbsenzFlow</span>
              )}
            </Link>
            {user && (
              <>
                <Link
                  to="/"
                  className="ml-8 flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
                >
                  Dashboard
                </Link>
                <Link
                  to="/create-absence"
                  className="flex items-center px-3 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
                >
                  Neue Abwesenheit
                </Link>
              </>
            )}
          </div>
          {user && (
            <div className="flex items-center">
              <span className="text-sm text-gray-600">{user.full_name}</span>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const config = window.absenzflowConfig;

  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      // Set API base URL from WordPress config
      if (config?.apiUrl) {
        api.setBaseURL(config.apiUrl);
      }

      // Check for stored token
      const token = api.getToken();
      if (token) {
        api.setToken(token);
        const currentUser = await api.getCurrentUser();
        setUser(currentUser);
      }
    } catch (error) {
      console.error('Failed to initialize app:', error);
      // Clear invalid token
      api.setToken(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  // For now, use WordPress user info as fallback
  // In production, proper authentication flow would be needed
  const displayUser: User = user || {
    id: 0,
    username: config?.user?.username || 'unknown',
    email: '',
    full_name: config?.user?.displayName || 'Unbekannter Benutzer',
    role: config?.user?.role || 'teacher',
    is_active: true,
    created_at: new Date().toISOString(),
  };

  return (
    <HashRouter>
      <div className="min-h-screen bg-gray-50">
        <Navigation user={displayUser} />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/create-absence" element={<CreateAbsence />} />
          <Route path="/absence/:id" element={<AbsenceDetail />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </HashRouter>
  );
}

export default App;
