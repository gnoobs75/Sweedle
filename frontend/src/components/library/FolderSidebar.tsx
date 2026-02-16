/**
 * FolderSidebar - Folder navigation sidebar for the library
 */

import { useState, useEffect, useCallback } from 'react';
import { useLibraryStore } from '../../stores/libraryStore';
import {
  getFolderTree,
  createFolder,
  deleteFolder,
  type FolderWithChildren,
  type Folder,
} from '../../services/api/folders';

interface FolderItemProps {
  folder: FolderWithChildren;
  depth: number;
  onSelect: (folder: FolderWithChildren) => void;
  onDelete: (folderId: number) => void;
  selectedFolderId: number | null;
}

function FolderItem({ folder, depth, onSelect, onDelete, selectedFolderId }: FolderItemProps) {
  const [isExpanded, setIsExpanded] = useState(depth < 2);
  const hasChildren = folder.children.length > 0;
  const isSelected = selectedFolderId === folder.id;

  return (
    <div>
      <div
        className={`flex items-center gap-1 px-2 py-1.5 rounded cursor-pointer group transition-colors ${
          isSelected
            ? 'bg-indigo-600 text-white'
            : 'text-gray-300 hover:bg-gray-700/50'
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={() => onSelect(folder)}
      >
        {hasChildren && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="p-0.5 hover:bg-gray-600 rounded"
          >
            <svg
              className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        )}
        {!hasChildren && <span className="w-4" />}

        <svg
          className="w-4 h-4 flex-shrink-0"
          style={{ color: folder.color }}
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z" />
        </svg>

        <span className="flex-1 text-sm truncate">{folder.name}</span>

        {folder.assetCount > 0 && (
          <span className={`text-xs ${isSelected ? 'text-indigo-200' : 'text-gray-500'}`}>
            {folder.assetCount}
          </span>
        )}

        <button
          onClick={(e) => {
            e.stopPropagation();
            if (confirm(`Delete folder "${folder.name}"? Assets will be moved to root.`)) {
              onDelete(folder.id);
            }
          }}
          className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-red-600 rounded transition-opacity"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {hasChildren && isExpanded && (
        <div>
          {folder.children.map((child) => (
            <FolderItem
              key={child.id}
              folder={child}
              depth={depth + 1}
              onSelect={onSelect}
              onDelete={onDelete}
              selectedFolderId={selectedFolderId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FolderSidebar() {
  const {
    folders,
    setFolders,
    currentFolderId,
    setCurrentFolder,
    setFolderPath,
    isFolderSidebarOpen,
    toggleFolderSidebar,
  } = useLibraryStore();

  const [isCreating, setIsCreating] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  // Load folder tree
  const loadFolders = useCallback(async () => {
    setIsLoading(true);
    try {
      const tree = await getFolderTree();
      setFolders(tree.folders);
    } catch (error) {
      console.error('Failed to load folders:', error);
    } finally {
      setIsLoading(false);
    }
  }, [setFolders]);

  useEffect(() => {
    loadFolders();
  }, [loadFolders]);

  // Handle folder selection
  const handleSelectFolder = useCallback(
    (folder: FolderWithChildren | null) => {
      if (folder === null) {
        setCurrentFolder(null);
        setFolderPath([]);
      } else {
        setCurrentFolder(folder.id);

        // Build path by finding parents
        const path: Folder[] = [];
        const findPath = (folders: FolderWithChildren[], targetId: number): boolean => {
          for (const f of folders) {
            if (f.id === targetId) {
              path.push(f);
              return true;
            }
            if (f.children.length > 0 && findPath(f.children, targetId)) {
              path.unshift(f);
              return true;
            }
          }
          return false;
        };
        findPath(folders, folder.id);
        setFolderPath(path);
      }
    },
    [folders, setCurrentFolder, setFolderPath]
  );

  // Create new folder
  const handleCreateFolder = useCallback(async () => {
    if (!newFolderName.trim()) return;

    try {
      await createFolder({
        name: newFolderName.trim(),
        parentId: currentFolderId || undefined,
      });
      setNewFolderName('');
      setIsCreating(false);
      loadFolders();
    } catch (error) {
      console.error('Failed to create folder:', error);
      alert(error instanceof Error ? error.message : 'Failed to create folder');
    }
  }, [newFolderName, currentFolderId, loadFolders]);

  // Delete folder
  const handleDeleteFolder = useCallback(
    async (folderId: number) => {
      try {
        await deleteFolder(folderId);
        if (currentFolderId === folderId) {
          handleSelectFolder(null);
        }
        loadFolders();
      } catch (error) {
        console.error('Failed to delete folder:', error);
        alert(error instanceof Error ? error.message : 'Failed to delete folder');
      }
    },
    [currentFolderId, handleSelectFolder, loadFolders]
  );

  if (!isFolderSidebarOpen) {
    return (
      <button
        onClick={toggleFolderSidebar}
        className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
        title="Show folders"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
          />
        </svg>
      </button>
    );
  }

  return (
    <div className="w-56 flex-shrink-0 bg-gray-800/50 border-r border-gray-700 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-2 border-b border-gray-700">
        <span className="text-sm font-medium text-gray-300">Folders</span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsCreating(true)}
            className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
            title="New folder"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
          </button>
          <button
            onClick={toggleFolderSidebar}
            className="p-1 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
            title="Hide folders"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            </svg>
          </button>
        </div>
      </div>

      {/* New folder input */}
      {isCreating && (
        <div className="p-2 border-b border-gray-700">
          <div className="flex gap-1">
            <input
              type="text"
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleCreateFolder();
                if (e.key === 'Escape') {
                  setIsCreating(false);
                  setNewFolderName('');
                }
              }}
              placeholder="Folder name"
              className="flex-1 px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
              autoFocus
            />
            <button
              onClick={handleCreateFolder}
              className="px-2 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded"
            >
              Add
            </button>
            <button
              onClick={() => {
                setIsCreating(false);
                setNewFolderName('');
              }}
              className="px-2 py-1 text-xs bg-gray-600 hover:bg-gray-500 text-white rounded"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Folder tree */}
      <div className="flex-1 overflow-y-auto py-1">
        {/* All Assets (root) */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 cursor-pointer transition-colors ${
            currentFolderId === null
              ? 'bg-indigo-600 text-white'
              : 'text-gray-300 hover:bg-gray-700/50'
          }`}
          onClick={() => handleSelectFolder(null)}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <span className="text-sm">All Assets</span>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="p-4 text-center text-gray-500 text-sm">Loading folders...</div>
        )}

        {/* Folder list */}
        {!isLoading && folders.length === 0 && (
          <div className="p-4 text-center text-gray-500 text-xs">
            No folders yet. Create one to organize your assets.
          </div>
        )}

        {!isLoading &&
          folders.map((folder) => (
            <FolderItem
              key={folder.id}
              folder={folder}
              depth={0}
              onSelect={handleSelectFolder}
              onDelete={handleDeleteFolder}
              selectedFolderId={currentFolderId}
            />
          ))}
      </div>
    </div>
  );
}
