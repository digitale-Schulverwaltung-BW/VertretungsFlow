/**
 * AbsenceSuccessModal Component
 * Success modal shown after absence creation with PDF form download options
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import FormDownloadButton from './FormDownloadButton';
import { getAvailableFormsForReason, INFO_TEXTS } from '../constants';
import type { Absence } from '../types';
import '../styles/AbsenceSuccessModal.css';

interface AbsenceSuccessModalProps {
  absence: Absence;
  onClose: () => void;
}

const AbsenceSuccessModal: React.FC<AbsenceSuccessModalProps> = ({
  absence,
  onClose
}) => {
  const navigate = useNavigate();

  // Get available PDF forms for this absence reason
  const availableForms = getAvailableFormsForReason(absence.reason);

  // Get info text if applicable
  const infoText = INFO_TEXTS[absence.reason];

  const handleClose = () => {
    onClose();
    navigate('/');
  };

  // Handle click outside modal
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  return (
    <div className="absence-success-modal-backdrop" onClick={handleBackdropClick}>
      <div className="absence-success-modal">
        {/* Header */}
        <div className="modal-header">
          <div className="success-icon">✓</div>
          <h2>Abwesenheit erfolgreich eingereicht</h2>
        </div>

        {/* Content */}
        <div className="modal-content">
          <p className="success-message">
            Ihre Abwesenheitsmeldung wurde erfolgreich eingereicht.
          </p>
          <p className="absence-id">
            Abwesenheits-ID: <strong>#{absence.id}</strong>
          </p>

          {/* Info text for specific reasons */}
          {infoText && (
            <div className="info-box">
              <span className="info-icon">ℹ️</span>
              <p>{infoText}</p>
            </div>
          )}

          {/* PDF Forms */}
          {availableForms.length > 0 && (
            <div className="pdf-forms-section">
              <h3>Formulare zum Download</h3>
              <p className="section-description">
                Laden Sie bei Bedarf die vorausgefüllten Formulare herunter und reichen Sie diese ggf. ein.
              </p>
              <div className="form-buttons">
                {availableForms.map((form) => (
                  <FormDownloadButton
                    key={form.type}
                    absenceId={absence.id}
                    formType={form.type}
                    label={form.label}
                  />
                ))}
              </div>
            </div>
          )}

          {availableForms.length === 0 && (
            <div className="no-forms-message">
              <p>Für diesen Abwesenheitsgrund sind keine Formulare verfügbar.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button className="btn-primary" onClick={handleClose}>
            Zur Übersicht
          </button>
        </div>
      </div>
    </div>
  );
};

export default AbsenceSuccessModal;
