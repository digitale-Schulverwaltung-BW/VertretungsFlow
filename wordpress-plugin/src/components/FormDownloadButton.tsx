/**
 * FormDownloadButton Component
 * Button to download pre-filled PDF forms for absences
 */
import React, { useState } from 'react';
import api from '../api/client';
import '../styles/FormDownloadButton.css';

interface FormDownloadButtonProps {
  absenceId: number;
  formType: string;
  label: string;
}

const FormDownloadButton: React.FC<FormDownloadButtonProps> = ({
  absenceId,
  formType,
  label
}) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDownload = async () => {
    setIsDownloading(true);
    setError(null);

    try {
      // Call API to download PDF blob
      const blob = await api.downloadPDFForm(absenceId, formType);

      // Generate filename
      const filename = `Antrag_Absenz_${absenceId}_${formType}.pdf`;

      // Create blob URL
      const url = window.URL.createObjectURL(blob);

      // Create temporary anchor element to trigger download
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      link.style.display = 'none';

      // Append to body, click, and remove
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      // Clean up blob URL
      window.URL.revokeObjectURL(url);

      console.log(`✅ Downloaded PDF form: ${filename}`);
    } catch (err: any) {
      console.error('❌ PDF download failed:', err);

      let errorMessage = 'Download fehlgeschlagen. Bitte versuchen Sie es erneut.';

      if (err.response) {
        // Backend returned an error
        if (err.response.status === 404) {
          errorMessage = 'Formular nicht gefunden.';
        } else if (err.response.status === 403) {
          errorMessage = 'Keine Berechtigung zum Download.';
        } else if (err.response.status === 400) {
          errorMessage = 'Formular nicht anwendbar für diesen Abwesenheitsgrund.';
        } else if (err.response.data && typeof err.response.data === 'object') {
          // Try to extract detail message from error response
          const detail = (err.response.data as any).detail;
          if (detail) {
            errorMessage = detail;
          }
        }
      } else if (err.message) {
        errorMessage = `Fehler: ${err.message}`;
      }

      setError(errorMessage);
      alert(errorMessage);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="form-download-button-container">
      <button
        className="form-download-button"
        onClick={handleDownload}
        disabled={isDownloading}
      >
        {isDownloading ? (
          <>
            <span className="spinner"></span>
            <span>Wird heruntergeladen...</span>
          </>
        ) : (
          <>
            <span className="download-icon">📄</span>
            <span>{label}</span>
          </>
        )}
      </button>
      {error && (
        <div className="form-download-error">
          {error}
        </div>
      )}
    </div>
  );
};

export default FormDownloadButton;
