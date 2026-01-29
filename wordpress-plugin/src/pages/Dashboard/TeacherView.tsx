import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api/client';
import type { User, Absence } from '../../types';
import AbsenceTable from '../../components/dashboard/AbsenceTable';

interface TeacherViewProps {
  user: User;
}

const TeacherView: React.FC<TeacherViewProps> = ({ user }) => {
  const [absences, setAbsences] = useState<Absence[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const loadAbsences = async () => {
      try {
        const data = await api.getAbsences();
        setAbsences(data);
      } catch (err: any) {
        setError(err.message || 'Fehler beim Laden der Abwesenheiten');
      } finally {
        setLoading(false);
      }
    };

    loadAbsences();
  }, []);

  const handleAbsenceClick = (absence: Absence) => {
    navigate(`/absence/${absence.id}`);
  };

  const handleNewAbsence = () => {
    navigate('/create-absence');
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Lädt Abwesenheiten...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header mit Button */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-gray-900">
          Meine Abwesenheiten
        </h2>
        <button
          onClick={handleNewAbsence}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
        >
          + Neue Abwesenheit
        </button>
      </div>

      {/* Tabelle */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <AbsenceTable absences={absences} onAbsenceClick={handleAbsenceClick} />
      </div>

      {/* Info wenn keine Abwesenheiten */}
      {absences.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 mb-4">Sie haben noch keine Abwesenheiten gemeldet.</p>
          <button
            onClick={handleNewAbsence}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Erste Abwesenheit erstellen
          </button>
        </div>
      )}
    </div>
  );
};

export default TeacherView;
