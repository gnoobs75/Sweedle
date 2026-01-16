/**
 * Settings Store - User preferences and settings
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  // Tutorial Mode
  tutorialMode: boolean;
  dismissedTutorials: string[]; // Track which tutorials user has dismissed

  // Display preferences
  showTerminologyTooltips: boolean;
  autoPlayAnimations: boolean;

  // Quality defaults
  defaultQualityPreset: 'fast' | 'standard' | 'quality';

  // Actions
  setTutorialMode: (enabled: boolean) => void;
  toggleTutorialMode: () => void;
  dismissTutorial: (stageId: string) => void;
  resetDismissedTutorials: () => void;
  setShowTerminologyTooltips: (show: boolean) => void;
  setAutoPlayAnimations: (autoPlay: boolean) => void;
  setDefaultQualityPreset: (preset: 'fast' | 'standard' | 'quality') => void;
  resetSettings: () => void;
}

const defaultSettings = {
  tutorialMode: true, // On by default for new users
  dismissedTutorials: [],
  showTerminologyTooltips: true,
  autoPlayAnimations: true,
  defaultQualityPreset: 'standard' as const,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ...defaultSettings,

      setTutorialMode: (enabled) => set({ tutorialMode: enabled }),

      toggleTutorialMode: () =>
        set((state) => ({ tutorialMode: !state.tutorialMode })),

      dismissTutorial: (stageId) =>
        set((state) => ({
          dismissedTutorials: state.dismissedTutorials.includes(stageId)
            ? state.dismissedTutorials
            : [...state.dismissedTutorials, stageId],
        })),

      resetDismissedTutorials: () => set({ dismissedTutorials: [] }),

      setShowTerminologyTooltips: (show) =>
        set({ showTerminologyTooltips: show }),

      setAutoPlayAnimations: (autoPlay) =>
        set({ autoPlayAnimations: autoPlay }),

      setDefaultQualityPreset: (preset) =>
        set({ defaultQualityPreset: preset }),

      resetSettings: () => set(defaultSettings),
    }),
    {
      name: 'sweedle-settings',
    }
  )
);
