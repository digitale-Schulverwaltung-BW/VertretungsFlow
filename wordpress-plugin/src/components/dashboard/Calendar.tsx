import React, { useState } from 'react';
import type { Absence } from '../../types';
import {
  format,
  startOfMonth,
  endOfMonth,
  eachDayOfInterval,
  isSameMonth,
  isToday,
  parseISO,
  isWithinInterval,
  startOfDay,
  endOfDay,
  getDay
} from 'date-fns';
import { de } from 'date-fns/locale';

interface CalendarProps {
  absences: Absence[];
  onDayClick?: (date: Date, absences: Absence[]) => void;
}

const Calendar: React.FC<CalendarProps> = ({ absences, onDayClick }) => {
  const [currentMonth, setCurrentMonth] = useState(new Date());

  const monthStart = startOfMonth(currentMonth);
  const monthEnd = endOfMonth(currentMonth);
  const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd });

  // Finde Absenzen für einen bestimmten Tag
  const getAbsencesForDay = (day: Date): Absence[] => {
    const dayStart = startOfDay(day);

    return absences.filter((absence) => {
      const absenceStart = startOfDay(parseISO(absence.start_date));
      const absenceEnd = endOfDay(parseISO(absence.end_date));

      // Prüfe ob der Tag innerhalb des Abwesenheits-Zeitraums liegt
      return isWithinInterval(dayStart, { start: absenceStart, end: absenceEnd });
    });
  };

  const previousMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1));
  };

  const nextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1));
  };

  // Füge Padding-Tage am Anfang hinzu (Montag = 0)
  const firstDayOfWeek = getDay(monthStart);
  const paddingDays = firstDayOfWeek === 0 ? 6 : firstDayOfWeek - 1; // Montag als erster Tag

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          {format(currentMonth, 'MMMM yyyy', { locale: de })}
        </h3>
        <div className="flex space-x-2">
          <button
            onClick={previousMonth}
            className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50"
          >
            ←
          </button>
          <button
            onClick={nextMonth}
            className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50"
          >
            →
          </button>
        </div>
      </div>

      {/* Wochentage */}
      <div className="grid grid-cols-7 gap-2 mb-2">
        {['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].map((day) => (
          <div key={day} className="text-center text-sm font-medium text-gray-600">
            {day}
          </div>
        ))}
      </div>

      {/* Tage */}
      <div className="grid grid-cols-7 gap-1">
        {/* Padding Tage */}
        {Array.from({ length: paddingDays }).map((_, idx) => (
          <div key={`padding-${idx}`} className="h-12" />
        ))}

        {/* Tatsächliche Tage */}
        {daysInMonth.map((day) => {
          const dayAbsences = getAbsencesForDay(day);
          const hasAbsences = dayAbsences.length > 0;
          const today = isToday(day);

          return (
            <div
              key={day.toISOString()}
              onClick={() => hasAbsences && onDayClick?.(day, dayAbsences)}
              className={`
                h-12 px-1 py-1 rounded text-center text-xs flex flex-col items-center justify-center
                ${!isSameMonth(day, currentMonth) ? 'text-gray-300' : 'text-gray-900'}
                ${today ? 'bg-blue-100 font-bold' : ''}
                ${hasAbsences ? 'bg-yellow-50 cursor-pointer hover:bg-yellow-100' : ''}
                ${hasAbsences && today ? 'bg-blue-200' : ''}
              `}
            >
              <div className="leading-none">{format(day, 'd')}</div>
              {hasAbsences && (
                <div className="text-[10px] text-blue-600 leading-none mt-0.5">
                  {dayAbsences.length}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Calendar;
