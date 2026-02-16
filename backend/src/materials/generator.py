"""PBR material map generator."""

import logging
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)


def load_texture(path: Path) -> np.ndarray:
    """Load a texture as numpy array."""
    img = Image.open(path).convert('RGB')
    return np.array(img, dtype=np.float32) / 255.0


def save_texture(data: np.ndarray, path: Path, mode: str = 'RGB') -> None:
    """Save numpy array as texture."""
    data = np.clip(data * 255, 0, 255).astype(np.uint8)
    img = Image.fromarray(data, mode=mode)
    img.save(path)
    logger.info(f"Saved texture: {path}")


def generate_normal_map(
    color_texture: np.ndarray,
    strength: float = 1.0,
) -> np.ndarray:
    """
    Generate a normal map from a color texture using Sobel filters.

    Args:
        color_texture: RGB texture as float array
        strength: Normal map intensity (1.0 = normal, higher = more pronounced)

    Returns:
        Normal map as RGB array
    """
    # Convert to grayscale (luminance)
    if len(color_texture.shape) == 3:
        gray = np.dot(color_texture[..., :3], [0.299, 0.587, 0.114])
    else:
        gray = color_texture

    # Compute gradients using Sobel-like operators
    # Horizontal gradient (X)
    gx = np.zeros_like(gray)
    gx[:, :-1] = gray[:, 1:] - gray[:, :-1]
    gx[:, -1] = 0

    # Vertical gradient (Y)
    gy = np.zeros_like(gray)
    gy[:-1, :] = gray[1:, :] - gray[:-1, :]
    gy[-1, :] = 0

    # Scale gradients by strength
    gx *= strength
    gy *= strength

    # Create normal map (X, Y, Z)
    # Z component ensures normalized vectors
    z = np.sqrt(1 - np.clip(gx**2 + gy**2, 0, 1))

    # Pack into RGB (convert from [-1,1] to [0,1])
    normal_map = np.zeros((*gray.shape, 3), dtype=np.float32)
    normal_map[..., 0] = gx * 0.5 + 0.5  # R = X
    normal_map[..., 1] = gy * 0.5 + 0.5  # G = Y
    normal_map[..., 2] = z * 0.5 + 0.5   # B = Z

    return normal_map


def generate_roughness_map(
    color_texture: np.ndarray,
    base_roughness: float = 0.5,
    variance: float = 0.3,
    invert: bool = False,
) -> np.ndarray:
    """
    Generate a roughness map from color texture.

    Darker/less saturated areas are assumed rougher.

    Args:
        color_texture: RGB texture
        base_roughness: Base roughness value (0-1)
        variance: How much the texture affects roughness
        invert: Invert the result

    Returns:
        Grayscale roughness map as RGB array
    """
    # Calculate value (brightness) and saturation
    r, g, b = color_texture[..., 0], color_texture[..., 1], color_texture[..., 2]

    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)

    value = max_c
    saturation = np.zeros_like(max_c)
    mask = max_c > 0
    saturation[mask] = (max_c[mask] - min_c[mask]) / max_c[mask]

    # Higher saturation = likely shiny (low roughness)
    # Higher value = likely shiny (low roughness)
    roughness_factor = 1.0 - (saturation * 0.5 + value * 0.5)

    # Apply base and variance
    roughness = base_roughness + (roughness_factor - 0.5) * variance
    roughness = np.clip(roughness, 0, 1)

    if invert:
        roughness = 1.0 - roughness

    # Return as RGB
    return np.stack([roughness, roughness, roughness], axis=-1)


def generate_metallic_map(
    color_texture: np.ndarray,
    threshold: float = 0.7,
    metallic_colors: list = None,
) -> np.ndarray:
    """
    Generate a metallic map from color texture.

    Detects metallic-looking colors (high saturation yellows, grays, etc.)

    Args:
        color_texture: RGB texture
        threshold: Saturation threshold for metallic detection
        metallic_colors: List of RGB tuples for metallic colors

    Returns:
        Grayscale metallic map as RGB array
    """
    r, g, b = color_texture[..., 0], color_texture[..., 1], color_texture[..., 2]

    # Default metallic colors (gold, silver, copper, bronze)
    if metallic_colors is None:
        metallic_colors = [
            (1.0, 0.84, 0.0),   # Gold
            (0.75, 0.75, 0.75), # Silver
            (0.72, 0.45, 0.2),  # Copper
            (0.8, 0.5, 0.2),    # Bronze
            (0.5, 0.5, 0.5),    # Gray metal
        ]

    # Calculate color similarity to metallic colors
    metallic = np.zeros_like(r)

    for mc in metallic_colors:
        # Calculate distance to metallic color
        dist = np.sqrt(
            (r - mc[0])**2 +
            (g - mc[1])**2 +
            (b - mc[2])**2
        )
        # Convert distance to similarity (closer = more metallic)
        similarity = 1.0 - np.clip(dist / 0.5, 0, 1)
        metallic = np.maximum(metallic, similarity * 0.5)

    # Also check for high value + low saturation (chrome-like)
    max_c = np.maximum(np.maximum(r, g), b)
    min_c = np.minimum(np.minimum(r, g), b)

    value = max_c
    saturation = np.zeros_like(max_c)
    mask = max_c > 0
    saturation[mask] = (max_c[mask] - min_c[mask]) / max_c[mask]

    # High value + low saturation = possibly metallic
    chrome_like = value * (1.0 - saturation)
    metallic = np.maximum(metallic, chrome_like * 0.3)

    metallic = np.clip(metallic, 0, 1)

    return np.stack([metallic, metallic, metallic], axis=-1)


def generate_ao_map(
    color_texture: np.ndarray,
    strength: float = 1.0,
    blur_radius: int = 3,
) -> np.ndarray:
    """
    Generate an ambient occlusion map from color texture.

    Uses edge detection and blur to simulate cavity darkness.

    Args:
        color_texture: RGB texture
        strength: AO intensity
        blur_radius: Blur radius for smoothing

    Returns:
        Grayscale AO map as RGB array
    """
    # Convert to grayscale
    if len(color_texture.shape) == 3:
        gray = np.dot(color_texture[..., :3], [0.299, 0.587, 0.114])
    else:
        gray = color_texture

    # Detect edges (crevices are dark, edges are bright)
    # Use simple gradient magnitude
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, :-1] = gray[:, 1:] - gray[:, :-1]
    gy[:-1, :] = gray[1:, :] - gray[:-1, :]

    edges = np.sqrt(gx**2 + gy**2)

    # Invert edges (crevices should be dark in AO)
    ao = 1.0 - edges * strength

    # Blend with original brightness (darker areas get more AO)
    ao = ao * (0.5 + gray * 0.5)

    # Apply blur for smooth AO
    if blur_radius > 0:
        ao_img = Image.fromarray((np.clip(ao, 0, 1) * 255).astype(np.uint8), mode='L')
        ao_img = ao_img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        ao = np.array(ao_img, dtype=np.float32) / 255.0

    ao = np.clip(ao, 0, 1)

    return np.stack([ao, ao, ao], axis=-1)


def generate_pbr_maps(
    color_texture_path: Path,
    output_dir: Path,
    prefix: str = "",
    normal_strength: float = 1.0,
    base_roughness: float = 0.5,
    roughness_variance: float = 0.3,
    ao_strength: float = 1.0,
) -> dict:
    """
    Generate all PBR maps from a color texture.

    Args:
        color_texture_path: Path to base color texture
        output_dir: Directory to save generated maps
        prefix: Filename prefix for output files
        normal_strength: Normal map intensity
        base_roughness: Base roughness value
        roughness_variance: Roughness variation
        ao_strength: AO intensity

    Returns:
        Dict with paths to generated maps
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load color texture
    color = load_texture(color_texture_path)

    results = {
        'color': str(color_texture_path),
    }

    # Generate normal map
    normal = generate_normal_map(color, strength=normal_strength)
    normal_path = output_dir / f"{prefix}normal.png"
    save_texture(normal, normal_path)
    results['normal'] = str(normal_path)

    # Generate roughness map
    roughness = generate_roughness_map(
        color,
        base_roughness=base_roughness,
        variance=roughness_variance,
    )
    roughness_path = output_dir / f"{prefix}roughness.png"
    save_texture(roughness, roughness_path)
    results['roughness'] = str(roughness_path)

    # Generate metallic map
    metallic = generate_metallic_map(color)
    metallic_path = output_dir / f"{prefix}metallic.png"
    save_texture(metallic, metallic_path)
    results['metallic'] = str(metallic_path)

    # Generate AO map
    ao = generate_ao_map(color, strength=ao_strength)
    ao_path = output_dir / f"{prefix}ao.png"
    save_texture(ao, ao_path)
    results['ao'] = str(ao_path)

    logger.info(f"Generated PBR maps for {color_texture_path}")

    return results
