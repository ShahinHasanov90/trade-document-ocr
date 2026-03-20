"""
Text extraction wrapper using Tesseract OCR.

Handles OCR configuration, language selection, and raw text extraction
from preprocessed document images.
"""

from __future__ import annotations

import logging
from typing import Optional, Union

import numpy as np
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

# Language code mapping for convenience
LANGUAGE_MAP = {
    "en": "eng",
    "ru": "rus",
    "az": "aze",
    "eng": "eng",
    "rus": "rus",
    "aze": "aze",
}


class TextExtractor:
    """Extracts text from preprocessed images using Tesseract OCR."""

    def __init__(
        self,
        lang: str = "eng",
        psm: int = 3,
        oem: int = 3,
        tesseract_cmd: Optional[str] = None,
    ):
        """
        Initialize the text extractor.

        Args:
            lang: Tesseract language code (e.g., 'eng', 'rus', 'aze', 'eng+rus+aze').
            psm: Page segmentation mode (3 = fully automatic).
            oem: OCR engine mode (3 = default, LSTM + legacy).
            tesseract_cmd: Custom path to tesseract binary, if needed.
        """
        self.lang = self._normalize_lang(lang)
        self.psm = psm
        self.oem = oem

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    @staticmethod
    def _normalize_lang(lang: str) -> str:
        """Normalize language code to Tesseract format."""
        parts = lang.split("+")
        normalized = []
        for part in parts:
            part = part.strip().lower()
            normalized.append(LANGUAGE_MAP.get(part, part))
        return "+".join(normalized)

    def _build_config(self, psm: Optional[int] = None) -> str:
        """Build Tesseract configuration string."""
        page_seg = psm if psm is not None else self.psm
        return f"--oem {self.oem} --psm {page_seg}"

    def extract_text(
        self,
        image: Union[np.ndarray, Image.Image, str],
        psm: Optional[int] = None,
    ) -> str:
        """
        Extract text from an image.

        Args:
            image: Preprocessed image as NumPy array, PIL Image, or file path.
            psm: Override page segmentation mode for this call.

        Returns:
            Extracted raw text string.
        """
        config = self._build_config(psm)

        if isinstance(image, str):
            image = Image.open(image)
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        logger.debug("Running Tesseract OCR (lang=%s, config=%s)", self.lang, config)
        text = pytesseract.image_to_string(image, lang=self.lang, config=config)

        logger.debug("Extracted %d characters", len(text))
        return text

    def extract_with_confidence(
        self,
        image: Union[np.ndarray, Image.Image, str],
        psm: Optional[int] = None,
    ) -> list[dict]:
        """
        Extract text with per-word confidence scores.

        Args:
            image: Preprocessed image as NumPy array, PIL Image, or file path.
            psm: Override page segmentation mode for this call.

        Returns:
            List of dicts with keys: text, confidence, left, top, width, height.
        """
        config = self._build_config(psm)

        if isinstance(image, str):
            image = Image.open(image)
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image)

        data = pytesseract.image_to_data(
            image, lang=self.lang, config=config, output_type=pytesseract.Output.DICT
        )

        results = []
        n_boxes = len(data["text"])
        for i in range(n_boxes):
            word = data["text"][i].strip()
            if not word:
                continue
            results.append(
                {
                    "text": word,
                    "confidence": int(data["conf"][i]),
                    "left": data["left"][i],
                    "top": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i],
                }
            )

        return results

    def get_available_languages(self) -> list[str]:
        """Return list of available Tesseract languages."""
        return pytesseract.get_languages()
