import React, { useState } from 'react';
import { DayPicker, DateRange } from 'react-day-picker';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';
import 'react-day-picker/dist/style.css';
import type { AbsenceReason } from '../../types';

interface StepOneProps {
  onNext: (data: StepOneData) => void;
}

export interface StepOneData {
  reason: AbsenceReason;
  startDate: Date;
  endDate: Date;
  startLesson: number;
  endLesson: number;
}

const reasons: Array<{ value: AbsenceReason; label: string }> = [
  { value: 'training', label: 'Fortbildung' },
  { value: 'exam', label: 'Prüfung' },
  { value: 'excursion', label: 'Exkursion' },
  { value: 'sick', label: 'Krank' },
  { value: 'personal', label: 'Privat' },
  { value: 'official', label: 'Dienstlich' },
  { value: 'other', label: 'Sonstiges' },
];

const lessonNumbers = Array.from({ length: 16 }, (_, i) => i + 1);

const StepOne: React.FC<StepOneProps> = ({ onNext }) => {
  const [reason, setReason] = useState<AbsenceReason>('training');
  const [dateRange, setDateRange] = useState<DateRange | undefined>();
  const [startLesson, setStartLesson] = useState<number>(1);
  const [endLesson, setEndLesson] = useState<number>(16);
  const [errors, setErrors] = useState<string[]>([]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const newErrors: string[] = [];

    if (!dateRange?.from || !dateRange?.to) {
      newErrors.push('Bitte wählen Sie einen Datumszeitraum aus.');
    }

    if (endLesson < startLesson) {
      newErrors.push('Die Endstunde muss nach der Startstunde liegen.');
    }

    if (dateRange?.from && dateRange.from < new Date()) {
      newErrors.push('Das Startdatum muss in der Zukunft liegen.');
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
    });
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Abwesenheit</h1>
        <p className="text-gray-600 mb-8">Meldung einer geplanten Abwesenheit</p>

        {errors.length > 0 && (
          <div className="mb-6 bg-red-50 border-l-4 border-red-500 p-4">
            <div className="flex">
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
              Grund
            </label>
            <select
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value as AbsenceReason)}
              className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {reasons.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>

          {/* Datum-Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Zeitraum
            </label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-600 mb-1">von:</label>
                <DayPicker
                  mode="range"
                  selected={dateRange}
                  onSelect={setDateRange}
                  locale={de}
                  className="border border-gray-300 rounded-md p-3"
                  disabled={{ before: new Date() }}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">bis:</label>
                <DayPicker
                  mode="range"
                  selected={dateRange}
                  onSelect={setDateRange}
                  locale={de}
                  className="border border-gray-300 rounded-md p-3"
                  disabled={{ before: new Date() }}
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
