import React from 'react';
import type { Absence } from '../../types';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';

interface AbsencesListModalProps {
  title: string;
  absences: Absence[];
  onClose: () => void;
  onAbsenceClick: (absence: Absence) => void;
}

const AbsencesListModal: React.FC<AbsencesListModalProps> = ({
  title,
  absences,
  onClose,
  onAbsenceClick
}) => {
  const getStatusBadge = (status: string) => {
    const statusStyles = {
      submitted: 'bg-yellow-100 text-yellow-800',
      approved: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800',
      completed: 'bg-gray-100 text-gray-800',
      draft: 'bg-gray-100 text-gray-600'
    };

    const statusLabels = {
      submitted: 'Eingereicht',
      approved: 'Genehmigt',
      rejected: 'Abgelehnt',
      completed: 'Erledigt',
      draft: 'Entwurf'
    };

    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusStyles[status as keyof typeof statusStyles] || 'bg-gray-100 text-gray-800'}`}>
        {statusLabels[status as keyof typeof statusLabels] || status}
      </span>
    );
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex min-h-full items-center justify-center p-4">
          <div className="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900">
                {title} ({absences.length})
              </h2>
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {absences.length === 0 ? (
                <p className="text-center text-gray-500 py-8">
                  Keine Abwesenheiten in diesem Status
                </p>
              ) : (
                <div className="space-y-3">
                  {absences.map((absence) => (
                    <div
                      key={absence.id}
                      onClick={() => {
                        onAbsenceClick(absence);
                        onClose();
                      }}
                      className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:bg-blue-50 cursor-pointer transition-colors"
                    >
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <p className="font-medium text-gray-900">
                            {absence.teacher.full_name || absence.teacher.username}
                          </p>
                          {getStatusBadge(absence.status)}
                        </div>
                        <p className="text-sm text-gray-600 mb-1">
                          <span className="font-medium">Zeitraum:</span>{' '}
                          {format(new Date(absence.start_date), 'dd.MM.yyyy', { locale: de })} -{' '}
                          {format(new Date(absence.end_date), 'dd.MM.yyyy', { locale: de })}
                        </p>
                        <p className="text-sm text-gray-600 mb-1">
                          <span className="font-medium">Stunden:</span> {absence.start_period} - {absence.end_period}
                        </p>
                        <p className="text-sm text-gray-500">{absence.reason}</p>
                        {absence.affected_lessons && absence.affected_lessons.length > 0 && (
                          <p className="text-xs text-gray-400 mt-1">
                            {absence.affected_lessons.length} betroffene Stunden
                          </p>
                        )}
                      </div>
                      <div className="ml-4">
                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex justify-end p-6 border-t border-gray-200">
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
              >
                Schließen
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default AbsencesListModal;
