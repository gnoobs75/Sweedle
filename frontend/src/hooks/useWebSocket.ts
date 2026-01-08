/**
 * WebSocket React Hook
 */

import { useEffect, useRef, useCallback } from 'react';
import { getWebSocketClient, WebSocketClient } from '../services/websocket/WebSocketClient';
import { useUIStore } from '../stores/uiStore';
import { useQueueStore } from '../stores/queueStore';
import { useLibraryStore } from '../stores/libraryStore';
import { useGenerationStore } from '../stores/generationStore';
import { logger } from '../lib/logger';
import type { WSMessage, GenerationJob } from '../types';

export function useWebSocket() {
  const clientRef = useRef<WebSocketClient | null>(null);

  const { setConnected, setConnectionError, addNotification } = useUIStore();
  const { updateJobProgress, updateJobStatus, setQueueStatus, addJob } = useQueueStore();
  const { addAsset } = useLibraryStore();
  const { setIsGenerating, setCurrentJobId } = useGenerationStore();

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

          if (message.status === 'completed' || message.status === 'failed') {
            logger.info('WebSocket', `Job ${message.status}`, {
              jobId: message.job_id,
              error: message.error
            });

            updateJobStatus(message.job_id, message.status, message.error);
            setIsGenerating(false);

            if (message.status === 'completed') {
              addNotification({
                type: 'success',
                title: 'Generation Complete',
                message: 'Your 3D model is ready!',
              });
            } else if (message.status === 'failed') {
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
