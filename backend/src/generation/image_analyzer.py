"""
Image Quality Analyzer for 3D Generation Suitability

Analyzes uploaded images and provides feedback on their suitability
for 3D mesh generation based on research from Hunyuan3D documentation
and community best practices.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class QualityCheck:
    """Individual quality check result."""
    name: str
    passed: bool
    score: float  # 0.0 to 1.0
    message: str
    suggestion: Optional[str] = None


@dataclass
class ImageAnalysisResult:
    """Complete image analysis result."""
    overall_score: float  # 0.0 to 1.0
    quality_level: str  # "excellent", "good", "fair", "poor"
    checks: List[QualityCheck] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    tips: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "quality_level": self.quality_level,
            "checks": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "score": c.score,
                    "message": c.message,
                    "suggestion": c.suggestion,
                }
                for c in self.checks
            ],
            "warnings": self.warnings,
            "tips": self.tips,
        }


class ImageAnalyzer:
    """
    Analyzes images for 3D generation suitability.

    Based on Hunyuan3D documentation and community best practices:
    - Transparent/simple backgrounds work best
    - Centered subjects produce better results
    - Clear, well-lit images are preferred
    - 1024x1024 is optimal resolution
    - Single, distinct subjects work better than complex scenes
    """

    # Optimal resolution for Hunyuan3D
    OPTIMAL_SIZE = 1024
    MIN_SIZE = 256

    def analyze(self, image: Image.Image) -> ImageAnalysisResult:
        """
        Analyze an image for 3D generation suitability.

        Args:
            image: PIL Image to analyze

        Returns:
            ImageAnalysisResult with scores and feedback
        """
        checks = []
        warnings = []
        tips = []

        # Convert to RGBA for analysis if needed
        if image.mode != 'RGBA':
            rgba_image = image.convert('RGBA')
        else:
            rgba_image = image

        img_array = np.array(rgba_image)

        # 1. Check resolution
        checks.append(self._check_resolution(image))

        # 2. Check aspect ratio
        checks.append(self._check_aspect_ratio(image))

        # 3. Check for transparency/background
        bg_check = self._check_background(img_array)
        checks.append(bg_check)

        # 4. Check subject centering
        center_check = self._check_centering(img_array)
        checks.append(center_check)

        # 5. Check image clarity/sharpness
        checks.append(self._check_sharpness(img_array))

        # 6. Check subject coverage (not too small, not too large)
        checks.append(self._check_subject_coverage(img_array))

        # 7. Check contrast/lighting
        checks.append(self._check_contrast(img_array))

        # Calculate overall score (weighted average)
        weights = {
            "resolution": 0.10,
            "aspect_ratio": 0.05,
            "background": 0.25,
            "centering": 0.20,
            "sharpness": 0.15,
            "coverage": 0.15,
            "contrast": 0.10,
        }

        total_weight = sum(weights.values())
        weighted_score = sum(
            c.score * weights.get(c.name, 0.1)
            for c in checks
        ) / total_weight

        # Determine quality level
        if weighted_score >= 0.85:
            quality_level = "excellent"
        elif weighted_score >= 0.70:
            quality_level = "good"
        elif weighted_score >= 0.50:
            quality_level = "fair"
        else:
            quality_level = "poor"

        # Add warnings for failed checks
        for check in checks:
            if not check.passed and check.suggestion:
                warnings.append(check.suggestion)

        # Add general tips based on analysis
        if not bg_check.passed:
            tips.append("Use an image with transparent background (PNG) for best results")

        if weighted_score < 0.70:
            tips.append("Consider using a front-facing view of the subject")
            tips.append("Ensure the subject is well-lit with minimal shadows")

        if quality_level == "excellent":
            tips.append("This image looks great for 3D generation!")

        return ImageAnalysisResult(
            overall_score=weighted_score,
            quality_level=quality_level,
            checks=checks,
            warnings=warnings,
            tips=tips,
        )

    def _check_resolution(self, image: Image.Image) -> QualityCheck:
        """Check if image resolution is suitable."""
        width, height = image.size
        min_dim = min(width, height)
        max_dim = max(width, height)

        if min_dim >= self.OPTIMAL_SIZE:
            score = 1.0
            passed = True
            message = f"Resolution {width}x{height} is optimal"
            suggestion = None
        elif min_dim >= 512:
            score = 0.8
            passed = True
            message = f"Resolution {width}x{height} is good"
            suggestion = None
        elif min_dim >= self.MIN_SIZE:
            score = 0.5
            passed = True
            message = f"Resolution {width}x{height} is acceptable but may affect quality"
            suggestion = "Consider using a higher resolution image (1024x1024 recommended)"
        else:
            score = 0.2
            passed = False
            message = f"Resolution {width}x{height} is too low"
            suggestion = "Image resolution is too low. Use at least 512x512, preferably 1024x1024"

        return QualityCheck(
            name="resolution",
            passed=passed,
            score=score,
            message=message,
            suggestion=suggestion,
        )

    def _check_aspect_ratio(self, image: Image.Image) -> QualityCheck:
        """Check if aspect ratio is close to square."""
        width, height = image.size
        ratio = max(width, height) / min(width, height)

        if ratio <= 1.2:
            score = 1.0
            passed = True
            message = "Aspect ratio is optimal (near square)"
            suggestion = None
        elif ratio <= 1.5:
            score = 0.7
            passed = True
            message = "Aspect ratio is acceptable"
            suggestion = None
        else:
            score = 0.4
            passed = False
            message = f"Aspect ratio {ratio:.1f}:1 is not ideal"
            suggestion = "Consider cropping to a square aspect ratio for best results"

        return QualityCheck(
            name="aspect_ratio",
            passed=passed,
            score=score,
            message=message,
            suggestion=suggestion,
        )

    def _check_background(self, img_array: np.ndarray) -> QualityCheck:
        """Check for transparent or simple background."""
        if img_array.shape[2] == 4:
            # Has alpha channel
            alpha = img_array[:, :, 3]
            transparent_ratio = np.sum(alpha < 128) / alpha.size

            if transparent_ratio > 0.3:
                score = 1.0
                passed = True
                message = f"Image has transparent background ({transparent_ratio*100:.0f}% transparent)"
                suggestion = None
            elif transparent_ratio > 0.1:
                score = 0.7
                passed = True
                message = "Image has some transparency"
                suggestion = None
            else:
                # Check for solid/simple background
                score, passed, message, suggestion = self._analyze_background_complexity(img_array)
        else:
            # No alpha, check background complexity
            score, passed, message, suggestion = self._analyze_background_complexity(img_array)

        return QualityCheck(
            name="background",
            passed=passed,
            score=score,
            message=message,
            suggestion=suggestion,
        )

    def _analyze_background_complexity(self, img_array: np.ndarray) -> Tuple[float, bool, str, Optional[str]]:
        """Analyze background complexity for non-transparent images."""
        # Sample edges of image to estimate background
        rgb = img_array[:, :, :3]
        h, w = rgb.shape[:2]

        # Sample border pixels (top/bottom rows, left/right columns)
        border_size = max(1, min(h, w) // 20)

        top = rgb[:border_size, :, :].reshape(-1, 3)
        bottom = rgb[-border_size:, :, :].reshape(-1, 3)
        left = rgb[:, :border_size, :].reshape(-1, 3)
        right = rgb[:, -border_size:, :].reshape(-1, 3)

        border_pixels = np.vstack([top, bottom, left, right])

        # Calculate color variance in border region
        color_std = np.std(border_pixels, axis=0).mean()

        if color_std < 15:
            return (0.8, True, "Background appears to be solid color", None)
        elif color_std < 40:
            return (0.6, True, "Background is relatively simple",
                    "Consider using transparent PNG for better results")
        else:
            return (0.3, False, "Background appears complex",
                    "Use an image with transparent or solid-color background for best results")

    def _check_centering(self, img_array: np.ndarray) -> QualityCheck:
        """Check if subject is centered in the image."""
        if img_array.shape[2] == 4:
            # Use alpha channel to find subject
            alpha = img_array[:, :, 3]
            mask = alpha > 128
        else:
            # Use edge detection to estimate subject location
            gray = np.mean(img_array[:, :, :3], axis=2)
            # Simple edge detection via gradient
            gy, gx = np.gradient(gray)
            edges = np.sqrt(gx**2 + gy**2)
            mask = edges > np.percentile(edges, 75)

        if not np.any(mask):
            return QualityCheck(
                name="centering",
                passed=True,
                score=0.5,
                message="Could not determine subject location",
                suggestion=None,
            )

        # Find center of mass of subject
        y_indices, x_indices = np.where(mask)
        center_y = np.mean(y_indices)
        center_x = np.mean(x_indices)

        h, w = img_array.shape[:2]
        img_center_y, img_center_x = h / 2, w / 2

        # Calculate offset from center (normalized)
        offset_x = abs(center_x - img_center_x) / (w / 2)
        offset_y = abs(center_y - img_center_y) / (h / 2)
        max_offset = max(offset_x, offset_y)

        if max_offset < 0.15:
            score = 1.0
            passed = True
            message = "Subject is well-centered"
            suggestion = None
        elif max_offset < 0.3:
            score = 0.7
            passed = True
            message = "Subject is reasonably centered"
            suggestion = None
        else:
            score = 0.4
            passed = False
            message = "Subject is off-center"
            suggestion = "Center the subject in the image for better 3D reconstruction"

        return QualityCheck(
            name="centering",
            passed=passed,
            score=score,
            message=message,
            suggestion=suggestion,
        )

    def _check_sharpness(self, img_array: np.ndarray) -> QualityCheck:
        """Check image sharpness/clarity using Laplacian variance."""
        gray = np.mean(img_array[:, :, :3], axis=2)

        # Laplacian kernel for edge detection
        # Simple approximation: variance of gradient
        gy, gx = np.gradient(gray)
        laplacian_var = np.var(gx) + np.var(gy)

        # Normalize - these thresholds are empirical
        if laplacian_var > 500:
            score = 1.0
            passed = True
            message = "Image is sharp and clear"
            suggestion = None
        elif laplacian_var > 200:
            score = 0.7
            passed = True
            message = "Image clarity is acceptable"
            suggestion = None
        elif laplacian_var > 50:
            score = 0.4
            passed = False
            message = "Image appears slightly blurry"
            suggestion = "Use a sharper, clearer image for better detail in the 3D model"
        else:
            score = 0.2
            passed = False
            message = "Image is too blurry"
            suggestion = "Image is blurry. Use a clear, in-focus photo for best results"

        return QualityCheck(
            name="sharpness",
            passed=passed,
            score=score,
            message=message,
            suggestion=suggestion,
        )

    def _check_subject_coverage(self, img_array: np.ndarray) -> QualityCheck:
        """Check that subject fills appropriate portion of frame."""
        if img_array.shape[2] == 4:
            alpha = img_array[:, :, 3]
            subject_ratio = np.sum(alpha > 128) / alpha.size
        else:
            # Estimate using non-background pixels
            gray = np.mean(img_array[:, :, :3], axis=2)
            # Assume background is near edges
            border = 10
            bg_color = np.median(np.concatenate([
                gray[:border, :].flatten(),
                gray[-border:, :].flatten(),
                gray[:, :border].flatten(),
                gray[:, -border:].flatten(),
            ]))
            subject_mask = np.abs(gray - bg_color) > 30
            subject_ratio = np.sum(subject_mask) / subject_mask.size

        if 0.15 <= subject_ratio <= 0.85:
            score = 1.0
            passed = True
            message = f"Subject fills {subject_ratio*100:.0f}% of frame - good coverage"
            suggestion = None
        elif 0.05 <= subject_ratio < 0.15:
            score = 0.5
            passed = False
            message = f"Subject is small ({subject_ratio*100:.0f}% of frame)"
            suggestion = "Consider cropping closer to the subject for better detail"
        elif subject_ratio > 0.85:
            score = 0.6
            passed = True
            message = f"Subject fills most of frame ({subject_ratio*100:.0f}%)"
            suggestion = "Subject may be cropped. Consider adding some margin around it"
        else:
            score = 0.3
            passed = False
            message = "Could not detect clear subject in image"
            suggestion = "Ensure the subject is visible and distinct from the background"

        return QualityCheck(
            name="coverage",
            passed=passed,
            score=score,
            message=message,
            suggestion=suggestion,
        )

    def _check_contrast(self, img_array: np.ndarray) -> QualityCheck:
        """Check image contrast and lighting."""
        gray = np.mean(img_array[:, :, :3], axis=2)

        # Check dynamic range
        p5, p95 = np.percentile(gray, [5, 95])
        dynamic_range = p95 - p5

        # Check overall brightness
        mean_brightness = np.mean(gray)

        contrast_ok = dynamic_range > 80
        brightness_ok = 40 < mean_brightness < 220

        if contrast_ok and brightness_ok:
            score = 1.0
            passed = True
            message = "Good contrast and lighting"
            suggestion = None
        elif contrast_ok:
            score = 0.7
            passed = True
            if mean_brightness <= 40:
                message = "Image is quite dark but has good contrast"
                suggestion = "Consider brightening the image slightly"
            else:
                message = "Image is very bright but has good contrast"
                suggestion = "Image may be overexposed"
        elif brightness_ok:
            score = 0.5
            passed = False
            message = "Low contrast - details may be lost"
            suggestion = "Increase image contrast for better 3D detail extraction"
        else:
            score = 0.3
            passed = False
            message = "Poor lighting and contrast"
            suggestion = "Use a well-lit image with good contrast for best results"

        return QualityCheck(
            name="contrast",
            passed=passed,
            score=score,
            message=message,
            suggestion=suggestion,
        )


# Global analyzer instance
_analyzer: Optional[ImageAnalyzer] = None


def get_analyzer() -> ImageAnalyzer:
    """Get or create the global analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = ImageAnalyzer()
    return _analyzer


def analyze_image(image: Image.Image) -> ImageAnalysisResult:
    """Analyze an image for 3D generation suitability."""
    return get_analyzer().analyze(image)
