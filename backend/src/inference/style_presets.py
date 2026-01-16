"""Style presets for text-to-image generation.

These presets are optimized for generating images that work well
with the Hunyuan3D image-to-3D pipeline.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class StylePreset:
    """A style preset for text-to-image generation."""
    id: str
    name: str
    description: str
    prompt_prefix: str
    prompt_suffix: str
    negative_prompt: str
    # Optional overrides
    guidance_scale: Optional[float] = None
    steps: Optional[int] = None


# Default negative prompt for all game assets
DEFAULT_NEGATIVE = (
    "blurry, low quality, distorted, deformed, ugly, bad anatomy, "
    "watermark, text, logo, signature, multiple objects, busy background, "
    "cropped, cut off, out of frame"
)

# Style presets optimized for 3D generation
STYLE_PRESETS: dict[str, StylePreset] = {
    "game_asset": StylePreset(
        id="game_asset",
        name="Game Asset",
        description="General 3D game asset with clean background",
        prompt_prefix="3D game asset render, single object, centered, white background, ",
        prompt_suffix=", studio lighting, high detail, clean edges, professional product shot",
        negative_prompt=DEFAULT_NEGATIVE + ", environment, scene, multiple items",
    ),

    "character": StylePreset(
        id="character",
        name="Character",
        description="Full-body character suitable for rigging",
        prompt_prefix="3D character design, full body, T-pose or A-pose, neutral standing position, ",
        prompt_suffix=", front view, symmetrical, clean white background, game-ready character, high detail",
        negative_prompt=DEFAULT_NEGATIVE + ", sitting, action pose, partial body, cropped limbs",
    ),

    "prop": StylePreset(
        id="prop",
        name="Prop/Item",
        description="Game prop or inventory item",
        prompt_prefix="3D game prop, single item, centered, white background, ",
        prompt_suffix=", studio lighting, inventory icon style, clean render, high detail",
        negative_prompt=DEFAULT_NEGATIVE + ", hand holding, in use, environment",
    ),

    "creature": StylePreset(
        id="creature",
        name="Creature",
        description="Fantasy creature or monster",
        prompt_prefix="3D creature design, fantasy monster, full body, neutral pose, ",
        prompt_suffix=", white background, creature concept art, detailed, game-ready",
        negative_prompt=DEFAULT_NEGATIVE + ", action scene, environment, partial body",
    ),

    "vehicle": StylePreset(
        id="vehicle",
        name="Vehicle",
        description="Vehicle or transportation",
        prompt_prefix="3D vehicle render, side view, clean design, ",
        prompt_suffix=", white background, studio lighting, game asset style, detailed",
        negative_prompt=DEFAULT_NEGATIVE + ", motion blur, environment, road, action",
    ),

    "weapon": StylePreset(
        id="weapon",
        name="Weapon",
        description="Weapon or tool",
        prompt_prefix="3D weapon design, single weapon, centered, horizontal orientation, ",
        prompt_suffix=", white background, game inventory style, detailed, clean render",
        negative_prompt=DEFAULT_NEGATIVE + ", hand holding, in use, action, blood",
    ),

    "architecture": StylePreset(
        id="architecture",
        name="Building/Structure",
        description="Building or architectural element",
        prompt_prefix="3D building model, isometric view, architectural render, ",
        prompt_suffix=", clean white background, game asset style, detailed facade",
        negative_prompt=DEFAULT_NEGATIVE + ", interior, people, vehicles, environment",
    ),

    "nature": StylePreset(
        id="nature",
        name="Nature/Plant",
        description="Plant, tree, or natural element",
        prompt_prefix="3D plant asset, single plant or tree, centered, ",
        prompt_suffix=", white background, game foliage style, detailed leaves",
        negative_prompt=DEFAULT_NEGATIVE + ", forest, environment, multiple plants",
    ),

    "furniture": StylePreset(
        id="furniture",
        name="Furniture",
        description="Furniture or interior object",
        prompt_prefix="3D furniture render, single piece, centered, ",
        prompt_suffix=", white background, interior design style, clean render, detailed",
        negative_prompt=DEFAULT_NEGATIVE + ", room, interior scene, multiple items",
    ),

    "stylized": StylePreset(
        id="stylized",
        name="Stylized/Cartoon",
        description="Stylized or cartoon-style asset",
        prompt_prefix="3D stylized game asset, cartoon style, vibrant colors, ",
        prompt_suffix=", white background, mobile game style, clean design, cel shaded look",
        negative_prompt=DEFAULT_NEGATIVE + ", realistic, photorealistic, gritty",
        guidance_scale=8.0,  # Higher guidance for more stylized look
    ),
}


def get_preset(preset_id: str) -> StylePreset:
    """Get a style preset by ID.

    Args:
        preset_id: The preset identifier

    Returns:
        StylePreset or the default 'game_asset' preset if not found
    """
    return STYLE_PRESETS.get(preset_id, STYLE_PRESETS["game_asset"])


def build_prompt(user_prompt: str, preset_id: str = "game_asset") -> tuple[str, str]:
    """Build the full prompt and negative prompt from user input and preset.

    Args:
        user_prompt: The user's description of what to generate
        preset_id: The style preset to apply

    Returns:
        Tuple of (full_prompt, negative_prompt)
    """
    preset = get_preset(preset_id)

    # Build full prompt: prefix + user input + suffix
    full_prompt = f"{preset.prompt_prefix}{user_prompt}{preset.prompt_suffix}"

    return full_prompt, preset.negative_prompt


def get_all_presets() -> list[dict]:
    """Get all available presets as a list of dicts for API response."""
    return [
        {
            "id": preset.id,
            "name": preset.name,
            "description": preset.description,
        }
        for preset in STYLE_PRESETS.values()
    ]
