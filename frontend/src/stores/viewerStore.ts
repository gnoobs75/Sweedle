/**
 * Viewer Store - Manages 3D viewer state and settings
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ViewerSettings } from '../types';

interface ViewerState {
  // Current model
  currentModelUrl: string | null;
  currentAssetId: string | null;
  isLoading: boolean;
  loadError: string | null;

  // Model info
  modelInfo: {
    vertexCount?: number;
    faceCount?: number;
    materials?: string[];
    hasTextures?: boolean;
  };

  // Viewer settings
  settings: ViewerSettings;

  // Camera
  cameraPosition: [number, number, number];
  cameraTarget: [number, number, number];

  // LOD
  currentLodLevel: number;
  availableLodLevels: number[];

  // Actions
  loadModel: (url: string, assetId?: string) => void;
  clearModel: () => void;
  setLoading: (loading: boolean) => void;
  setLoadError: (error: string | null) => void;
  setModelInfo: (info: ViewerState['modelInfo']) => void;
  setSetting: <K extends keyof ViewerSettings>(key: K, value: ViewerSettings[K]) => void;
  setSettings: (settings: Partial<ViewerSettings>) => void;
  resetSettings: () => void;
  setCameraPosition: (position: [number, number, number]) => void;
  setCameraTarget: (target: [number, number, number]) => void;
  resetCamera: () => void;
  setLodLevel: (level: number) => void;
  setAvailableLodLevels: (levels: number[]) => void;
}

const defaultSettings: ViewerSettings = {
  showWireframe: false,
  showGrid: true,
  showAxes: false,
  autoRotate: false,
  backgroundColor: '#1a1a2e',
  environmentMap: 'studio',
  exposure: 1.0,
};

const defaultCameraPosition: [number, number, number] = [3, 3, 3];
const defaultCameraTarget: [number, number, number] = [0, 0, 0];

export const useViewerStore = create<ViewerState>()(
  persist(
    (set) => ({
      // Initial state
      currentModelUrl: null,
      currentAssetId: null,
      isLoading: false,
      loadError: null,
      modelInfo: {},
      settings: { ...defaultSettings },
      cameraPosition: defaultCameraPosition,
      cameraTarget: defaultCameraTarget,
      currentLodLevel: 0,
      availableLodLevels: [],

      // Actions
      loadModel: (url, assetId) =>
        set({
          currentModelUrl: url,
          currentAssetId: assetId || null,
          isLoading: true,
          loadError: null,
          modelInfo: {},
        }),

      clearModel: () =>
        set({
          currentModelUrl: null,
          currentAssetId: null,
          isLoading: false,
          loadError: null,
          modelInfo: {},
          currentLodLevel: 0,
          availableLodLevels: [],
        }),

      setLoading: (loading) => set({ isLoading: loading }),

      setLoadError: (error) => set({ loadError: error, isLoading: false }),

      setModelInfo: (info) => set({ modelInfo: info }),

      setSetting: (key, value) =>
        set((state) => ({
          settings: { ...state.settings, [key]: value },
        })),

      setSettings: (settings) =>
        set((state) => ({
          settings: { ...state.settings, ...settings },
        })),

      resetSettings: () => set({ settings: { ...defaultSettings } }),

      setCameraPosition: (position) => set({ cameraPosition: position }),

      setCameraTarget: (target) => set({ cameraTarget: target }),

      resetCamera: () =>
        set({
          cameraPosition: defaultCameraPosition,
          cameraTarget: defaultCameraTarget,
        }),

      setLodLevel: (level) => set({ currentLodLevel: level }),

      setAvailableLodLevels: (levels) => set({ availableLodLevels: levels }),
    }),
    {
      name: 'sweedle-viewer',
      partialize: (state) => ({
        settings: state.settings,
      }),
    }
  )
);
