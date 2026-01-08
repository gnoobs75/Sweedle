/**
 * QueuePanel Component - Complete queue management panel
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { useQueueStore } from '../../stores/queueStore';
import { JobCard, JobListItem } from './JobCard';
import { QueueControls } from './QueueControls';
import { FolderImporter } from './FolderImporter';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';
import type { GenerationJob } from '../../types';

type ViewMode = 'cards' | 'list';
type FilterStatus = 'all' | 'active' | 'completed' | 'failed';

interface QueuePanelProps {
  className?: string;
}

export function QueuePanel({ className }: QueuePanelProps) {
  const { jobs, selectedJobId, setSelectedJob } = useQueueStore();

  const [viewMode, setViewMode] = useState<ViewMode>('cards');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [showImporter, setShowImporter] = useState(false);
  const [selectedJob, setLocalSelectedJob] = useState<GenerationJob | null>(null);

  // Filter jobs
  const filteredJobs = useMemo(() => {
    switch (filterStatus) {
      case 'active':
        return jobs.filter(
          (j) => j.status === 'processing' || j.status === 'queued' || j.status === 'pending'
        );
      case 'completed':
        return jobs.filter((j) => j.status === 'completed');
      case 'failed':
        return jobs.filter((j) => j.status === 'failed' || j.status === 'cancelled');
      default:
        return jobs;
    }
  }, [jobs, filterStatus]);

  // Sort: processing first, then by creation date
  const sortedJobs = useMemo(() => {
    return [...filteredJobs].sort((a, b) => {
      const statusOrder = {
        processing: 0,
        queued: 1,
        pending: 2,
        completed: 3,
        failed: 4,
        cancelled: 5,
      };
      const aOrder = statusOrder[a.status] ?? 10;
      const bOrder = statusOrder[b.status] ?? 10;
      if (aOrder !== bOrder) return aOrder - bOrder;
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });
  }, [filteredJobs]);

  // Update selected job when jobs change
  useEffect(() => {
    if (selectedJobId) {
      const job = jobs.find((j) => j.id === selectedJobId);
      setLocalSelectedJob(job || null);
    }
  }, [jobs, selectedJobId]);

  const handleJobClick = useCallback(
    (job: GenerationJob) => {
      setSelectedJob(job.id);
      setLocalSelectedJob(job);
    },
    [setSelectedJob]
  );

  const handleCloseDetails = useCallback(() => {
    setSelectedJob(null);
    setLocalSelectedJob(null);
  }, [setSelectedJob]);

  const activeCount = jobs.filter(
    (j) => j.status === 'processing' || j.status === 'queued' || j.status === 'pending'
  ).length;

  return (
    <div className={cn('h-full flex', className)}>
      {/* Main Content */}
      <div className={cn('flex-1 flex flex-col min-w-0', selectedJob && 'hidden lg:flex')}>
        {/* Header */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">Queue</h2>
              <p className="text-sm text-text-muted">
                {jobs.length} job{jobs.length !== 1 ? 's' : ''}
                {activeCount > 0 && ` (${activeCount} active)`}
              </p>
            </div>
            <Button variant="primary" size="sm" onClick={() => setShowImporter(true)}>
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Batch Import
            </Button>
          </div>

          {/* Controls */}
          <QueueControls />
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1 px-4 py-2 border-b border-border bg-surface-light overflow-x-auto">
          {(['all', 'active', 'completed', 'failed'] as const).map((status) => {
            const count = (() => {
              switch (status) {
                case 'active':
                  return jobs.filter(
                    (j) => j.status === 'processing' || j.status === 'queued' || j.status === 'pending'
                  ).length;
                case 'completed':
                  return jobs.filter((j) => j.status === 'completed').length;
                case 'failed':
                  return jobs.filter((j) => j.status === 'failed' || j.status === 'cancelled').length;
                default:
                  return jobs.length;
              }
            })();

            return (
              <button
                key={status}
                onClick={() => setFilterStatus(status)}
                className={cn(
                  'px-3 py-1.5 rounded-lg text-sm capitalize whitespace-nowrap transition-colors',
                  filterStatus === status
                    ? 'bg-primary text-white'
                    : 'text-text-secondary hover:bg-surface-lighter'
                )}
              >
                {status}
                {count > 0 && (
                  <Badge
                    variant={filterStatus === status ? 'default' : 'default'}
                    size="sm"
                    className="ml-1.5"
                  >
                    {count}
                  </Badge>
                )}
              </button>
            );
          })}

          {/* View Mode Toggle */}
          <div className="ml-auto flex items-center bg-surface rounded-lg p-1">
            <button
              onClick={() => setViewMode('cards')}
              className={cn(
                'p-1.5 rounded transition-colors',
                viewMode === 'cards' ? 'bg-primary text-white' : 'text-text-muted hover:text-text-primary'
              )}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
              </svg>
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                'p-1.5 rounded transition-colors',
                viewMode === 'list' ? 'bg-primary text-white' : 'text-text-muted hover:text-text-primary'
              )}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>

        {/* Job List */}
        <div className="flex-1 overflow-y-auto p-4">
          {sortedJobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <svg
                className="w-16 h-16 text-text-muted mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
              <p className="text-text-secondary mb-2">
                {filterStatus === 'all'
                  ? 'No jobs in queue'
                  : `No ${filterStatus} jobs`}
              </p>
              <p className="text-sm text-text-muted mb-4">
                Start a generation or import images to add jobs
              </p>
              <Button variant="secondary" onClick={() => setShowImporter(true)}>
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Import Images
              </Button>
            </div>
          ) : viewMode === 'cards' ? (
            <div className="space-y-3">
              {sortedJobs.map((job) => (
                <JobCard key={job.id} job={job} />
              ))}
            </div>
          ) : (
            <div className="divide-y divide-border">
              {sortedJobs.map((job) => (
                <JobListItem
                  key={job.id}
                  job={job}
                  onClick={() => handleJobClick(job)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Job Details Sidebar (when clicking on list item) */}
      {selectedJob && viewMode === 'list' && (
        <div className="w-full lg:w-96 border-l border-border bg-surface flex-shrink-0 animate-fadeIn">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h3 className="text-lg font-semibold text-text-primary">Job Details</h3>
            <button
              onClick={handleCloseDetails}
              className="p-1 text-text-muted hover:text-text-primary transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="p-4">
            <JobCard job={selectedJob} />
          </div>
        </div>
      )}

      {/* Folder Importer Modal */}
      {showImporter && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowImporter(false)}
          />
          <div className="relative w-full max-w-2xl max-h-[80vh] bg-surface rounded-2xl shadow-2xl overflow-hidden animate-fadeIn">
            <FolderImporter onClose={() => setShowImporter(false)} />
          </div>
        </div>
      )}
    </div>
  );
}
