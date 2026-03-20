"""
Image preprocessing for OCR: deskew, denoise, binarization, contrast enhancement.

Prepares document images for optimal text extraction by Tesseract.
"""

from __future__ import annotations

import logging
from typing import Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocesses document images for OCR extraction."""

    def __init__(
        self,
        target_dpi: int = 300,
        denoise_strength: int = 10,
        binarize: bool = True,
        deskew: bool = True,
        enhance_contrast: bool = True,
    ):
        self.target_dpi = target_dpi
        self.denoise_strength = denoise_strength
        self.binarize = binarize
        self.deskew = deskew
        self.enhance_contrast = enhance_contrast

    def preprocess(self, image_path: str) -> np.ndarray:
        """
        Run the full preprocessing pipeline on an image.

        Args:
            image_path: Path to the input image.

        Returns:
            Preprocessed image as a NumPy array (grayscale).
        """
        logger.debug("Loading image: %s", image_path)
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Step 1: Denoise
        gray = self._denoise(gray)

        # Step 2: Deskew
        if self.deskew:
            gray = self._deskew(gray)

        # Step 3: Contrast enhancement
        if self.enhance_contrast:
            gray = self._enhance_contrast(gray)

        # Step 4: Binarization
        if self.binarize:
            gray = self._binarize(gray)

        return gray

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """Apply non-local means denoising."""
        logger.debug("Applying denoising (strength=%d)", self.denoise_strength)
        return cv2.fastNlMeansDenoising(image, h=self.denoise_strength)

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Detect and correct document skew angle."""
        coords = np.column_stack(np.where(image > 0))
        if len(coords) < 10:
            logger.debug("Not enough points for deskew, skipping")
            return image

        angle = cv2.minAreaRect(coords)[-1]

        # Normalize angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.5:
            logger.debug("Skew angle %.2f is negligible, skipping rotation", angle)
            return image

        logger.debug("Correcting skew: %.2f degrees", angle)
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        logger.debug("Enhancing contrast with CLAHE")
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)

    def _binarize(self, image: np.ndarray) -> np.ndarray:
        """Apply adaptive thresholding for binarization."""
        logger.debug("Applying adaptive binarization")
        return cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2,
        )

    @staticmethod
    def load_pil_image(image_path: str) -> Image.Image:
        """Load an image as a PIL Image object."""
        return Image.open(image_path)
