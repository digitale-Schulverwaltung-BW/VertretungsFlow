import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';
import api from '../../api/client';
import type { Absence, User } from '../../types';
import { getAbsenceReasonLabel } from '../../constants';

interface NavEntry {
  id: number;
  status: string;
}

const MAX_FEEDBACK_LENGTH = 2000;

// Unerledigt = noch Handlungsbedarf für die Vertretungsplanung
const isOpen = (status: string) => status === 'submitted' || status === 'approved';

const AbsenceDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [absence, setAbsence] = useState<Absence | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [allAbsences, setAllAbsences] = useState<NavEntry[]>([]);
  const [feedback, setFeedback] = useState('');
  const [currentIndex, setCurrentIndex] = useState<number>(-1);

  useEffect(() => {
    const loadData = async () => {
      if (!id) {
        setError('Keine Abwesenheits-ID angegeben');
        setLoading(false);
        return;
      }

      try {
        const [absenceData, userData, allAbsences] = await Promise.all([
          api.getAbsence(parseInt(id)),
          api.getCurrentUser(),
          api.getAbsences() // Load all absences for navigation
        ]);
        setAbsence(absenceData);
        setUser(userData);

        // Extract IDs and find current index
        const entries = allAbsences.map(a => ({ id: a.id!, status: a.status }));
        setAllAbsences(entries);
        setCurrentIndex(entries.findIndex(e => e.id === parseInt(id)));
        setFeedback('');
      } catch (err: any) {
        setError(err.message || 'Fehler beim Laden der Abwesenheit');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id]);

  // Status des aktuellen Eintrags in der Navigationsliste aktuell halten
  const updateNavStatus = (status: string) => {
    setAllAbsences(prev => prev.map((e, i) => (i === currentIndex ? { ...e, status } : e)));
  };

  const handleApprove = async (approved: boolean) => {
    if (!absence || !id) return;

    setActionLoading(true);
    try {
      // Rückmeldung wird nur bei Ablehnung per E-Mail mitgeschickt
      await api.approveAbsence(parseInt(id), approved, approved ? undefined : feedback.trim() || undefined);
      // Reload absence data
      const updated = await api.getAbsence(parseInt(id));
      setAbsence(updated);
      updateNavStatus(updated.status);
      setFeedback('');
    } catch (err: any) {
      alert(err.message || 'Fehler beim Genehmigen der Abwesenheit');
    } finally {
      setActionLoading(false);
    }
  };

  const handleComplete = async () => {
    if (!absence || !id) return;

    setActionLoading(true);
    try {
      await api.completeAbsence(parseInt(id), feedback.trim() || undefined);
      // Reload absence data
      const updated = await api.getAbsence(parseInt(id));
      setAbsence(updated);
      updateNavStatus(updated.status);
      setFeedback('');
    } catch (err: any) {
      alert(err.message || 'Fehler beim Eintragen der Abwesenheit');
    } finally {
      setActionLoading(false);
    }
  };

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
      <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusStyles[status as keyof typeof statusStyles] || 'bg-gray-100 text-gray-800'}`}>
        {statusLabels[status as keyof typeof statusLabels] || status}
      </span>
    );
  };

  const formatPeriod = (period: number, endPeriod?: number): string => {
    if (endPeriod && endPeriod !== period) {
      return `${period}-${endPeriod}`;
    }
    return `${period}`;
  };

  // Check WordPress config for dept_heads_can_complete setting
  const config = window.absenzflowConfig;
  const deptHeadsCanComplete = config?.deptHeadsCanComplete || false;

  // Admin und Planner sehen immer alle Buttons, unabhängig vom Status
  const isAdminOrPlanner = user?.role === 'admin' || user?.role === 'planner';

  const canApprove = isAdminOrPlanner || user?.role === 'dept_head';
  const canComplete = isAdminOrPlanner || (user?.role === 'dept_head' && deptHeadsCanComplete);
  const canDelete = isAdminOrPlanner;

  const hasPrevious = currentIndex > 0;
  const hasNext = currentIndex >= 0 && currentIndex < allAbsences.length - 1;

  // Nächste/vorige unerledigte Absenz relativ zur aktuellen Position
  const nextOpenIndex = currentIndex < 0
    ? -1
    : allAbsences.findIndex((e, i) => i > currentIndex && isOpen(e.status));
  let previousOpenIndex = -1;
  for (let i = currentIndex - 1; i >= 0; i--) {
    if (isOpen(allAbsences[i].status)) {
      previousOpenIndex = i;
      break;
    }
  }
  const openCount = allAbsences.filter(e => isOpen(e.status)).length;

  const goToIndex = (index: number) => {
    if (index >= 0 && index < allAbsences.length) {
      navigate(`/absence/${allAbsences[index].id}`);
    }
  };

  const handlePrevious = () => hasPrevious && goToIndex(currentIndex - 1);
  const handleNext = () => hasNext && goToIndex(currentIndex + 1);

  const handleDelete = async () => {
    if (!absence || !id) return;

    if (!confirm('Möchten Sie diese Abwesenheit wirklich löschen? Diese Aktion kann nicht rückgängig gemacht werden.')) {
      return;
    }

    setActionLoading(true);
    try {
      await api.deleteAbsence(parseInt(id));
      // Navigate back to dashboard after successful deletion
      navigate('/');
    } catch (err: any) {
      alert(err.message || 'Fehler beim Löschen der Abwesenheit');
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Lädt Abwesenheit...</p>
        </div>
      </div>
    );
  }

  if (error || !absence) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">{error || 'Abwesenheit nicht gefunden'}</p>
        </div>
        <button
          onClick={() => navigate('/')}
          className="mt-4 px-4 py-2 text-white-600 hover:text-white-800"
        >
          ← Zurück zum Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate(-1)}
          className="text-white-600 hover:text-white-800 mb-4 flex items-center"
        >
          ← Zurück zum Dashboard
        </button>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-3xl font-bold text-gray-900">Abwesenheit Details</h1>
            {getStatusBadge(absence.status)}
          </div>

          {/* Navigation Buttons */}
          {allAbsences.length > 1 && (
            <div className="flex items-center space-x-2">
              {isAdminOrPlanner && (
                <button
                  onClick={() => goToIndex(previousOpenIndex)}
                  disabled={previousOpenIndex < 0}
                  className="px-3 py-2 border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed"
                  title={`Vorherige unerledigte Abwesenheit (${openCount} unerledigt)`}
                >
                  ⇤ Unerledigt
                </button>
              )}
              <button
                onClick={handlePrevious}
                disabled={!hasPrevious}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed flex items-center"
                title="Vorherige Abwesenheit"
              >
                ← Zurück
              </button>
              <span className="text-sm text-gray-500">
                {currentIndex + 1} / {allAbsences.length}
              </span>
              <button
                onClick={handleNext}
                disabled={!hasNext}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-30 disabled:cursor-not-allowed flex items-center"
                title="Nächste Abwesenheit"
              >
                Weiter →
              </button>
              {isAdminOrPlanner && (
                <button
                  onClick={() => goToIndex(nextOpenIndex)}
                  disabled={nextOpenIndex < 0}
                  className="px-3 py-2 border border-blue-300 text-blue-700 rounded-lg hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed"
                  title={`Nächste unerledigte Abwesenheit (${openCount} unerledigt)`}
                >
                  Unerledigt ⇥
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Info Card */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Lehrkraft */}
          <div>
            <h3 className="text-sm font-bold text-blue-600 mb-1">Lehrkraft</h3>
            <p className="text-lg text-gray-900">
              {absence.teacher.full_name || absence.teacher.username}
            </p>
          </div>

          {/* Zeitraum */}
          <div>
            <h3 className="text-sm font-bold text-blue-600 mb-1">Zeitraum</h3>
            <p className="text-lg text-gray-900">
              {format(new Date(absence.start_date), 'dd.MM.yyyy', { locale: de })} -{' '}
              {format(new Date(absence.end_date), 'dd.MM.yyyy', { locale: de })}
            </p>
            <p className="text-sm text-gray-600 mt-1">
              Stunde {absence.start_period} - {absence.end_period}
            </p>
          </div>

          {/* Grund */}
          <div className="md:col-span-2">
            <h3 className="text-sm font-bold text-blue-600 mb-1">Grund</h3>
            <p className="text-lg text-gray-900">{getAbsenceReasonLabel(absence.reason)}</p>
          </div>

          {/* Exkursion: Klassen */}
          {absence.excursion_classes && (
            <div>
              <h3 className="text-sm font-bold text-blue-600 mb-1">Klasse(n)</h3>
              <p className="text-lg text-gray-900">{absence.excursion_classes}</p>
            </div>
          )}

          {/* Zusatzinfos je nach Grund */}
          {absence.personal_reason && (
            <div>
              <h3 className="text-sm font-bold text-blue-600 mb-1">
                {absence.reason === 'official' ? 'Anlass der Reise'
                  : absence.reason === 'exam' ? 'Prüfung, z.B. IHK, HK usw.'
                  : absence.reason === 'training' ? 'Fortbildung Nr./Thema'
                  : 'Begründung'}
              </h3>
              <p className="text-lg text-gray-900">{absence.personal_reason}</p>
            </div>
          )}

          {/* Bemerkungen */}
          {absence.admin_notes && (
            <div className="md:col-span-2">
              <h3 className="text-sm font-bold text-blue-600 mb-1">Bemerkungen</h3>
              <p className="text-gray-900 whitespace-pre-wrap">{absence.admin_notes}</p>
            </div>
          )}

          {/* Erstellt am */}
          <div>
            <h3 className="text-sm font-bold text-blue-600 mb-1">Erstellt am</h3>
            <p className="text-gray-900">
              {format(new Date(absence.created_at), 'dd.MM.yyyy HH:mm', { locale: de })}
            </p>
          </div>

          {/* Genehmigt/Erledigt */}
          {absence.approved_at && (
            <div>
              <h3 className="text-sm font-bold text-blue-600 mb-1">Genehmigt am</h3>
              <p className="text-gray-900">
                {format(new Date(absence.approved_at), 'dd.MM.yyyy HH:mm', { locale: de })}
              </p>
            </div>
          )}

          {absence.completed_at && (
            <div>
              <h3 className="text-sm font-bold text-blue-600 mb-1">Erledigt am</h3>
              <p className="text-gray-900">
                {format(new Date(absence.completed_at), 'dd.MM.yyyy HH:mm', { locale: de })}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Betroffene Stunden */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Betroffene Stunden ({absence.affected_lessons?.length || 0})
        </h2>

        {absence.affected_lessons && absence.affected_lessons.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Datum</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stunde</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fach</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Klasse</th>
                  {absence.reason !== 'personal' && (
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Kann entfallen</th>
                  )}
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hinweise Lehrkraft</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {absence.affected_lessons.map((lesson) => (
                  <tr key={lesson.id}>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {format(new Date(lesson.date), 'dd.MM.yyyy', { locale: de })}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {formatPeriod(lesson.period, lesson.end_period)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {lesson.subject || '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {lesson.class_name || '-'}
                    </td>
                    {absence.reason !== 'personal' && (
                      <td className="px-4 py-3 whitespace-nowrap text-center">
                        {lesson.can_be_canceled ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                            ✓ Ja
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            - Nein
                          </span>
                        )}
                      </td>
                    )}
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {lesson.notes ? (
                        <div className="max-w-md">
                          {lesson.notes}
                        </div>
                      ) : (
                        <span className="text-gray-400">Keine Angaben</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-4">Keine betroffenen Stunden</p>
        )}
      </div>

      {/* Anhänge */}
      {absence.attachments && absence.attachments.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Anhänge ({absence.attachments.length})
          </h2>
          <ul className="space-y-2">
            {absence.attachments.map((attachment) => (
              <li key={attachment.id} className="flex items-center justify-between bg-gray-50 px-4 py-3 rounded-md">
                <div className="flex items-center space-x-3">
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{attachment.filename}</p>
                    <p className="text-xs text-gray-500">
                      {(attachment.file_size / 1024).toFixed(1)} KB • {format(new Date(attachment.uploaded_at), 'dd.MM.yyyy HH:mm', { locale: de })}
                    </p>
                  </div>
                </div>
                <a
                  href={api.getAttachmentDownloadUrl(absence.id!, attachment.id)}
                  download={attachment.filename}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Download
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Action Buttons */}
      {(canApprove || canComplete || canDelete) && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Aktionen</h2>

          {(canApprove || canComplete) && (
            <div className="mb-4">
              <label htmlFor="feedback" className="block text-sm font-bold text-blue-600 mb-1">
                Rückmeldung an die Lehrkraft (optional)
              </label>
              <textarea
                id="feedback"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                maxLength={MAX_FEEDBACK_LENGTH}
                rows={3}
                disabled={actionLoading}
                placeholder="Wird in der E-Mail an die Lehrkraft mitgeschickt – bei „Ablehnen“ und „Als erledigt markieren“."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                {feedback.length} / {MAX_FEEDBACK_LENGTH}
              </p>
            </div>
          )}

          <div className="flex flex-wrap gap-4">
            {canApprove && (
              <>
                <button
                  onClick={() => handleApprove(true)}
                  disabled={actionLoading || absence.status === 'approved' || absence.status === 'completed'}
                  className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {actionLoading ? 'Lädt...' : '✓ Genehmigen'}
                </button>
                <button
                  onClick={() => handleApprove(false)}
                  disabled={actionLoading || absence.status === 'rejected' || absence.status === 'completed'}
                  className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                >
                  {actionLoading ? 'Lädt...' : '✗ Ablehnen'}
                </button>
              </>
            )}

            {canComplete && (
              <button
                onClick={handleComplete}
                disabled={actionLoading || absence.status === 'completed'}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {actionLoading ? 'Lädt...' : '✓ Als erledigt markieren'}
              </button>
            )}

            {canDelete && (
              <button
                onClick={handleDelete}
                disabled={actionLoading}
                className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {actionLoading ? 'Lädt...' : '🗑 Löschen'}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AbsenceDetail;
