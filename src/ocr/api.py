"""
FastAPI application for Trade Document OCR.

Endpoints:
    POST /extract       -- Extract fields from a single uploaded image
    POST /extract/batch -- Batch extraction from multiple images
    POST /classify      -- Classify document type
    GET  /health        -- Service health check
"""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse

from .pipeline import OCRPipeline
from .document_classifier import DocumentClassifier
from .schemas import (
    DocumentType,
    ExtractionResult,
    ClassificationResult,
    HealthResponse,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Trade Document OCR",
    description="OCR and structured field extraction for customs trade documents.",
    version="0.1.0",
)

# Global pipeline instance (initialized on first request or startup)
_pipeline: Optional[OCRPipeline] = None


def get_pipeline() -> OCRPipeline:
    """Get or create the global OCR pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = OCRPipeline(lang="eng+rus+aze")
    return _pipeline


def _save_upload_to_temp(upload: UploadFile) -> Path:
    """Save an uploaded file to a temporary path."""
    suffix = Path(upload.filename or "image.png").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(upload.file, tmp)
        return Path(tmp.name)


@app.post("/extract", response_model=ExtractionResult)
async def extract_fields(
    file: UploadFile = File(..., description="Document image to process."),
    document_type: Optional[str] = Query(
        None,
        description="Force document type (bill_of_lading, commercial_invoice, certificate_of_origin, packing_list).",
    ),
    lang: Optional[str] = Query(None, description="OCR language code (e.g., eng, rus, aze, eng+rus)."),
):
    """Extract structured fields from a single document image."""
    tmp_path = None
    try:
        tmp_path = _save_upload_to_temp(file)

        pipeline = get_pipeline()
        if lang:
            pipeline.extractor.lang = pipeline.extractor._normalize_lang(lang)

        doc_type = None
        if document_type:
            try:
                doc_type = DocumentType(document_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document_type '{document_type}'. "
                    f"Valid values: {[dt.value for dt in DocumentType if dt != DocumentType.UNKNOWN]}",
                )

        result = pipeline.process(tmp_path, document_type=doc_type)
        return result

    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Extraction failed")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {exc}")
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


@app.post("/extract/batch", response_model=list[ExtractionResult])
async def extract_batch(
    files: list[UploadFile] = File(..., description="List of document images to process."),
    document_type: Optional[str] = Query(None, description="Force document type for all files."),
):
    """Extract structured fields from multiple document images."""
    tmp_paths = []
    try:
        for upload_file in files:
            tmp_paths.append(_save_upload_to_temp(upload_file))

        pipeline = get_pipeline()

        doc_type = None
        if document_type:
            try:
                doc_type = DocumentType(document_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid document_type '{document_type}'.",
                )

        results = pipeline.process_batch(tmp_paths, document_type=doc_type)
        return results

    except Exception as exc:
        logger.exception("Batch extraction failed")
        raise HTTPException(status_code=500, detail=f"Batch extraction failed: {exc}")
    finally:
        for tmp_path in tmp_paths:
            if tmp_path.exists():
                tmp_path.unlink()


@app.post("/classify", response_model=ClassificationResult)
async def classify_document(
    file: UploadFile = File(..., description="Document image to classify."),
):
    """Classify the type of a trade document image."""
    tmp_path = None
    try:
        tmp_path = _save_upload_to_temp(file)

        pipeline = get_pipeline()

        # Preprocess and extract text
        processed_image = pipeline.preprocessor.preprocess(str(tmp_path))
        raw_text = pipeline.extractor.extract_text(processed_image)

        if not raw_text.strip():
            return ClassificationResult(
                document_type=DocumentType.UNKNOWN,
                confidence=0.0,
                scores={},
            )

        doc_type, confidence = pipeline.classifier.classify(raw_text)
        scores = pipeline.classifier.get_scores(raw_text)

        return ClassificationResult(
            document_type=doc_type,
            confidence=confidence,
            scores=scores,
        )

    except Exception as exc:
        logger.exception("Classification failed")
        raise HTTPException(status_code=500, detail=f"Classification failed: {exc}")
    finally:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and Tesseract availability."""
    tesseract_ok = False
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        tesseract_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        version="0.1.0",
        tesseract_available=tesseract_ok,
    )
