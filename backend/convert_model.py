"""Convert Hunyuan3D .ckpt model to .safetensors format."""

import torch
from safetensors.torch import save_file
from pathlib import Path

def convert_ckpt_to_safetensors():
    # Paths
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub" / "models--tencent--Hunyuan3D-2.1"
    snapshot_dir = list((cache_dir / "snapshots").iterdir())[0]  # Get first snapshot

    model_dir = snapshot_dir / "hunyuan3d-dit-v2-1"
    ckpt_path = model_dir / "model.fp16.ckpt"
    safetensors_path = model_dir / "model.fp16.safetensors"

    print(f"Looking for: {ckpt_path}")

    if not ckpt_path.exists():
        print(f"ERROR: {ckpt_path} not found!")
        return False

    if safetensors_path.exists():
        print(f"Safetensors file already exists: {safetensors_path}")
        return True

    print(f"Loading checkpoint from {ckpt_path}...")
    checkpoint = torch.load(ckpt_path, map_location="cpu")

    # Handle different checkpoint formats
    if isinstance(checkpoint, dict):
        if "state_dict" in checkpoint:
            state_dict = checkpoint["state_dict"]
        elif "model" in checkpoint:
            state_dict = checkpoint["model"]
        else:
            state_dict = checkpoint
    else:
        state_dict = checkpoint

    print(f"Converting to safetensors format...")
    print(f"Found {len(state_dict)} tensors")

    # Save as safetensors
    save_file(state_dict, str(safetensors_path))
    print(f"Saved to {safetensors_path}")

    # Also convert VAE if exists
    vae_dir = snapshot_dir / "hunyuan3d-vae-v2-1"
    vae_ckpt = vae_dir / "model.fp16.ckpt"
    vae_safetensors = vae_dir / "model.fp16.safetensors"

    if vae_ckpt.exists() and not vae_safetensors.exists():
        print(f"\nConverting VAE model...")
        vae_checkpoint = torch.load(vae_ckpt, map_location="cpu")
        if isinstance(vae_checkpoint, dict):
            if "state_dict" in vae_checkpoint:
                vae_state = vae_checkpoint["state_dict"]
            elif "model" in vae_checkpoint:
                vae_state = vae_checkpoint["model"]
            else:
                vae_state = vae_checkpoint
        else:
            vae_state = vae_checkpoint
        save_file(vae_state, str(vae_safetensors))
        print(f"Saved VAE to {vae_safetensors}")

    return True

if __name__ == "__main__":
    success = convert_ckpt_to_safetensors()
    if success:
        print("\nConversion complete! Restart the backend now.")
    else:
        print("\nConversion failed!")
