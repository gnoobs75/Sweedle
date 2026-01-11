/**
 * WebSocket React Hook
 */

import { useEffect, useRef, useCallback } from 'react';
import { getWebSocketClient, WebSocketClient } from '../services/websocket/WebSocketClient';
import { useUIStore } from '../stores/uiStore';
import { useQueueStore } from '../stores/queueStore';
import { useLibraryStore } from '../stores/libraryStore';
import { useGenerationStore } from '../stores/generationStore';
import { useRiggingStore, type CharacterType } from '../stores/riggingStore';
import { useViewerStore } from '../stores/viewerStore';
import { useWorkflowStore } from '../stores/workflowStore';
import { getAsset, getAssetModelUrl } from '../services/api/assets';
import { getSkeleton } from '../services/api/rigging';
import { logger } from '../lib/logger';
import type { WSMessage, GenerationJob } from '../types';

export function useWebSocket() {
  const clientRef = useRef<WebSocketClient | null>(null);

  const { setConnected, setConnectionError, addNotification } = useUIStore();
  const { updateJobProgress, updateJobStatus, setQueueStatus, addJob } = useQueueStore();
  const { addAsset, updateAsset } = useLibraryStore();
  const { setIsGenerating, setCurrentJobId } = useGenerationStore();
  const { reloadModel, loadModel, currentAssetId } = useViewerStore();
  const {
    setProgress: setRiggingProgress,
    setDetectedType,
    setIsRigging,
    setStatus: setRiggingStatus,
    setError: setRiggingError,
    setSkeletonData,
  } = useRiggingStore();
  const {
    activeAssetId: workflowAssetId,
    currentStage: workflowCurrentStage,
    setProgress: setWorkflowProgress,
    setStageStatus,
    setPipelineStatus,
    setProcessing: setWorkflowProcessing,
  } = useWorkflowStore();

  // Message handler
  const handleMessage = useCallback(
    (message: WSMessage) => {
      logger.debug('WebSocket', `Received message: ${message.type}`, message);

      switch (message.type) {
        case 'progress': {
          logger.info('WebSocket', 'Job progress update', {
            jobId: message.job_id,
            progress: message.progress,
            stage: message.stage,
            status: message.status
          });

          updateJobProgress(message.job_id, message.progress, message.stage);

          // Update workflow store if this is the active workflow
          if (message.asset_id === workflowAssetId) {
            setWorkflowProgress(message.progress, message.stage || 'Processing...');
          }

          if (message.status === 'completed' || message.status === 'failed') {
            logger.info('WebSocket', `Job ${message.status}`, {
              jobId: message.job_id,
              error: message.error,
              assetId: message.asset_id,
            });

            updateJobStatus(message.job_id, message.status, message.error);
            setIsGenerating(false);

            if (message.status === 'completed') {
              // Reload model if it's the current one (for texture updates)
              if (message.asset_id && message.asset_id === currentAssetId) {
                logger.info('WebSocket', 'Reloading model after job completion', { assetId: message.asset_id });
                reloadModel();
              }

              // Update workflow store if this is the active workflow
              if (message.asset_id === workflowAssetId) {
                setWorkflowProcessing(false);
                // Update the current stage (mesh or texture depending on what's processing)
                const completedStage = workflowCurrentStage === 'texture' ? 'texture' : 'mesh';
                setStageStatus(completedStage, 'completed');
                setWorkflowProgress(1.0, 'Complete');

                // Load the generated model in the viewer automatically
                const modelUrl = getAssetModelUrl(message.asset_id);
                logger.info('WebSocket', 'Loading workflow model into viewer', {
                  assetId: message.asset_id,
                  modelUrl
                });
                loadModel(modelUrl, message.asset_id);
              }

              // Refresh asset data from API to get updated hasTexture, etc.
              if (message.asset_id) {
                getAsset(message.asset_id)
                  .then((updatedAsset) => {
                    logger.info('WebSocket', 'Refreshed asset after completion', {
                      assetId: updatedAsset.id,
                      hasTexture: updatedAsset.hasTexture
                    });
                    updateAsset(updatedAsset.id, updatedAsset);
                  })
                  .catch((err) => {
                    logger.error('WebSocket', 'Failed to refresh asset', err);
                  });
              }

              addNotification({
                type: 'success',
                title: 'Generation Complete',
                message: 'Your 3D model is ready!',
              });
            } else if (message.status === 'failed') {
              // Update workflow store if this is the active workflow
              if (message.asset_id === workflowAssetId) {
                setWorkflowProcessing(false);
                // Update the current stage (mesh or texture depending on what's processing)
                const failedStage = workflowCurrentStage === 'texture' ? 'texture' : 'mesh';
                setStageStatus(failedStage, 'failed', message.error);
              }

              addNotification({
                type: 'error',
                title: 'Generation Failed',
                message: message.error || 'An error occurred during generation',
              });
            }
          } else if (message.status === 'processing') {
            updateJobStatus(message.job_id, 'processing');
          }
          break;
        }

        case 'queue_status': {
          logger.debug('WebSocket', 'Queue status update', {
            queueSize: message.queue_size,
            processing: message.processing_count
          });

          setQueueStatus({
            queueSize: message.queue_size,
            currentJobId: message.current_job_id,
            pendingCount: message.pending_count,
            processingCount: message.processing_count,
            completedCount: message.completed_count,
            failedCount: message.failed_count ?? 0,
          });
          break;
        }

        case 'job_created': {
          logger.info('WebSocket', 'New job created', {
            jobId: message.job_id,
            assetId: message.asset_id,
            jobType: message.job_type
          });

          const newJob: GenerationJob = {
            id: message.job_id,
            assetId: message.asset_id,
            type: message.job_type,
            status: 'queued',
            progress: 0,
            createdAt: new Date().toISOString(),
          };
          addJob(newJob);
          setCurrentJobId(message.job_id);

          // Subscribe to job updates
          clientRef.current?.subscribeToJob(message.job_id);
          break;
        }

        case 'asset_ready': {
          logger.info('WebSocket', 'Asset ready', { name: message.name });

          addNotification({
            type: 'success',
            title: 'Asset Ready',
            message: `${message.name} is now available in your library`,
          });
          // Asset will be fetched from API
          break;
        }

        case 'error': {
          logger.error('WebSocket', 'Server error', message);
          addNotification({
            type: 'error',
            title: 'Error',
            message: message.message,
          });
          break;
        }

        case 'rigging_progress': {
          logger.info('WebSocket', 'Rigging progress update', {
            jobId: message.job_id,
            progress: message.progress,
            stage: message.stage,
            detectedType: message.detected_type,
          });

          setRiggingProgress(message.progress, message.stage);
          if (message.detected_type) {
            setDetectedType(message.detected_type as CharacterType);
          }
          break;
        }

        case 'rigging_complete': {
          logger.info('WebSocket', 'Rigging complete', {
            assetId: message.asset_id,
            characterType: message.character_type,
            boneCount: message.bone_count,
          });

          setIsRigging(false);
          setRiggingStatus('completed');
          setRiggingProgress(1.0, 'Complete');

          // Load skeleton data from API
          if (message.asset_id) {
            getSkeleton(message.asset_id)
              .then((skeletonResponse) => {
                if (skeletonResponse) {
                  logger.info('WebSocket', 'Loaded skeleton data', {
                    assetId: message.asset_id,
                    boneCount: skeletonResponse.skeleton.boneCount,
                  });
                  setSkeletonData(skeletonResponse.skeleton);
                }
              })
              .catch((err) => {
                logger.error('WebSocket', 'Failed to load skeleton', err);
              });

            // Reload model to show rigged version
            if (message.asset_id === currentAssetId) {
              logger.info('WebSocket', 'Reloading model after rigging', { assetId: message.asset_id });
              reloadModel();
            }

            // Refresh asset data
            getAsset(message.asset_id)
              .then((updatedAsset) => {
                updateAsset(updatedAsset.id, updatedAsset);
              })
              .catch((err) => {
                logger.error('WebSocket', 'Failed to refresh asset after rigging', err);
              });
          }

          // Update workflow store if this is the active workflow
          if (message.asset_id === workflowAssetId) {
            setWorkflowProcessing(false);
            setStageStatus('rigging', 'completed');
            setWorkflowProgress(1.0, 'Complete');

            // Reload model to show rigged version
            const modelUrl = getAssetModelUrl(message.asset_id);
            logger.info('WebSocket', 'Loading rigged model into viewer', {
              assetId: message.asset_id,
              modelUrl
            });
            loadModel(modelUrl, message.asset_id);
          }

          addNotification({
            type: 'success',
            title: 'Rigging Complete',
            message: `${message.character_type} skeleton applied (${message.bone_count} bones)`,
          });
          break;
        }

        case 'rigging_failed': {
          logger.error('WebSocket', 'Rigging failed', {
            assetId: message.asset_id,
            error: message.error,
          });

          setIsRigging(false);
          setRiggingStatus('failed');
          setRiggingError(message.error || 'Rigging failed');

          // Update workflow store if this is the active workflow
          if (message.asset_id === workflowAssetId) {
            setWorkflowProcessing(false);
            setStageStatus('rigging', 'failed', message.error);
          }

          addNotification({
            type: 'error',
            title: 'Rigging Failed',
            message: message.error || 'An error occurred during rigging',
          });
          break;
        }

        case 'workflow_update': {
          logger.info('WebSocket', 'Workflow update', {
            assetId: message.asset_id,
            stage: message.stage,
            status: message.status,
            progress: message.progress,
          });

          // Only process if this is for the active workflow asset
          if (message.asset_id === workflowAssetId) {
            // Map backend stage to frontend stage
            const stageMap: Record<string, 'upload' | 'mesh' | 'texture' | 'rigging' | 'export'> = {
              'uploaded': 'upload',
              'mesh_generated': 'mesh',
              'mesh_approved': 'mesh',
              'textured': 'texture',
              'texture_approved': 'texture',
              'rigged': 'rigging',
              'exported': 'export',
            };
            const frontendStage = stageMap[message.stage] || 'upload';

            // Map status
            const statusMap: Record<string, 'pending' | 'processing' | 'completed' | 'approved' | 'skipped' | 'failed'> = {
              'started': 'processing',
              'progress': 'processing',
              'completed': 'completed',
              'approved': 'approved',
              'failed': 'failed',
              'advanced': 'completed',
              'skipped_to_export': 'skipped',
            };
            const frontendStatus = statusMap[message.status] || 'pending';

            setStageStatus(frontendStage, frontendStatus);
            if (message.progress !== undefined) {
              setWorkflowProgress(message.progress, message.message || '');
            }
          }
          break;
        }

        case 'pipeline_status': {
          logger.debug('WebSocket', 'Pipeline status update', {
            shapeLoaded: message.shape_loaded,
            textureLoaded: message.texture_loaded,
            vramAllocated: message.vram_allocated_gb,
            vramFree: message.vram_free_gb,
          });

          setPipelineStatus({
            shapeLoaded: message.shape_loaded,
            textureLoaded: message.texture_loaded,
            vramAllocatedGb: message.vram_allocated_gb,
            vramFreeGb: message.vram_free_gb,
          });
          break;
        }
      }
    },
    [
      updateJobProgress,
      updateJobStatus,
      setQueueStatus,
      addJob,
      setCurrentJobId,
      setIsGenerating,
      addNotification,
      addAsset,
      updateAsset,
      reloadModel,
      loadModel,
      currentAssetId,
      setRiggingProgress,
      setDetectedType,
      setIsRigging,
      setRiggingStatus,
      setRiggingError,
      setSkeletonData,
      workflowAssetId,
      workflowCurrentStage,
      setWorkflowProgress,
      setStageStatus,
      setPipelineStatus,
      setWorkflowProcessing,
    ]
  );

  // Connect handler
  const handleConnect = useCallback(() => {
    logger.info('WebSocket', 'Connected to server');
    setConnected(true);
    setConnectionError(null);

    // Request initial queue status
    clientRef.current?.requestQueueStatus();
  }, [setConnected, setConnectionError]);

  // Disconnect handler
  const handleDisconnect = useCallback(() => {
    logger.warn('WebSocket', 'Disconnected from server');
    setConnected(false);
  }, [setConnected]);

  // Error handler
  const handleError = useCallback(
    (error: Event | Error) => {
      logger.error('WebSocket', 'Connection error', error);
      setConnectionError('Connection error');
    },
    [setConnectionError]
  );

  // Initialize WebSocket
  useEffect(() => {
    const client = getWebSocketClient();
    clientRef.current = client;

    // Register handlers
    const unsubMessage = client.onMessage(handleMessage);
    const unsubConnect = client.onConnect(handleConnect);
    const unsubDisconnect = client.onDisconnect(handleDisconnect);
    const unsubError = client.onError(handleError);

    // Connect
    client.connect();

    // Cleanup
    return () => {
      unsubMessage();
      unsubConnect();
      unsubDisconnect();
      unsubError();
    };
  }, [handleMessage, handleConnect, handleDisconnect, handleError]);

  // Return client methods
  return {
    isConnected: clientRef.current?.isConnected ?? false,
    subscribeToJob: (jobId: string) => clientRef.current?.subscribeToJob(jobId),
    unsubscribeFromJob: (jobId: string) => clientRef.current?.unsubscribeFromJob(jobId),
    requestQueueStatus: () => clientRef.current?.requestQueueStatus(),
  };
}
