import type { Component } from 'vue';

export interface StepItem {
  description?: string;
  disabled?: boolean;
  icon?: Component | string;
  image?: string;
  title: string;
  videoUrl?: string;
}

export interface StepWizardExposes {
  getCurrentStep: () => number;
  nextStep: () => void;
  prevStep: () => void;
  setStep: (index: number) => void;
}
