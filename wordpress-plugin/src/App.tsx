import React, { useEffect, useState } from 'react';
import { HashRouter, Routes, Route, Link, Navigate } from 'react-router-dom';
import api from './api/client';
import CreateAbsence from './pages/CreateAbsence';
import type { User } from './types';

const Dashboard: React.FC<{ user: User }> = ({ user }) => {
  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">Dashboard</h1>

        <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-blue-500"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-blue-700">
                <strong>Willkommen, {user.full_name}!</strong>
              </p>
              <p className="text-sm text-blue-600 mt-1">Rolle: {user.role}</p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="bg-gray-50 p-6 rounded-md border-2 border-dashed border-gray-300">
            <h2 className="text-lg font-semibold mb-2">Abwesenheit melden</h2>
            <p className="text-gray-600 mb-4">
              Melden Sie eine geplante Abwesenheit und geben Sie Hinweise für den
              Vertretungsplaner.
            </p>
            <Link
              to="/create"
              className="inline-block px-6 py-3 bg-black text-white rounded-md hover:bg-gray-800"
            >
              Neue Abwesenheit erstellen
            </Link>
          </div>

          <div className="bg-gray-50 p-4 rounded-md">
            <h2 className="text-lg font-semibold mb-2">Meine Abwesenheiten</h2>
            <p className="text-gray-600 text-sm">
              Hier werden Ihre Abwesenheiten angezeigt (noch nicht implementiert).
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

const Navigation: React.FC<{ user: User | null }> = ({ user }) => {
  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <Link to="/" className="flex items-center px-2 py-2 text-gray-900">
              <span className="text-xl font-bold">AbsenzFlow</span>
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
                  to="/create"
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
          <Route path="/" element={<Dashboard user={displayUser} />} />
          <Route path="/create" element={<CreateAbsence />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </HashRouter>
  );
}

export default App;
