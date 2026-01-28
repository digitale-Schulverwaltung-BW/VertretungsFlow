import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';
import api from '../../api/client';
import type { Lesson } from '../../types';
import type { StepOneData } from './StepOne';

interface StepTwoProps {
  stepOneData: StepOneData;
  onBack: () => void;
  onSubmit: () => void;
}

interface LessonWithMeta extends Lesson {
  can_be_canceled: boolean;
  notes: string;
}

const StepTwo: React.FC<StepTwoProps> = ({ stepOneData, onBack, onSubmit }) => {
  const [lessons, setLessons] = useState<LessonWithMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchLessons();
  }, []);

  const fetchLessons = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.fetchLessons({
        start_date: format(stepOneData.startDate, 'yyyy-MM-dd'),
        end_date: format(stepOneData.endDate, 'yyyy-MM-dd'),
        start_period: stepOneData.startLesson,
        end_period: stepOneData.endLesson,
      });

      // Add metadata for cancellation and notes
      const lessonsWithMeta: LessonWithMeta[] = response.map((lesson) => ({
        ...lesson,
        can_be_canceled: false,
        notes: '',
      }));

      setLessons(lessonsWithMeta);
    } catch (err) {
      console.error('Fehler beim Laden der Stunden:', err);
      setError('Stunden konnten nicht geladen werden. Bitte versuchen Sie es erneut.');
    } finally {
      setLoading(false);
    }
  };

  const handleCheckboxChange = (index: number, checked: boolean) => {
    const newLessons = [...lessons];
    newLessons[index].can_be_canceled = checked;
    setLessons(newLessons);
  };

  const handleNotesChange = (index: number, notes: string) => {
    const newLessons = [...lessons];
    newLessons[index].notes = notes;
    setLessons(newLessons);
  };

  const handleSubmit = async () => {
    try {
      setSubmitting(true);
      setError(null);

      await api.createAbsence({
        reason: stepOneData.reason,
        start_date: format(stepOneData.startDate, 'yyyy-MM-dd'),
        end_date: format(stepOneData.endDate, 'yyyy-MM-dd'),
        start_period: stepOneData.startLesson,
        end_period: stepOneData.endLesson,
        affected_lessons: lessons.map((lesson) => ({
          date: lesson.date,
          period: lesson.period,
          subject: lesson.subject,
          class_name: lesson.class_name,
          room: lesson.room,
          can_be_canceled: lesson.can_be_canceled,
          notes: lesson.notes || undefined,
        })),
      });

      onSubmit();
    } catch (err) {
      console.error('Fehler beim Erstellen der Abwesenheit:', err);
      setError('Abwesenheit konnte nicht erstellt werden. Bitte versuchen Sie es erneut.');
    } finally {
      setSubmitting(false);
    }
  };

  const dateTitle = `${format(stepOneData.startDate, 'd.M.yyyy', { locale: de })}-${format(
    stepOneData.endDate,
    'd.M.yyyy',
    { locale: de }
  )}`;

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-8">
          Abwesenheit vom {dateTitle}
        </h1>

        {error && (
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
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
            <span className="ml-3 text-gray-700">Lade Stunden...</span>
          </div>
        ) : lessons.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-600">Keine Stunden gefunden für den gewählten Zeitraum.</p>
            <button
              onClick={onBack}
              className="mt-4 px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Zurück
            </button>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Datum
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Stunde
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Klasse
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Fach
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Kann entfallen
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Vertretungsvorschlag
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {lessons.map((lesson, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {format(new Date(lesson.date), 'dd.MM.yyyy', { locale: de })}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {lesson.period}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {lesson.class_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {lesson.subject}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <input
                          type="checkbox"
                          checked={lesson.can_be_canceled}
                          onChange={(e) => handleCheckboxChange(index, e.target.checked)}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                        />
                      </td>
                      <td className="px-6 py-4">
                        <input
                          type="text"
                          value={lesson.notes}
                          onChange={(e) => handleNotesChange(index, e.target.value)}
                          placeholder="z.B. Projektbearbeitung"
                          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex justify-between items-center pt-6 mt-6 border-t border-gray-200">
              <button
                onClick={onBack}
                disabled={submitting}
                className="px-6 py-3 border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
              >
                Zurück
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="px-8 py-3 bg-black text-white rounded-md hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 disabled:opacity-50"
              >
                {submitting ? 'Wird übermittelt...' : 'Übermitteln'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default StepTwo;
