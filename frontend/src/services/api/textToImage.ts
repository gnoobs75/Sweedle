/**
 * Text-to-Image API client
 */

import { apiClient } from './client';

export interface StylePreset {
  id: string;
  name: string;
  description: string;
}

export interface TextToImageRequest {
  prompt: string;
  style_preset?: string;
  negative_prompt?: string;
  seed?: number;
  num_inference_steps?: number;
  guidance_scale?: number;
}

export interface TextToImageResponse {
  success: boolean;
  image_id: string;
  image_url: string;
  seed_used: number;
  prompt_used: string;
  generation_time: number;
  error?: string;
}

/**
 * Get available style presets for text-to-image generation.
 */
export async function getStylePresets(): Promise<StylePreset[]> {
  return apiClient.get<StylePreset[]>('/generation/text-to-image/presets');
}

/**
 * Generate an image from a text prompt.
 */
export async function generateImageFromText(
  request: TextToImageRequest
): Promise<TextToImageResponse> {
  const formData = new FormData();
  formData.append('prompt', request.prompt);

  if (request.style_preset) {
    formData.append('style_preset', request.style_preset);
  }
  if (request.negative_prompt) {
    formData.append('negative_prompt', request.negative_prompt);
  }
  if (request.seed !== undefined) {
    formData.append('seed', request.seed.toString());
  }
  if (request.num_inference_steps !== undefined) {
    formData.append('num_inference_steps', request.num_inference_steps.toString());
  }
  if (request.guidance_scale !== undefined) {
    formData.append('guidance_scale', request.guidance_scale.toString());
  }

  return apiClient.post<TextToImageResponse>(
    '/generation/text-to-image',
    formData
  );
}

/**
 * Convert a generated image URL to a File object for use with image-to-3D.
 */
export async function imageUrlToFile(
  imageUrl: string,
  filename: string = 'generated.png'
): Promise<File> {
  const response = await fetch(imageUrl);
  const blob = await response.blob();
  return new File([blob], filename, { type: 'image/png' });
}
