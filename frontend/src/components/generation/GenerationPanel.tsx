/**
 * GenerationPanel Component - Mode-aware generation panel
 */

import { useUIStore } from '../../stores/uiStore';
import { SimpleModePanel } from './SimpleModePanel';
import { AdvancedModePanel } from './AdvancedModePanel';

export function GenerationPanel() {
  const { mode } = useUIStore();

  if (mode === 'advanced') {
    return <AdvancedModePanel />;
  }

  return <SimpleModePanel />;
}
