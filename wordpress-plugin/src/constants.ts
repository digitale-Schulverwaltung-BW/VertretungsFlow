import type { AbsenceReason } from './types';

export const ABSENCE_REASONS: Array<{ value: AbsenceReason; label: string }> = [
  { value: 'undefined', label: 'bitte wählen...' },
  { value: 'training', label: 'Fortbildung' },
  { value: 'exam', label: 'Prüfung' },
  { value: 'excursion', label: 'Exkursion' },
  { value: 'sick', label: 'Krank' },
  { value: 'personal', label: 'Privat' },
  { value: 'official', label: 'Dienstlich' },
  { value: 'other', label: 'Sonstiges' },
];

/**
 * Konvertiert einen AbsenceReason-Value in das entsprechende Label
 */
export const getAbsenceReasonLabel = (reason: string): string => {
  const found = ABSENCE_REASONS.find(r => r.value === reason);
  return found ? found.label : reason;
};
