/**
 * TagManager Component - Create and manage tags
 */

import { useState, useCallback } from 'react';
import { useLibraryStore } from '../../stores/libraryStore';
import { useUIStore } from '../../stores/uiStore';
import { createTag, deleteTag as deleteTagApi } from '../../services/api/assets';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';
import { cn } from '../../lib/utils';
import type { Tag } from '../../types';

interface TagManagerProps {
  className?: string;
}

const TAG_COLORS = [
  '#ef4444', // Red
  '#f97316', // Orange
  '#f59e0b', // Amber
  '#84cc16', // Lime
  '#22c55e', // Green
  '#14b8a6', // Teal
  '#06b6d4', // Cyan
  '#3b82f6', // Blue
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#a855f7', // Purple
  '#ec4899', // Pink
];

export function TagManager({ className }: TagManagerProps) {
  const { tags, addTag, removeTag } = useLibraryStore();
  const { addNotification } = useUIStore();

  const [newTagName, setNewTagName] = useState('');
  const [selectedColor, setSelectedColor] = useState(TAG_COLORS[0]);
  const [isCreating, setIsCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const handleCreateTag = useCallback(async () => {
    if (!newTagName.trim()) return;

    setIsCreating(true);
    try {
      const tag = await createTag(newTagName.trim(), selectedColor);
      addTag(tag);
      setNewTagName('');
      setShowForm(false);
      addNotification({
        type: 'success',
        title: 'Tag Created',
        message: `Tag "${tag.name}" has been created`,
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Failed to Create Tag',
        message: error instanceof Error ? error.message : 'An error occurred',
      });
    } finally {
      setIsCreating(false);
    }
  }, [newTagName, selectedColor, addTag, addNotification]);

  const handleDeleteTag = useCallback(
    async (tag: Tag) => {
      try {
        await deleteTagApi(tag.id);
        removeTag(tag.id);
        addNotification({
          type: 'success',
          title: 'Tag Deleted',
          message: `Tag "${tag.name}" has been deleted`,
        });
      } catch (error) {
        addNotification({
          type: 'error',
          title: 'Failed to Delete Tag',
          message: error instanceof Error ? error.message : 'An error occurred',
        });
      }
    },
    [removeTag, addNotification]
  );

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text-secondary">Tags</h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowForm(!showForm)}
        >
          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Tag
        </Button>
      </div>

      {/* Create Tag Form */}
      {showForm && (
        <Card variant="outlined" padding="sm" className="space-y-3 animate-fadeIn">
          <Input
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            placeholder="Tag name"
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleCreateTag();
            }}
          />

          <div>
            <label className="block text-xs text-text-muted mb-2">Color</label>
            <div className="flex flex-wrap gap-1.5">
              {TAG_COLORS.map((color) => (
                <button
                  key={color}
                  onClick={() => setSelectedColor(color)}
                  className={cn(
                    'w-6 h-6 rounded-full transition-all',
                    selectedColor === color && 'ring-2 ring-offset-2 ring-offset-surface ring-white scale-110'
                  )}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={handleCreateTag}
              isLoading={isCreating}
              disabled={!newTagName.trim()}
              className="flex-1"
            >
              Create
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </Button>
          </div>
        </Card>
      )}

      {/* Tag List */}
      {tags.length > 0 ? (
        <div className="space-y-1">
          {tags.map((tag) => (
            <div
              key={tag.id}
              className="flex items-center justify-between p-2 rounded-lg hover:bg-surface-light group"
            >
              <Badge
                variant="default"
                style={{ backgroundColor: `${tag.color}20`, color: tag.color }}
              >
                {tag.name}
              </Badge>
              <button
                onClick={() => handleDeleteTag(tag)}
                className="p-1 text-text-muted hover:text-error opacity-0 group-hover:opacity-100 transition-all"
                title="Delete tag"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-text-muted text-center py-4">
          No tags yet. Create one to organize your assets.
        </p>
      )}
    </div>
  );
}

/**
 * Inline tag selector for asset editing
 */
interface TagSelectorProps {
  selectedTags: number[];
  onChange: (tagIds: number[]) => void;
  className?: string;
}

export function TagSelector({ selectedTags, onChange, className }: TagSelectorProps) {
  const { tags } = useLibraryStore();

  const toggleTag = useCallback(
    (tagId: number) => {
      if (selectedTags.includes(tagId)) {
        onChange(selectedTags.filter((id) => id !== tagId));
      } else {
        onChange([...selectedTags, tagId]);
      }
    },
    [selectedTags, onChange]
  );

  if (tags.length === 0) {
    return (
      <p className="text-sm text-text-muted">
        No tags available. Create tags in the library panel.
      </p>
    );
  }

  return (
    <div className={cn('flex flex-wrap gap-1.5', className)}>
      {tags.map((tag) => {
        const isSelected = selectedTags.includes(tag.id);
        return (
          <Badge
            key={tag.id}
            variant={isSelected ? 'primary' : 'default'}
            className="cursor-pointer transition-all hover:scale-105"
            style={
              isSelected
                ? { backgroundColor: tag.color, color: 'white' }
                : { backgroundColor: `${tag.color}20`, color: tag.color }
            }
            onClick={() => toggleTag(tag.id)}
          >
            {isSelected && (
              <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            )}
            {tag.name}
          </Badge>
        );
      })}
    </div>
  );
}
