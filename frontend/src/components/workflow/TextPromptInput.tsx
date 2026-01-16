/**
 * TextPromptInput - Text-to-image input for generating source images
 */

import { useState, useEffect, useCallback } from 'react';
import {
  generateImageFromText,
  getStylePresets,
  imageUrlToFile,
  type StylePreset,
  type TextToImageResponse,
} from '../../services/api/textToImage';
import { useWorkflowStore } from '../../stores/workflowStore';
import { Spinner } from '../ui/Spinner';

interface TextPromptInputProps {
  onImageGenerated: (file: File, previewUrl: string) => void;
}

export function TextPromptInput({ onImageGenerated }: TextPromptInputProps) {
  const [prompt, setPrompt] = useState('');
  const [selectedPreset, setSelectedPreset] = useState('game_asset');
  const [presets, setPresets] = useState<StylePreset[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [negativePrompt, setNegativePrompt] = useState('');
  const [seed, setSeed] = useState<string>('');
  const [steps, setSteps] = useState(30);
  const [guidance, setGuidance] = useState(7.5);

  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  const [generatedImage, setGeneratedImage] = useState<TextToImageResponse | null>(null);

  // Load presets on mount
  useEffect(() => {
    loadPresets();
  }, []);

  async function loadPresets() {
    try {
      const fetchedPresets = await getStylePresets();
      setPresets(fetchedPresets);
    } catch (err) {
      console.error('Failed to load style presets:', err);
      // Use fallback presets
      setPresets([
        { id: 'game_asset', name: 'Game Asset', description: 'General 3D game asset' },
        { id: 'character', name: 'Character', description: 'Full-body character' },
        { id: 'prop', name: 'Prop', description: 'Game prop/item' },
        { id: 'creature', name: 'Creature', description: 'Fantasy creature' },
      ]);
    }
  }

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) return;

    setIsGenerating(true);
    setError(null);
    setProgress(0);
    setProgressMessage('Starting generation...');
    setGeneratedImage(null);

    try {
      const response = await generateImageFromText({
        prompt: prompt.trim(),
        style_preset: selectedPreset,
        negative_prompt: negativePrompt || undefined,
        seed: seed ? parseInt(seed, 10) : undefined,
        num_inference_steps: steps,
        guidance_scale: guidance,
      });

      if (response.success) {
        setGeneratedImage(response);
        setProgress(1);
        setProgressMessage('Image generated!');
      } else {
        throw new Error(response.error || 'Generation failed');
      }
    } catch (err) {
      console.error('Text-to-image generation failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate image');
    } finally {
      setIsGenerating(false);
    }
  }, [prompt, selectedPreset, negativePrompt, seed, steps, guidance]);

  const handleUseImage = useCallback(async () => {
    if (!generatedImage) return;

    try {
      // Convert the generated image URL to a File
      const file = await imageUrlToFile(
        generatedImage.image_url,
        `generated-${generatedImage.image_id}.png`
      );

      // Pass to parent with the image URL as preview
      onImageGenerated(file, generatedImage.image_url);
    } catch (err) {
      console.error('Failed to use generated image:', err);
      setError('Failed to process generated image');
    }
  }, [generatedImage, onImageGenerated]);

  const handleRegenerate = useCallback(() => {
    setGeneratedImage(null);
    handleGenerate();
  }, [handleGenerate]);

  return (
    <div className="space-y-4">
      {/* Prompt input */}
      <div className="space-y-2">
        <label className="block text-sm text-gray-400">
          Describe what you want to create
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g., a wooden treasure chest with gold trim and iron hinges"
          rows={3}
          maxLength={500}
          disabled={isGenerating}
          className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none resize-none disabled:opacity-50"
        />
        <div className="flex justify-between text-xs text-gray-500">
          <span>Be specific about the object you want to create</span>
          <span>{prompt.length}/500</span>
        </div>
      </div>

      {/* Style preset selector */}
      <div className="space-y-2">
        <label className="block text-sm text-gray-400">Style Preset</label>
        <div className="grid grid-cols-2 gap-2">
          {presets.slice(0, 6).map((preset) => (
            <button
              key={preset.id}
              onClick={() => setSelectedPreset(preset.id)}
              disabled={isGenerating}
              className={`p-2 rounded border text-left transition-colors ${
                selectedPreset === preset.id
                  ? 'border-indigo-500 bg-indigo-900/30 text-white'
                  : 'border-gray-600 bg-gray-800 text-gray-400 hover:border-gray-500'
              } disabled:opacity-50`}
            >
              <div className="text-sm font-medium">{preset.name}</div>
              <div className="text-xs text-gray-500 truncate">{preset.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Advanced options toggle */}
      <button
        onClick={() => setShowAdvanced(!showAdvanced)}
        disabled={isGenerating}
        className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-300 disabled:opacity-50"
      >
        <svg
          className={`w-4 h-4 transition-transform ${showAdvanced ? 'rotate-90' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        Advanced Options
      </button>

      {/* Advanced options */}
      {showAdvanced && (
        <div className="space-y-3 p-3 bg-gray-800/50 rounded border border-gray-700">
          <div className="space-y-1">
            <label className="block text-xs text-gray-400">Negative Prompt</label>
            <input
              type="text"
              value={negativePrompt}
              onChange={(e) => setNegativePrompt(e.target.value)}
              placeholder="Things to avoid (optional)"
              disabled={isGenerating}
              className="w-full px-2 py-1.5 text-sm bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
            />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1">
              <label className="block text-xs text-gray-400">Seed</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                placeholder="Random"
                disabled={isGenerating}
                className="w-full px-2 py-1.5 text-sm bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none disabled:opacity-50"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs text-gray-400">Steps: {steps}</label>
              <input
                type="range"
                min={10}
                max={50}
                value={steps}
                onChange={(e) => setSteps(parseInt(e.target.value, 10))}
                disabled={isGenerating}
                className="w-full disabled:opacity-50"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs text-gray-400">Guidance: {guidance.toFixed(1)}</label>
              <input
                type="range"
                min={1}
                max={20}
                step={0.5}
                value={guidance}
                onChange={(e) => setGuidance(parseFloat(e.target.value))}
                disabled={isGenerating}
                className="w-full disabled:opacity-50"
              />
            </div>
          </div>
        </div>
      )}

      {/* Generation progress / result */}
      {isGenerating && (
        <div className="p-4 bg-indigo-900/20 border border-indigo-700/30 rounded-lg">
          <div className="flex items-center gap-3">
            <Spinner size="md" variant="primary" />
            <div className="flex-1">
              <div className="text-sm font-medium text-indigo-400">
                {progressMessage || 'Generating image...'}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                First generation may take longer while loading model (~7GB)
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Generated image preview */}
      {generatedImage && !isGenerating && (
        <div className="space-y-3">
          <div className="relative rounded-lg overflow-hidden border border-gray-700">
            <img
              src={generatedImage.image_url}
              alt="Generated"
              className="w-full object-contain max-h-64"
            />
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-3">
              <div className="text-xs text-gray-300">
                Seed: {generatedImage.seed_used} | Time: {generatedImage.generation_time.toFixed(1)}s
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleRegenerate}
              className="flex-1 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded transition-colors"
            >
              Regenerate
            </button>
            <button
              onClick={handleUseImage}
              className="flex-1 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded transition-colors"
            >
              Use This Image
            </button>
          </div>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="p-3 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Generate button (when no image generated yet) */}
      {!generatedImage && !isGenerating && (
        <button
          onClick={handleGenerate}
          disabled={!prompt.trim()}
          className="w-full py-2.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed rounded transition-colors"
        >
          Generate Image
        </button>
      )}

      {/* Info note */}
      <p className="text-xs text-gray-500">
        Images are generated using Stable Diffusion XL locally on your GPU.
        First generation may take longer while loading the model (~7GB VRAM).
      </p>
    </div>
  );
}
