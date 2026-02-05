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

/**
 * PDF-Formulare für verschiedene Abwesenheitsgründe
 */
export interface PDFFormInfo {
  type: string;
  label: string;
}

export const PDF_FORMS: Record<AbsenceReason, PDFFormInfo[]> = {
  excursion: [
    {
      type: 'excursion_form',
      label: 'Antrag auf außerunterrichtliche Veranstaltung'
    }
  ],
  training: [
    {
      type: 'business_trip_form',
      label: 'Dienstreiseantrag'
    }
  ],
  exam: [
    {
      type: 'business_trip_form',
      label: 'Dienstreiseantrag'
    }
  ],
  official: [
    {
      type: 'business_trip_form',
      label: 'Dienstreiseantrag'
    }
  ],
  other: [
    {
      type: 'business_trip_form',
      label: 'Dienstreiseantrag'
    }
  ],
  personal: [],
  sick: [],
  undefined: []
};

/**
 * Gibt verfügbare PDF-Formulare für einen Abwesenheitsgrund zurück
 */
export function getAvailableFormsForReason(reason: AbsenceReason): PDFFormInfo[] {
  return PDF_FORMS[reason] || [];
}

/**
 * Info-Texte für bestimmte Abwesenheitsgründe
 */
export const INFO_TEXTS: Record<string, string> = {
  training: "Fortbildungen, die über LFB-online gestellt werden, werden automatisch genehmigt und können über Drive-BW abgerechnet werden."
};
