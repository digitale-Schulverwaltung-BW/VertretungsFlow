import React, { useState } from 'react';
import { DayPicker, DateRange } from 'react-day-picker';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';
import 'react-day-picker/dist/style.css';
import type { AbsenceReason } from '../../types';
import { ABSENCE_REASONS } from '../../constants';

interface StepOneProps {
  onNext: (data: StepOneData) => void;
}

export interface StepOneData {
  reason: AbsenceReason;
  startDate: Date;
  endDate: Date;
  startLesson: number;
  endLesson: number;
  excursionClasses?: string;
  personalReason?: string;
}

const lessonNumbers = Array.from({ length: 16 }, (_, i) => i + 1);

const StepOne: React.FC<StepOneProps> = ({ onNext }) => {
  const [reason, setReason] = useState<AbsenceReason>('undefined');
  const [dateRange, setDateRange] = useState<DateRange | undefined>();
  const [startLesson, setStartLesson] = useState<number>(1);
  const [endLesson, setEndLesson] = useState<number>(16);
  const [errors, setErrors] = useState<string[]>([]);
  const [leftMonth, setLeftMonth] = useState<Date>(new Date());
  const [rightMonth, setRightMonth] = useState<Date>(new Date());
  const [excursionClasses, setExcursionClasses] = useState<string>('');
  const [personalReason, setPersonalReason] = useState<string>('');

  const handleStartDayClick = (day: Date) => {
    // Einzelklick im linken Picker: immer nur Start-Datum setzen
    const newStartDate = day;

    // Auto-Korrektur: Start > Ende → Ende = Start
    if (dateRange?.to && newStartDate > dateRange.to) {
      setDateRange({ from: newStartDate, to: newStartDate });
    } else {
      // Wenn kein End-Datum existiert, setze es auf Start-Datum (eintägige Absenz)
      setDateRange({ from: newStartDate, to: dateRange?.to || newStartDate });
    }
  };

  const handleStartDateSelect = (range: DateRange | undefined) => {
    if (!range) {
      setDateRange(undefined);
      return;
    }

    // Nur bei Range-Drag (beide Werte gesetzt und unterschiedlich)
    if (range.from && range.to && range.from.getTime() !== range.to.getTime()) {
      setDateRange(range);
    }
    // Bei Einzelklick wird onDayClick aufgerufen, nicht hier
  };

  const handleEndDayClick = (day: Date) => {
    // Einzelklick im rechten Picker: immer nur End-Datum setzen
    const newEndDate = day;

    // Auto-Korrektur: Ende < Start → Start = Ende
    if (dateRange?.from && newEndDate < dateRange.from) {
      setDateRange({ from: newEndDate, to: newEndDate });
    } else {
      // Wenn kein Start-Datum existiert, setze es auf End-Datum (eintägige Absenz)
      setDateRange({ from: dateRange?.from || newEndDate, to: newEndDate });
    }
  };

  const handleEndDateSelect = (range: DateRange | undefined) => {
    if (!range) {
      setDateRange(undefined);
      return;
    }

    // Nur bei Range-Drag (beide Werte gesetzt und unterschiedlich)
    if (range.from && range.to && range.from.getTime() !== range.to.getTime()) {
      setDateRange(range);
    }
    // Bei Einzelklick wird onDayClick aufgerufen, nicht hier
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const newErrors: string[] = [];

    if (reason === 'undefined') {
      newErrors.push('Bitte wählen Sie einen Absenzgrund aus.');
    }

    if (!dateRange?.from || !dateRange?.to) {
      newErrors.push('Bitte wählen Sie einen Datumszeitraum aus.');
    }

    if (endLesson < startLesson) {
      newErrors.push('Die Endstunde muss nach der Startstunde liegen.');
    }

    if (dateRange?.from && dateRange.from < new Date()) {
      newErrors.push('Das Startdatum muss in der Zukunft liegen.');
    }

    if (reason === 'excursion' && !excursionClasses.trim()) {
      newErrors.push('Bitte geben Sie die betroffenen Klassen an.');
    }

    if ((reason === 'personal' || reason === 'other') && !personalReason.trim()) {
      newErrors.push('Bitte geben Sie eine Begründung an.');
    }

    if (newErrors.length > 0) {
      setErrors(newErrors);
      return;
    }

    onNext({
      reason,
      startDate: dateRange!.from!,
      endDate: dateRange!.to!,
      startLesson,
      endLesson,
      excursionClasses: reason === 'excursion' ? excursionClasses : undefined,
      personalReason: reason === 'personal' || reason === 'other' ? personalReason : undefined,
    });
  };

  const startPickerModifiers = {
    primary: dateRange?.from ? [dateRange.from] : [],
    secondary: dateRange?.to ? [dateRange.to] : [],
  };

  const endPickerModifiers = {
    primary: dateRange?.to ? [dateRange.to] : [],
    secondary: dateRange?.from ? [dateRange.from] : [],
  };

  const modifiersClassNames = {
    primary: 'bg-black text-white font-bold rounded-full',
    secondary: 'bg-gray-300 text-gray-600 rounded-full',
  };

  const handleLeftMonthChange = (month: Date) => {
    setLeftMonth(month);
    // Nur synchronisieren wenn noch keine Auswahl
    if (!dateRange?.from) {
      setRightMonth(month);
    }
  };

  const handleRightMonthChange = (month: Date) => {
    setRightMonth(month);
    // Nur synchronisieren wenn noch keine Auswahl
    if (!dateRange?.from) {
      setLeftMonth(month);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Abwesenheit</h1>
        <p className="text-gray-600 mb-8">Meldung einer geplanten Abwesenheit</p>

        {errors.length > 0 && (
          <div className="mb-6 bg-red-50 border-l-4 border-red-500 p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-red-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <ul className="list-disc list-inside text-sm text-red-700">
                  {errors.map((error, i) => (
                    <li key={i}>{error}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Grund */}
          <div>
            <label
              htmlFor="reason"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Grund<span className="text-red-500">*</span>
            </label>
            <select
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value as AbsenceReason)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {ABSENCE_REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          {/* Exkursion: Klassen-Input */}
          {reason === 'excursion' && (
            <div>
              <label
                htmlFor="excursionClasses"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Klasse(n) <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="excursionClasses"
                value={excursionClasses}
                onChange={(e) => setExcursionClasses(e.target.value)}
                placeholder="z.B. 10a, 10b"
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>
          )}

          {/* Privat/Sonstiges: Begründung */}
          {(reason === 'personal' || reason === 'other') && (
            <div>
              <label
                htmlFor="personalReason"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Begründung <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                id="personalReason"
                value={personalReason}
                onChange={(e) => setPersonalReason(e.target.value)}
                placeholder="z.B. Arzttermin"
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>
          )}

          {/* Datum-Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Zeitraum
            </label>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-600 mb-1">von:</label>
                <DayPicker
                  mode="range"
                  selected={dateRange}
                  onSelect={handleStartDateSelect}
                  onDayClick={handleStartDayClick}
                  month={leftMonth}
                  onMonthChange={handleLeftMonthChange}
                  locale={de}
                  className="border border-gray-300 rounded-md p-3"
                  disabled={{ before: new Date() }}
                  modifiers={startPickerModifiers}
                  modifiersClassNames={modifiersClassNames}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">bis:</label>
                <DayPicker
                  mode="range"
                  selected={dateRange}
                  onSelect={handleEndDateSelect}
                  onDayClick={handleEndDayClick}
                  month={rightMonth}
                  onMonthChange={handleRightMonthChange}
                  locale={de}
                  className="border border-gray-300 rounded-md p-3"
                  disabled={{ before: new Date() }}
                  modifiers={endPickerModifiers}
                  modifiersClassNames={modifiersClassNames}
                />
              </div>
            </div>
          </div>

          {/* Stunden */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="startLesson"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Stunde (von)
              </label>
              <select
                id="startLesson"
                value={startLesson}
                onChange={(e) => setStartLesson(Number(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {lessonNumbers.map((num) => (
                  <option key={num} value={num}>
                    {num}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="endLesson"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Stunde (bis)
              </label>
              <select
                id="endLesson"
                value={endLesson}
                onChange={(e) => setEndLesson(Number(e.target.value))}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {lessonNumbers.map((num) => (
                  <option key={num} value={num}>
                    {num}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Weiter Button */}
          <div className="flex justify-end pt-4">
            <button
              type="submit"
              className="px-8 py-3 bg-black text-white rounded-md hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900"
            >
              Weiter
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default StepOne;
