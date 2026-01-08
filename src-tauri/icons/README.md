# Sweedle App Icons

This directory should contain the application icons in various sizes for different platforms.

## Required Icon Files

For a complete Tauri build, you need the following icons:

### Windows
- `icon.ico` - Multi-resolution ICO file (16x16, 32x32, 48x48, 256x256)

### macOS
- `icon.icns` - macOS icon bundle

### Linux / General
- `32x32.png` - 32x32 pixels
- `128x128.png` - 128x128 pixels
- `128x128@2x.png` - 256x256 pixels (for HiDPI displays)

### Source
- `icon.svg` - Vector source file (included)

## Generating Icons

### Option 1: Using Tauri Icon Generator

The easiest way is to use Tauri's built-in icon generator:

```bash
cd src-tauri
cargo tauri icon ../frontend/public/favicon.svg
```

This will generate all required icon sizes from the SVG.

### Option 2: Online Tools

1. Go to https://tauri.app/guides/icons/
2. Upload your SVG or PNG (at least 1024x1024)
3. Download the generated icon pack
4. Extract to this `icons/` directory

### Option 3: Manual Generation

Use ImageMagick or similar tools:

```bash
# Install ImageMagick if needed
# Convert SVG to PNG at various sizes
convert icon.svg -resize 32x32 32x32.png
convert icon.svg -resize 128x128 128x128.png
convert icon.svg -resize 256x256 128x128@2x.png

# Create ICO for Windows (requires multiple sizes)
convert icon.svg -resize 256x256 icon.ico

# Create ICNS for macOS (requires iconutil on macOS)
# See: https://developer.apple.com/documentation/xcode/creating-a-mac-app-icon
```

## Current Status

- [x] `icon.svg` - Source vector file (copied from frontend favicon)
- [ ] `32x32.png` - Generate before production build
- [ ] `128x128.png` - Generate before production build
- [ ] `128x128@2x.png` - Generate before production build
- [ ] `icon.ico` - Generate before production build
- [ ] `icon.icns` - Generate before production build (macOS only)

## Note

The Tauri build will work without these icons (using defaults), but for a polished production release, you should generate all icon sizes.
