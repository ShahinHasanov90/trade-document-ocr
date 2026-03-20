"""
Document type classifier for trade documents.

Classifies documents into: bill of lading, commercial invoice,
certificate of origin, or packing list using keyword scoring.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from .schemas import DocumentType

logger = logging.getLogger(__name__)

DEFAULT_RULES_PATH = Path(__file__).parent.parent.parent / "config" / "extraction_rules.yaml"

# Default keyword weights for classification
DEFAULT_KEYWORDS: dict[DocumentType, list[tuple[str, float]]] = {
    DocumentType.BILL_OF_LADING: [
        ("bill of lading", 5.0),
        ("b/l", 4.0),
        ("shipper", 2.0),
        ("consignee", 2.0),
        ("vessel", 3.0),
        ("port of loading", 3.0),
        ("port of discharge", 3.0),
        ("carrier", 2.0),
        ("container", 2.0),
        ("freight", 2.0),
        ("notify party", 2.0),
        ("on board", 1.5),
    ],
    DocumentType.COMMERCIAL_INVOICE: [
        ("commercial invoice", 5.0),
        ("invoice", 4.0),
        ("invoice no", 3.0),
        ("invoice number", 3.0),
        ("seller", 2.0),
        ("buyer", 2.0),
        ("unit price", 3.0),
        ("total amount", 3.0),
        ("payment terms", 2.0),
        ("incoterms", 2.0),
        ("quantity", 1.5),
        ("description of goods", 2.0),
    ],
    DocumentType.CERTIFICATE_OF_ORIGIN: [
        ("certificate of origin", 5.0),
        ("origin", 2.0),
        ("country of origin", 4.0),
        ("certif", 2.0),
        ("chamber of commerce", 3.0),
        ("manufacturer", 2.0),
        ("producer", 2.0),
        ("hereby certif", 3.0),
        ("preferential", 2.0),
        ("tariff", 1.5),
    ],
    DocumentType.PACKING_LIST: [
        ("packing list", 5.0),
        ("packing", 2.0),
        ("gross weight", 3.0),
        ("net weight", 3.0),
        ("carton", 2.0),
        ("package", 2.0),
        ("dimensions", 2.0),
        ("marks and numbers", 3.0),
        ("measurement", 2.0),
        ("pieces", 1.5),
        ("cbm", 2.0),
    ],
}


class DocumentClassifier:
    """Classifies trade document type based on keyword scoring."""

    def __init__(
        self,
        rules_path: Optional[str] = None,
        keywords: Optional[dict[DocumentType, list[tuple[str, float]]]] = None,
    ):
        """
        Initialize the classifier.

        Args:
            rules_path: Path to extraction rules YAML (for additional keywords).
            keywords: Custom keyword weights. Uses defaults if None.
        """
        self.keywords = keywords or DEFAULT_KEYWORDS.copy()

        # Load additional keywords from YAML if available
        if rules_path:
            self._load_yaml_keywords(Path(rules_path))
        elif DEFAULT_RULES_PATH.exists():
            self._load_yaml_keywords(DEFAULT_RULES_PATH)

    def _load_yaml_keywords(self, rules_path: Path) -> None:
        """Load additional classification keywords from YAML config."""
        try:
            with open(rules_path, "r", encoding="utf-8") as f:
                rules = yaml.safe_load(f) or {}

            classification = rules.get("classification", {})
            for type_key, config in classification.items():
                try:
                    doc_type = DocumentType(type_key)
                except ValueError:
                    continue

                extra_keywords = config.get("keywords", [])
                weight = config.get("default_weight", 2.0)
                existing = self.keywords.get(doc_type, [])
                for kw in extra_keywords:
                    if isinstance(kw, dict):
                        existing.append((kw["term"], kw.get("weight", weight)))
                    else:
                        existing.append((kw, weight))
                self.keywords[doc_type] = existing

        except Exception as exc:
            logger.warning("Could not load classification keywords: %s", exc)

    def classify(self, text: str) -> tuple[DocumentType, float]:
        """
        Classify document type from OCR text.

        Args:
            text: Raw OCR text content.

        Returns:
            Tuple of (DocumentType, confidence_score).
            Confidence is normalized between 0.0 and 1.0.
        """
        text_lower = text.lower()
        scores: dict[DocumentType, float] = {}

        for doc_type, keywords in self.keywords.items():
            score = 0.0
            for keyword, weight in keywords:
                if keyword.lower() in text_lower:
                    score += weight
            scores[doc_type] = score

        if not scores or max(scores.values()) == 0:
            return DocumentType.UNKNOWN, 0.0

        best_type = max(scores, key=scores.get)  # type: ignore[arg-type]
        best_score = scores[best_type]
        total_score = sum(scores.values())

        confidence = best_score / total_score if total_score > 0 else 0.0

        logger.debug(
            "Classification scores: %s -> %s (confidence=%.2f)",
            {k.value: f"{v:.1f}" for k, v in scores.items()},
            best_type.value,
            confidence,
        )

        return best_type, round(confidence, 3)

    def get_scores(self, text: str) -> dict[str, float]:
        """
        Get classification scores for all document types.

        Args:
            text: Raw OCR text content.

        Returns:
            Dictionary of document type name -> score.
        """
        text_lower = text.lower()
        scores = {}
        for doc_type, keywords in self.keywords.items():
            score = 0.0
            for keyword, weight in keywords:
                if keyword.lower() in text_lower:
                    score += weight
            scores[doc_type.value] = round(score, 2)
        return scores
