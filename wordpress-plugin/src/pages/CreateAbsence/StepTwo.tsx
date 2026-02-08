import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';
import api from '../../api/client';
import type { Lesson, Absence } from '../../types';
import type { StepOneData } from './StepOne';

interface StepTwoProps {
  stepOneData: StepOneData;
  onBack: () => void;
  onSubmit: (absence: Absence) => void;
}

interface LessonWithMeta extends Lesson {
  can_be_canceled: boolean;
  notes: string;
}

const StepTwo: React.FC<StepTwoProps> = ({ stepOneData, onBack, onSubmit }) => {
  const [lessons, setLessons] = useState<LessonWithMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingProgress, setLoadingProgress] = useState<string>('Verbinde mit WebUntis...');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [allCanceled, setAllCanceled] = useState(false);
  const [adminNotes, setAdminNotes] = useState<string>('');
  const [attachments, setAttachments] = useState<File[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    fetchLessons();
  }, []);

  const fetchLessons = async () => {
    try {
      setLoading(true);
      setError(null);

      // Calculate estimated items to process
      const daysDiff = Math.ceil(
        (stepOneData.endDate.getTime() - stepOneData.startDate.getTime()) / (1000 * 60 * 60 * 24)
      ) + 1;
      const periodsPerDay = stepOneData.endLesson - stepOneData.startLesson + 1;
      const estimatedItems = daysDiff * periodsPerDay;

      // Progress phases
      setLoadingProgress('Verbinde mit WebUntis...');
      await new Promise((resolve) => setTimeout(resolve, 300));

      setLoadingProgress(`Lade Stundenplan für ${daysDiff} Tag${daysDiff > 1 ? 'e' : ''}...`);
      await new Promise((resolve) => setTimeout(resolve, 400));

      setLoadingProgress(`Verarbeite ca. ${estimatedItems} Stunden...`);

      const response = await api.fetchLessons({
        start_date: format(stepOneData.startDate, 'yyyy-MM-dd'),
        end_date: format(stepOneData.endDate, 'yyyy-MM-dd'),
        start_period: stepOneData.startLesson,
        end_period: stepOneData.endLesson,
      });

      setLoadingProgress(`${response.length} Stunden gefunden, bereite Anzeige vor...`);
      await new Promise((resolve) => setTimeout(resolve, 300));

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

  const handleSelectAllCanceled = (checked: boolean) => {
    setAllCanceled(checked);
    const newLessons = lessons.map(lesson => ({
      ...lesson,
      can_be_canceled: checked
    }));
    setLessons(newLessons);
  };

  const handleCopyToAll = (sourceIndex: number) => {
    const sourceNotes = lessons[sourceIndex].notes;
    const newLessons = lessons.map(lesson => ({
      ...lesson,
      notes: sourceNotes
    }));
    setLessons(newLessons);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('File input changed:', e.target.files);
    setUploadError(null);

    if (!e.target.files) return;

    const files = Array.from(e.target.files);

    if (files.length + attachments.length > 5) {
      setUploadError('Maximal 5 Dateien erlaubt');
      return;
    }

    const maxSize = 10 * 1024 * 1024;
    const oversized = files.filter(f => f.size > maxSize);
    if (oversized.length > 0) {
      setUploadError(`Datei(en) zu groß (max 10 MB): ${oversized.map(f => f.name).join(', ')}`);
      return;
    }

    const allowedTypes = ['application/pdf', 'image/jpeg', 'image/png', 'image/gif',
                          'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                          'text/plain'];

    const invalidTypes = files.filter(f => !allowedTypes.includes(f.type));
    if (invalidTypes.length > 0) {
      setUploadError(`Ungültige Dateitypen: ${invalidTypes.map(f => f.name).join(', ')}`);
      return;
    }

    console.log('Adding files to attachments:', files);
    const newAttachments = [...attachments, ...files];
    console.log('New attachments array:', newAttachments);
    setAttachments(newAttachments);
  };

  const removeAttachment = (index: number) => {
    setAttachments(attachments.filter((_, i) => i !== index));
  };

  const formatPeriod = (lesson: LessonWithMeta): string => {
    if (lesson.end_period && lesson.end_period !== lesson.period) {
      return `${lesson.period}-${lesson.end_period}`;
    }
    return `${lesson.period}`;
  };

  const handleSubmit = async () => {
    try {
      setSubmitting(true);
      setError(null);

      // Validierung: Jede Stunde muss entweder "kann entfallen" oder Hinweise haben
      const invalidLessons = lessons.filter(
        lesson => !lesson.can_be_canceled && (!lesson.notes || lesson.notes.trim() === '')
      );

      if (invalidLessons.length > 0) {
        setError(
          `Bitte geben Sie für jede Stunde entweder "kann entfallen" an oder fügen Sie einen Vertretungs-Hinweis hinzu. ${invalidLessons.length} Stunde(n) ${invalidLessons.length === 1 ? 'fehlt' : 'fehlen'} noch.`
        );
        setSubmitting(false);
        return;
      }

      const createdAbsence = await api.createAbsence({
        reason: stepOneData.reason,
        start_date: format(stepOneData.startDate, 'yyyy-MM-dd'),
        end_date: format(stepOneData.endDate, 'yyyy-MM-dd'),
        start_period: stepOneData.startLesson,
        end_period: stepOneData.endLesson,
        excursion_classes: stepOneData.excursionClasses,
        personal_reason: stepOneData.personalReason,
        admin_notes: adminNotes || undefined,
        affected_lessons: lessons.map((lesson) => ({
          date: lesson.date,
          period: lesson.period,
          end_period: lesson.end_period,
          subject: lesson.subject,
          class_name: lesson.class_name,
          room: lesson.room,
          can_be_canceled: lesson.can_be_canceled,
          notes: lesson.notes || undefined,
        })),
      });

      console.log('Created absence:', createdAbsence);
      console.log('Attachments to upload:', attachments);

      // Attachments hochladen
      if (attachments.length > 0 && createdAbsence.id) {
        console.log('Starting upload for absence ID:', createdAbsence.id);
        for (const file of attachments) {
          try {
            await api.uploadAttachment(createdAbsence.id, file);
          } catch (uploadErr) {
            console.error('Upload error:', uploadErr);
            setError('Abwesenheit erstellt, aber Upload-Fehler bei: ' + file.name);
          }
        }
      }

      onSubmit(createdAbsence);
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

  const showCanBeCanceledColumn = stepOneData.reason !== 'personal';

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-8">
          Abwesenheit vom {dateTitle}
        </h1>

        {error && (
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
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
            <span className="ml-3 text-gray-700">{loadingProgress}</span>
          </div>
        ) : lessons.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-600 mb-2">Keine Stunden gefunden für den gewählten Zeitraum.</p>
            <p className="text-sm text-gray-500 mb-6">
              Sie können die Abwesenheit trotzdem speichern, um für Vertretungen nicht eingeteilt zu werden.
            </p>
            <div className="flex justify-center gap-4">
              <button
                onClick={onBack}
                className="px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Zurück
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="px-6 py-2 bg-black text-white rounded-md hover:bg-gray-800 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {submitting ? 'Wird gespeichert...' : 'Trotzdem speichern'}
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Bemerkungen */}
            <div className="mb-6">
              <label
                htmlFor="adminNotes"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Bemerkungen für Schulleitung/Vertretungsplaner (optional)
              </label>
              <textarea
                id="adminNotes"
                value={adminNotes}
                onChange={(e) => setAdminNotes(e.target.value)}
                rows={3}
                placeholder="z.B. Hinweise zur Vertretungsplanung..."
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* File Upload */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Anhänge (optional, max 5 Dateien, je max 10 MB)
              </label>

              <input
                type="file"
                multiple
                onChange={handleFileChange}
                className="hidden"
                id="fileUpload"
                accept=".pdf,.jpg,.jpeg,.png,.gif,.doc,.docx,.txt"
              />

              <label
                htmlFor="fileUpload"
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md cursor-pointer hover:bg-gray-50"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Dateien hinzufügen
              </label>

              {uploadError && <p className="mt-2 text-sm text-red-600">{uploadError}</p>}

              {attachments.length > 0 && (
                <ul className="mt-3 space-y-2">
                  {attachments.map((file, index) => (
                    <li key={index} className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded-md">
                      <span className="text-sm text-gray-700">
                        {file.name} ({(file.size / 1024).toFixed(1)} KB)
                      </span>
                      <button
                        type="button"
                        onClick={() => removeAttachment(index)}
                        className="text-red-600 hover:text-red-800"
                      >
                        ✕
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

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
                    {showCanBeCanceledColumn && (
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={allCanceled}
                            onChange={(e) => handleSelectAllCanceled(e.target.checked)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            title="Alle auswählen/abwählen"
                          />
                          <span>Kann entfallen</span>
                        </div>
                      </th>
                    )}
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
                        {formatPeriod(lesson)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {lesson.class_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {lesson.subject}
                      </td>
                      {showCanBeCanceledColumn && (
                        <td className="px-6 py-4 whitespace-nowrap">
                          <input
                            type="checkbox"
                            checked={lesson.can_be_canceled}
                            onChange={(e) => handleCheckboxChange(index, e.target.checked)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                        </td>
                      )}
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={lesson.notes}
                            onChange={(e) => handleNotesChange(index, e.target.value)}
                            placeholder="z.B. Projektbearbeitung"
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          />
                          {index === 0 && lessons.length > 1 && (
                            <button
                              type="button"
                              onClick={() => handleCopyToAll(0)}
                              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                              title="Für alle übernehmen"
                            >
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                className="h-5 w-5"
                                viewBox="0 0 20 20"
                                fill="currentColor"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                                  clipRule="evenodd"
                                />
                              </svg>
                            </button>
                          )}
                        </div>
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
