import React from 'react';
import type { Absence } from '../../types';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';

interface AbsenceTableProps {
  absences: Absence[];
  onAbsenceClick?: (absence: Absence) => void;
}

const AbsenceTable: React.FC<AbsenceTableProps> = ({ absences, onAbsenceClick }) => {
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
                {absence.reason}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                {getStatusBadge(absence.status)}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {absence.affected_lessons?.length || 0}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default AbsenceTable;
