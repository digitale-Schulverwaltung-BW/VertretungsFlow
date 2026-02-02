import React from 'react';
import type { Absence } from '../../types';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';
import { getAbsenceReasonLabel } from '../../constants';

interface ToDoListProps {
  absences: Absence[];
  userRole: string;
  onActionClick?: (absence: Absence) => void;
}

const ToDoList: React.FC<ToDoListProps> = ({ absences, userRole, onActionClick }) => {
  const getActionLabel = (absence: Absence) => {
    if (userRole === 'dept_head' && absence.status === 'submitted') {
      return 'Genehmigen';
    }
    if (userRole === 'planner' && absence.status === 'approved') {
      return 'Eintragen';
    }
    return 'Ansehen';
  };

  if (absences.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        Keine ausstehenden Aufgaben
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {absences.map((absence) => (
        <div
          key={absence.id}
          className="grid grid-cols-[2fr_2fr_1.5fr_auto] gap-3 items-center p-3 bg-white border border-gray-200 rounded-lg hover:border-blue-300 transition-colors"
        >
          <div className="font-medium text-gray-900 truncate">
            {absence.teacher.full_name || absence.teacher.username}
          </div>
          <div className="text-sm text-gray-600 whitespace-nowrap">
            {format(new Date(absence.start_date), 'dd.MM.yyyy', { locale: de })} - {' '}
            {format(new Date(absence.end_date), 'dd.MM.yyyy', { locale: de })}
          </div>
          <div className="text-sm text-gray-500 truncate">
            {getAbsenceReasonLabel(absence.reason)}
          </div>
          <button
            onClick={() => onActionClick?.(absence)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium whitespace-nowrap"
          >
            {getActionLabel(absence)}
          </button>
        </div>
      ))}
    </div>
  );
};

export default ToDoList;
