/**
 * Generation Store - Manages generation state and parameters
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  GenerationMode,
  GenerationParameters,
  OutputFormat,
} from '../types';

interface GenerationState {
  // Current generation input
  sourceImage: File | null;
  sourceImagePreview: string | null;
  prompt: string;
  assetName: string;

  // Parameters
  parameters: GenerationParameters;

  // UI state
  isGenerating: boolean;
  currentJobId: string | null;

  // Actions
  setSourceImage: (file: File | null) => void;
  setPrompt: (prompt: string) => void;
  setAssetName: (name: string) => void;
  setParameter: <K extends keyof GenerationParameters>(
    key: K,
    value: GenerationParameters[K]
  ) => void;
  setParameters: (params: Partial<GenerationParameters>) => void;
  resetParameters: () => void;
  setIsGenerating: (isGenerating: boolean) => void;
  setCurrentJobId: (jobId: string | null) => void;
  reset: () => void;

  // Presets
  applyPreset: (preset: 'fast' | 'standard' | 'quality') => void;
}

const defaultParameters: GenerationParameters = {
  inferenceSteps: 30,
  guidanceScale: 5.5,
  octreeResolution: 256,
  generateTexture: true,
  outputFormat: 'glb',
  mode: 'standard',
};

const presets: Record<string, Partial<GenerationParameters>> = {
  fast: {
    inferenceSteps: 15,
    guidanceScale: 4.0,
    octreeResolution: 128,
    generateTexture: true,
    mode: 'fast' as GenerationMode,
  },
  standard: {
    inferenceSteps: 30,
    guidanceScale: 5.5,
    octreeResolution: 256,
    generateTexture: true,
    mode: 'standard' as GenerationMode,
  },
  quality: {
    inferenceSteps: 50,
    guidanceScale: 7.0,
    octreeResolution: 384,  // 384 instead of 512 for VRAM safety
    generateTexture: true,
    mode: 'quality' as GenerationMode,
  },
};

export const useGenerationStore = create<GenerationState>()(
  persist(
    (set, get) => ({
      // Initial state
      sourceImage: null,
      sourceImagePreview: null,
      prompt: '',
      assetName: '',
      parameters: { ...defaultParameters },
      isGenerating: false,
      currentJobId: null,

      // Actions
      setSourceImage: (file) => {
        // Revoke previous preview URL
        const prevPreview = get().sourceImagePreview;
        if (prevPreview) {
          URL.revokeObjectURL(prevPreview);
        }

        if (file) {
          const preview = URL.createObjectURL(file);
          const name = file.name.replace(/\.[^/.]+$/, '');
          set({
            sourceImage: file,
            sourceImagePreview: preview,
            assetName: get().assetName || name,
          });
        } else {
          set({
            sourceImage: null,
            sourceImagePreview: null,
          });
        }
      },

      setPrompt: (prompt) => set({ prompt }),

      setAssetName: (name) => set({ assetName: name }),

      setParameter: (key, value) =>
        set((state) => ({
          parameters: { ...state.parameters, [key]: value },
        })),

      setParameters: (params) =>
        set((state) => ({
          parameters: { ...state.parameters, ...params },
        })),

      resetParameters: () => set({ parameters: { ...defaultParameters } }),

      setIsGenerating: (isGenerating) => set({ isGenerating }),

      setCurrentJobId: (jobId) => set({ currentJobId: jobId }),

      reset: () => {
        const prevPreview = get().sourceImagePreview;
        if (prevPreview) {
          URL.revokeObjectURL(prevPreview);
        }
        set({
          sourceImage: null,
          sourceImagePreview: null,
          prompt: '',
          assetName: '',
          parameters: { ...defaultParameters },
          isGenerating: false,
          currentJobId: null,
        });
      },

      applyPreset: (preset) => {
        const presetParams = presets[preset];
        if (presetParams) {
          set((state) => ({
            parameters: { ...state.parameters, ...presetParams },
          }));
        }
      },
    }),
    {
      name: 'sweedle-generation',
      partialize: (state) => ({
        parameters: state.parameters,
      }),
    }
  )
);
