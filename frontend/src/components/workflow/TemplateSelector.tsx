/**
 * TemplateSelector - UI for selecting and managing workflow templates
 */

import { useState, useEffect, useCallback } from 'react';
import {
  listTemplates,
  listCategories,
  createTemplate,
  deleteTemplate,
  type WorkflowTemplate,
  type CreateTemplateParams,
} from '../../services/api/templates';

interface TemplateSelectorProps {
  onSelectTemplate?: (template: WorkflowTemplate) => void;
  showCreateOption?: boolean;
}

export function TemplateSelector({
  onSelectTemplate,
  showCreateOption = true,
}: TemplateSelectorProps) {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Load templates and categories
  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [templatesData, categoriesData] = await Promise.all([
        listTemplates(selectedCategory || undefined),
        listCategories(),
      ]);
      setTemplates(templatesData);
      setCategories(categoriesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load templates');
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDeleteTemplate = async (templateId: string) => {
    if (!confirm('Are you sure you want to delete this template?')) return;

    try {
      await deleteTemplate(templateId);
      loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete template');
    }
  };

  const getStageIcons = (template: WorkflowTemplate) => {
    const stages = [];
    if (template.includeMesh) stages.push({ name: 'Mesh', icon: '🎲' });
    if (template.includeTexture) stages.push({ name: 'Texture', icon: '🎨' });
    if (template.includeRigging) stages.push({ name: 'Rigging', icon: '🦴' });
    if (template.includeAnimation) stages.push({ name: 'Animation', icon: '🎬' });
    if (template.includeExport) stages.push({ name: 'Export', icon: '📦' });
    return stages;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-white flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
          </svg>
          Workflow Templates
        </h3>
        {showCreateOption && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="text-xs text-indigo-400 hover:text-indigo-300"
          >
            + Create Template
          </button>
        )}
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`px-2 py-1 text-xs rounded ${
            selectedCategory === null
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:text-white'
          }`}
        >
          All
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-2 py-1 text-xs rounded capitalize ${
              selectedCategory === cat
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-2 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="text-center py-8 text-gray-400">
          Loading templates...
        </div>
      )}

      {/* Template Grid */}
      {!isLoading && (
        <div className="grid grid-cols-1 gap-3">
          {templates.map(template => (
            <div
              key={template.id}
              className="p-3 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-indigo-500/50 cursor-pointer transition-colors"
              onClick={() => onSelectTemplate?.(template)}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-medium text-white">{template.name}</h4>
                    {template.isBuiltin && (
                      <span className="px-1 py-0.5 text-[10px] bg-indigo-900/50 text-indigo-300 rounded">
                        Built-in
                      </span>
                    )}
                    {template.category && (
                      <span className="px-1 py-0.5 text-[10px] bg-gray-700 text-gray-300 rounded capitalize">
                        {template.category}
                      </span>
                    )}
                  </div>
                  {template.description && (
                    <p className="text-xs text-gray-400 mt-1">{template.description}</p>
                  )}
                </div>
                {!template.isBuiltin && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteTemplate(template.id);
                    }}
                    className="text-gray-500 hover:text-red-400"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                )}
              </div>

              {/* Stages */}
              <div className="flex gap-2 mt-2">
                {getStageIcons(template).map(stage => (
                  <span
                    key={stage.name}
                    className="text-xs bg-gray-900/50 px-1.5 py-0.5 rounded"
                    title={stage.name}
                  >
                    {stage.icon} {stage.name}
                  </span>
                ))}
              </div>

              {/* Settings Summary */}
              {template.meshSettings && (
                <div className="text-[10px] text-gray-500 mt-2">
                  {template.meshSettings.inferenceSteps} steps, {template.meshSettings.octreeResolution} resolution
                </div>
              )}
            </div>
          ))}

          {templates.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              No templates found
            </div>
          )}
        </div>
      )}

      {/* Create Template Modal */}
      {showCreateModal && (
        <CreateTemplateModal
          onClose={() => setShowCreateModal(false)}
          onCreated={() => {
            setShowCreateModal(false);
            loadData();
          }}
        />
      )}
    </div>
  );
}

// Create Template Modal
interface CreateTemplateModalProps {
  onClose: () => void;
  onCreated: () => void;
}

function CreateTemplateModal({ onClose, onCreated }: CreateTemplateModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [includeMesh, setIncludeMesh] = useState(true);
  const [includeTexture, setIncludeTexture] = useState(true);
  const [includeRigging, setIncludeRigging] = useState(false);
  const [includeAnimation, setIncludeAnimation] = useState(false);
  const [includeExport, setIncludeExport] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!name.trim()) {
      setError('Name is required');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      await createTemplate({
        name: name.trim(),
        description: description.trim() || undefined,
        category: category.trim() || undefined,
        includeMesh,
        includeTexture,
        includeRigging,
        includeAnimation,
        includeExport,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create template');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg border border-gray-700 max-w-md w-full p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-white">Create Template</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="p-2 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400">
            {error}
          </div>
        )}

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Name *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-white"
              placeholder="My Template"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-white"
              placeholder="Template description..."
              rows={2}
            />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Category</label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-white"
              placeholder="e.g., character, prop, environment"
            />
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-2">Stages</label>
            <div className="space-y-2">
              {[
                { key: 'mesh', label: 'Mesh Generation', checked: includeMesh, onChange: setIncludeMesh },
                { key: 'texture', label: 'Texture', checked: includeTexture, onChange: setIncludeTexture },
                { key: 'rigging', label: 'Rigging', checked: includeRigging, onChange: setIncludeRigging },
                { key: 'animation', label: 'Animation', checked: includeAnimation, onChange: setIncludeAnimation },
                { key: 'export', label: 'Export', checked: includeExport, onChange: setIncludeExport },
              ].map(stage => (
                <label key={stage.key} className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={stage.checked}
                    onChange={(e) => stage.onChange(e.target.checked)}
                    className="rounded border-gray-600"
                  />
                  {stage.label}
                </label>
              ))}
            </div>
          </div>
        </div>

        <div className="flex gap-2 pt-2">
          <button
            onClick={onClose}
            className="flex-1 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={isCreating}
            className="flex-1 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 rounded"
          >
            {isCreating ? 'Creating...' : 'Create Template'}
          </button>
        </div>
      </div>
    </div>
  );
}
