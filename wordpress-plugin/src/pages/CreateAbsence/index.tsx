import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import StepOne, { StepOneData } from './StepOne';
import StepTwo from './StepTwo';

const CreateAbsence: React.FC = () => {
  const [step, setStep] = useState<1 | 2>(1);
  const [stepOneData, setStepOneData] = useState<StepOneData | null>(null);
  const navigate = useNavigate();

  const handleStepOneComplete = (data: StepOneData) => {
    setStepOneData(data);
    setStep(2);
  };

  const handleBack = () => {
    setStep(1);
  };

  const handleSubmitComplete = () => {
    // Navigate to dashboard or absence list after successful submission
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
    </>
  );
};

export default CreateAbsence;
