import React, { useEffect, useState } from 'react';
import api from '../../api/client';
import type { User } from '../../types';
import TeacherView from './TeacherView';
import PlannerView from './PlannerView';

const Dashboard: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await api.getCurrentUser();
        setUser(userData);
      } catch (err: any) {
        setError(err.message || 'Fehler beim Laden der Benutzerdaten');
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Lädt Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error || !user) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error || 'Benutzer nicht gefunden'}</p>
        </div>
      </div>
    );
  }

  // Rolle-basiertes Rendering
  const isPlannerOrDeptHead = user.role === 'planner' ||
                              user.role === 'dept_head' ||
                              user.role === 'admin';

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">
          Willkommen, {user.full_name || user.username}
        </p>
      </div>

      {isPlannerOrDeptHead ? (
        <PlannerView user={user} />
      ) : (
        <TeacherView user={user} />
      )}
    </div>
  );
};

export default Dashboard;
