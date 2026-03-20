"""
Main OCR pipeline: image preprocessing -> text extraction -> field parsing -> structured output.

Orchestrates the full document processing workflow from raw image to validated
structured JSON.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

from .preprocessor import ImagePreprocessor
from .extractor import TextExtractor
from .parser import DocumentFieldParser
from .document_classifier import DocumentClassifier
from .field_validator import FieldValidator
from .schemas import ExtractionResult, DocumentType

logger = logging.getLogger(__name__)


class OCRPipeline:
    """End-to-end OCR pipeline for trade document processing."""

    def __init__(
        self,
        lang: str = "eng",
        rules_path: Optional[str] = None,
        validate: bool = True,
    ):
        """
        Initialize the OCR pipeline.

        Args:
            lang: Tesseract language code (eng, rus, aze, or combined like eng+rus+aze).
            rules_path: Path to extraction_rules.yaml. Uses default if None.
            validate: Whether to run field validation on extracted data.
        """
        self.lang = lang
        self.validate = validate

        self.preprocessor = ImagePreprocessor()
        self.extractor = TextExtractor(lang=lang)
        self.classifier = DocumentClassifier(rules_path=rules_path)
        self.parser = DocumentFieldParser(rules_path=rules_path)
        self.validator = FieldValidator()

    def process(
        self,
        image_path: Union[str, Path],
        document_type: Optional[DocumentType] = None,
    ) -> ExtractionResult:
        """
        Run the full OCR pipeline on a single document image.

        Args:
            image_path: Path to the document image file.
            document_type: If provided, skip classification and use this type.

        Returns:
            ExtractionResult with extracted and optionally validated fields.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.info("Processing document: %s", image_path.name)

        # Step 1: Image preprocessing
        logger.debug("Step 1: Preprocessing image")
        processed_image = self.preprocessor.preprocess(str(image_path))

        # Step 2: Text extraction via OCR
        logger.debug("Step 2: Extracting text")
        raw_text = self.extractor.extract_text(processed_image)

        if not raw_text.strip():
            logger.warning("No text extracted from %s", image_path.name)
            return ExtractionResult(
                source_file=str(image_path),
                document_type=DocumentType.UNKNOWN,
                raw_text="",
                fields={},
                confidence=0.0,
                validation_errors=["No text could be extracted from the image."],
            )

        # Step 3: Document classification
        if document_type is None:
            logger.debug("Step 3: Classifying document")
            doc_type, classification_confidence = self.classifier.classify(raw_text)
        else:
            doc_type = document_type
            classification_confidence = 1.0

        # Step 4: Field parsing
        logger.debug("Step 4: Parsing fields")
        fields = self.parser.parse(raw_text, doc_type)

        # Step 5: Field validation
        validation_errors = []
        if self.validate:
            logger.debug("Step 5: Validating fields")
            validation_errors = self.validator.validate(fields, doc_type)

        result = ExtractionResult(
            source_file=str(image_path),
            document_type=doc_type,
            raw_text=raw_text,
            fields=fields,
            confidence=classification_confidence,
            validation_errors=validation_errors,
        )

        logger.info(
            "Extraction complete: type=%s, fields=%d, errors=%d",
            doc_type.value,
            len(fields),
            len(validation_errors),
        )

        return result

    def process_batch(
        self,
        image_paths: list[Union[str, Path]],
        document_type: Optional[DocumentType] = None,
    ) -> list[ExtractionResult]:
        """
        Process multiple document images sequentially.

        Args:
            image_paths: List of paths to document image files.
            document_type: If provided, apply to all documents.

        Returns:
            List of ExtractionResult objects.
        """
        results = []
        for path in image_paths:
            try:
                result = self.process(path, document_type=document_type)
                results.append(result)
            except Exception as exc:
                logger.error("Failed to process %s: %s", path, exc)
                results.append(
                    ExtractionResult(
                        source_file=str(path),
                        document_type=DocumentType.UNKNOWN,
                        raw_text="",
                        fields={},
                        confidence=0.0,
                        validation_errors=[f"Processing failed: {exc}"],
                    )
                )
        return results
