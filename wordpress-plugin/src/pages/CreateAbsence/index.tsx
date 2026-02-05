import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import StepOne, { StepOneData } from './StepOne';
import StepTwo from './StepTwo';
import AbsenceSuccessModal from '../../components/AbsenceSuccessModal';
import type { Absence } from '../../types';

const CreateAbsence: React.FC = () => {
  const [step, setStep] = useState<1 | 2>(1);
  const [stepOneData, setStepOneData] = useState<StepOneData | null>(null);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [createdAbsence, setCreatedAbsence] = useState<Absence | null>(null);
  const navigate = useNavigate();

  const handleStepOneComplete = (data: StepOneData) => {
    setStepOneData(data);
    setStep(2);
  };

  const handleBack = () => {
    setStep(1);
  };

  const handleSubmitComplete = (absence: Absence) => {
    // Show success modal with PDF download options
    setCreatedAbsence(absence);
    setShowSuccessModal(true);
  };

  const handleModalClose = () => {
    setShowSuccessModal(false);
    navigate('/');
  };

  return (
    <>
      {step === 1 && <StepOne onNext={handleStepOneComplete} />}
      {step === 2 && stepOneData && (
        <StepTwo
          stepOneData={stepOneData}
          onBack={handleBack}
          onSubmit={handleSubmitComplete}
        />
      )}
      {showSuccessModal && createdAbsence && (
        <AbsenceSuccessModal
          absence={createdAbsence}
          onClose={handleModalClose}
        />
      )}
    </>
  );
};

export default CreateAbsence;
