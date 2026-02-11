import React from 'react';
import type { Absence } from '../../types';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';
import { getAbsenceReasonLabel } from '../../constants';

interface AbsenceTableProps {
  absences: Absence[];
  onAbsenceClick?: (absence: Absence) => void;
  onDeleteAbsence?: (absence: Absence, e: React.MouseEvent) => void;
  deletingId?: number | null;
}

const AbsenceTable: React.FC<AbsenceTableProps> = ({
  absences,
  onAbsenceClick,
  onDeleteAbsence,
  deletingId,
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

  const formatDate = (dateStr: string) => {
    return format(new Date(dateStr), 'dd.MM.yyyy', { locale: de });
  };

  if (absences.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        Keine Abwesenheiten vorhanden
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Lehrkraft
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Zeitraum
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Grund
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Status
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
              Betroffene Stunden
            </th>
            {onDeleteAbsence && (
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Aktionen
              </th>
            )}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {absences.map((absence) => (
            <tr
              key={absence.id}
              onClick={() => onAbsenceClick?.(absence)}
              className={onAbsenceClick ? 'hover:bg-gray-50 cursor-pointer' : ''}
            >
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {absence.teacher.full_name || absence.teacher.username}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {formatDate(absence.start_date)} - {formatDate(absence.end_date)}
              </td>
              <td className="px-6 py-4 text-sm text-gray-600">
                {getAbsenceReasonLabel(absence.reason)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                {getStatusBadge(absence.status)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {absence.affected_lessons?.length || 0}
              </td>
              {onDeleteAbsence && (
                <td className="px-6 py-4 whitespace-nowrap">
                  {absence.status !== 'completed' && (
                    <button
                      onClick={(e) => onDeleteAbsence(absence, e)}
                      disabled={deletingId === absence.id}
                      className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Abwesenheit löschen"
                    >
                      {deletingId === absence.id ? 'Lädt...' : 'Löschen'}
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AbsenceTable;
