/**
 * UI Store - Manages UI state and preferences
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Panel, PanelLayout, UIMode } from '../types';

interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  timestamp: number;
}

interface UIState {
  // Mode
  mode: UIMode;

  // Panel visibility and layout
  activePanels: Panel[];
  panelLayout: PanelLayout;

  // Sidebar
  sidebarCollapsed: boolean;
  sidebarWidth: number;

  // Notifications
  notifications: Notification[];

  // Modal state
  activeModal: string | null;
  modalData: Record<string, unknown>;

  // Connection status
  isConnected: boolean;
  connectionError: string | null;

  // Loading states
  globalLoading: boolean;
  loadingMessage: string | null;

  // Actions
  setMode: (mode: UIMode) => void;
  toggleMode: () => void;

  // Panel actions
  showPanel: (panel: Panel) => void;
  hidePanel: (panel: Panel) => void;
  togglePanel: (panel: Panel) => void;
  setPanelLayout: (layout: Partial<PanelLayout>) => void;
  resetPanelLayout: () => void;

  // Sidebar actions
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  setSidebarWidth: (width: number) => void;

  // Notification actions
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;

  // Modal actions
  openModal: (modalId: string, data?: Record<string, unknown>) => void;
  closeModal: () => void;

  // Connection actions
  setConnected: (connected: boolean) => void;
  setConnectionError: (error: string | null) => void;

  // Loading actions
  setGlobalLoading: (loading: boolean, message?: string) => void;
}

const defaultPanelLayout: PanelLayout = {
  left: 320,
  center: 0, // Flexible
  right: 320,
};

const defaultActivePanels: Panel[] = ['generation', 'viewer', 'library'];

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      // Initial state
      mode: 'simple',
      activePanels: [...defaultActivePanels],
      panelLayout: { ...defaultPanelLayout },
      sidebarCollapsed: false,
      sidebarWidth: 280,
      notifications: [],
      activeModal: null,
      modalData: {},
      isConnected: false,
      connectionError: null,
      globalLoading: false,
      loadingMessage: null,

      // Mode actions
      setMode: (mode) => set({ mode }),

      toggleMode: () =>
        set((state) => ({
          mode: state.mode === 'simple' ? 'advanced' : 'simple',
        })),

      // Panel actions
      showPanel: (panel) =>
        set((state) => {
          if (state.activePanels.includes(panel)) return state;
          return { activePanels: [...state.activePanels, panel] };
        }),

      hidePanel: (panel) =>
        set((state) => ({
          activePanels: state.activePanels.filter((p) => p !== panel),
        })),

      togglePanel: (panel) =>
        set((state) => {
          if (state.activePanels.includes(panel)) {
            return { activePanels: state.activePanels.filter((p) => p !== panel) };
          }
          return { activePanels: [...state.activePanels, panel] };
        }),

      setPanelLayout: (layout) =>
        set((state) => ({
          panelLayout: { ...state.panelLayout, ...layout },
        })),

      resetPanelLayout: () =>
        set({
          panelLayout: { ...defaultPanelLayout },
          activePanels: [...defaultActivePanels],
        }),

      // Sidebar actions
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

      toggleSidebar: () =>
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      setSidebarWidth: (width) =>
        set({ sidebarWidth: Math.max(200, Math.min(400, width)) }),

      // Notification actions
      addNotification: (notification) => {
        const id = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const newNotification: Notification = {
          ...notification,
          id,
          timestamp: Date.now(),
        };

        set((state) => ({
          notifications: [...state.notifications, newNotification],
        }));

        // Auto-remove after duration
        const duration = notification.duration ?? 5000;
        if (duration > 0) {
          setTimeout(() => {
            get().removeNotification(id);
          }, duration);
        }
      },

      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),

      clearNotifications: () => set({ notifications: [] }),

      // Modal actions
      openModal: (modalId, data = {}) =>
        set({
          activeModal: modalId,
          modalData: data,
        }),

      closeModal: () =>
        set({
          activeModal: null,
          modalData: {},
        }),

      // Connection actions
      setConnected: (connected) =>
        set({
          isConnected: connected,
          connectionError: connected ? null : get().connectionError,
        }),

      setConnectionError: (error) =>
        set({
          connectionError: error,
          isConnected: error ? false : get().isConnected,
        }),

      // Loading actions
      setGlobalLoading: (loading, message = undefined) =>
        set({
          globalLoading: loading,
          loadingMessage: loading ? message : undefined,
        }),
    }),
    {
      name: 'sweedle-ui',
      partialize: (state) => ({
        mode: state.mode,
        panelLayout: state.panelLayout,
        sidebarCollapsed: state.sidebarCollapsed,
        sidebarWidth: state.sidebarWidth,
      }),
    }
  )
);
