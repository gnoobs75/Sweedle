/**
 * Workflow API service
 */

import { apiClient } from './client';
import type { BackendWorkflowStage } from '../../types';

interface WorkflowStatusResponse {
  asset_id: string;
  workflow_stage: BackendWorkflowStage;
  has_mesh: boolean;
  has_texture: boolean;
  is_rigged: boolean;
  mesh_path?: string;
  textured_path?: string;
  rigged_mesh_path?: string;
}

interface AdvanceStageResponse {
  success: boolean;
  message: string;
  asset_id: string;
  new_stage: BackendWorkflowStage;
}

interface ApproveStageResponse {
  success: boolean;
  message: string;
  asset_id: string;
  approved_stage: BackendWorkflowStage;
  next_stage?: BackendWorkflowStage;
}

interface SkipToExportResponse {
  success: boolean;
  message: string;
  asset_id: string;
  skipped_stages: BackendWorkflowStage[];
}

/**
 * Get the workflow status for an asset
 */
export async function getWorkflowStatus(assetId: string): Promise<WorkflowStatusResponse> {
  return apiClient.get<WorkflowStatusResponse>(`/workflow/${assetId}/status`);
}

/**
 * Advance an asset to a specific workflow stage
 */
export async function advanceWorkflowStage(
  assetId: string,
  toStage: BackendWorkflowStage
): Promise<AdvanceStageResponse> {
  return apiClient.post<AdvanceStageResponse>(`/workflow/${assetId}/advance`, {
    to_stage: toStage,
  });
}

/**
 * Approve the current workflow stage
 */
export async function approveWorkflowStage(assetId: string): Promise<ApproveStageResponse> {
  return apiClient.post<ApproveStageResponse>(`/workflow/${assetId}/approve`);
}

/**
 * Skip remaining stages and go to export
 */
export async function skipToExport(assetId: string): Promise<SkipToExportResponse> {
  return apiClient.post<SkipToExportResponse>(`/workflow/${assetId}/skip-to-export`);
}
