import React, { useEffect, useState } from 'react';
import api from '../../api/client';
import type { User, Absence } from '../../types';
import StatCard from '../../components/dashboard/StatCard';
import ToDoList from '../../components/dashboard/ToDoList';
import Calendar from '../../components/dashboard/Calendar';
import AbsenceTable from '../../components/dashboard/AbsenceTable';
import DayAbsencesModal from '../../components/dashboard/DayAbsencesModal';
import AbsencesListModal from '../../components/dashboard/AbsencesListModal';

interface PlannerViewProps {
  user: User;
}

const PlannerView: React.FC<PlannerViewProps> = ({ user }) => {
  const [absences, setAbsences] = useState<Absence[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [calendarExpanded, setCalendarExpanded] = useState(false);
  const [absencesExpanded, setAbsencesExpanded] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedDayAbsences, setSelectedDayAbsences] = useState<Absence[]>([]);
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [statusModalTitle, setStatusModalTitle] = useState('');
  const [statusModalAbsences, setStatusModalAbsences] = useState<Absence[]>([]);

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

  // Statistiken berechnen
  const stats = {
    pending: absences.filter(a => a.status === 'submitted').length,
    approved: absences.filter(a => a.status === 'approved').length,
    completed: absences.filter(a => a.status === 'completed').length,
    totalLessons: absences.reduce((sum, a) => sum + (a.affected_lessons?.length || 0), 0)
  };

  // To-Do Liste: Absenzen die Aktion benötigen
  const todoAbsences = absences.filter(a => {
    if (user.role === 'dept_head') {
      return a.status === 'submitted';
    }
    if (user.role === 'planner') {
      return a.status === 'approved';
    }
    return false;
  });

  const handleAbsenceAction = (absence: Absence) => {
    window.location.hash = `/absence/${absence.id}`;
  };

  const handleDayClick = (date: Date, dayAbsences: Absence[]) => {
    setSelectedDate(date);
    setSelectedDayAbsences(dayAbsences);
    setModalOpen(true);
  };

  const handleAbsenceClick = (absence: Absence) => {
    window.location.hash = `/absence/${absence.id}`;
  };

  const handleStatCardClick = (status: string, title: string) => {
    const filtered = absences.filter(a => a.status === status);
    setStatusModalTitle(title);
    setStatusModalAbsences(filtered);
    setStatusModalOpen(true);
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Lädt Dashboard...</p>
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
      {/* Statistik-Karten */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Eingereicht"
          value={stats.pending}
          bgColor="bg-yellow-50"
          textColor="text-yellow-900"
          onClick={() => handleStatCardClick('submitted', 'Eingereichte Abwesenheiten')}
        />
        <StatCard
          title="Genehmigt"
          value={stats.approved}
          bgColor="bg-green-50"
          textColor="text-green-900"
          onClick={() => handleStatCardClick('approved', 'Genehmigte Abwesenheiten')}
        />
        <StatCard
          title="Erledigt"
          value={stats.completed}
          bgColor="bg-blue-50"
          textColor="text-blue-900"
          onClick={() => handleStatCardClick('completed', 'Erledigte Abwesenheiten')}
        />
        <StatCard
          title="Betroffene Stunden"
          value={stats.totalLessons}
          bgColor="bg-purple-50"
          textColor="text-purple-900"
        />
      </div>

      {/* To-Do Liste */}
      {todoAbsences.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Ausstehende Aufgaben ({todoAbsences.length})
          </h2>
          <ToDoList
            absences={todoAbsences}
            userRole={user.role}
            onActionClick={handleAbsenceAction}
          />
        </div>
      )}

      {/* Kalender (Expandable) */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <button
          onClick={() => setCalendarExpanded(!calendarExpanded)}
          className="group w-full flex items-center justify-between text-left hover:bg-gray-700 rounded-lg px-2 -mx-2 -my-1 transition-colors"
        >
          <h2 className="text-lg font-semibold text-gray-900 group-hover:text-white">
            Kalender
          </h2>
          <span className="text-gray-500 group-hover:text-white">
            {calendarExpanded ? '▼' : '▶'}
          </span>
        </button>

        {calendarExpanded && (
          <div className="mt-4">
            <Calendar absences={absences} onDayClick={handleDayClick} />
          </div>
        )}
      </div>

      {/* Alle Abwesenheiten (Expandable) */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <button
          onClick={() => setAbsencesExpanded(!absencesExpanded)}
          className="group w-full flex items-center justify-between text-left hover:bg-gray-700 rounded-lg px-2 -mx-2 -my-1 transition-colors"
        >
          <h2 className="text-lg font-semibold text-gray-900 group-hover:text-white">
            Alle Abwesenheiten ({absences.length})
          </h2>
          <span className="text-gray-500 group-hover:text-white">
            {absencesExpanded ? '▼' : '▶'}
          </span>
        </button>

        {absencesExpanded && (
          <div className="mt-4">
            <AbsenceTable absences={absences} onAbsenceClick={handleAbsenceClick} />
          </div>
        )}
      </div>

      {/* Day Absences Modal */}
      {modalOpen && selectedDate && (
        <DayAbsencesModal
          date={selectedDate}
          absences={selectedDayAbsences}
          onClose={() => setModalOpen(false)}
          onAbsenceClick={handleAbsenceClick}
        />
      )}

      {/* Status Filter Modal */}
      {statusModalOpen && (
        <AbsencesListModal
          title={statusModalTitle}
          absences={statusModalAbsences}
          onClose={() => setStatusModalOpen(false)}
          onAbsenceClick={handleAbsenceClick}
        />
      )}
    </div>
  );
};

export default PlannerView;
