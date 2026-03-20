"""Tests for the document type classifier."""

import pytest

from src.ocr.document_classifier import DocumentClassifier
from src.ocr.schemas import DocumentType


@pytest.fixture
def classifier():
    """Create a classifier instance without YAML rules."""
    return DocumentClassifier(rules_path=None, keywords=None)


class TestDocumentClassification:

    def test_classify_commercial_invoice(self, classifier):
        text = """
        COMMERCIAL INVOICE
        Invoice No: INV-2023-001
        Seller: ABC Trading Co.
        Buyer: XYZ Import LLC
        Description of Goods: Electronics
        Unit Price: $500.00
        Total Amount: $5,000.00
        Payment Terms: T/T 30 days
        """
        doc_type, confidence = classifier.classify(text)
        assert doc_type == DocumentType.COMMERCIAL_INVOICE
        assert confidence > 0.3

    def test_classify_bill_of_lading(self, classifier):
        text = """
        BILL OF LADING
        Shipper: Global Exports Ltd.
        Consignee: Local Imports Inc.
        Vessel: MSC OSCAR
        Port of Loading: Shanghai
        Port of Discharge: Rotterdam
        Container: MSKU1234567
        Freight: Prepaid
        Notify Party: Agent Co.
        """
        doc_type, confidence = classifier.classify(text)
        assert doc_type == DocumentType.BILL_OF_LADING
        assert confidence > 0.3

    def test_classify_certificate_of_origin(self, classifier):
        text = """
        CERTIFICATE OF ORIGIN
        Country of Origin: Azerbaijan
        Manufacturer: Caspian Products LLC
        We hereby certify that the goods described below originate in Azerbaijan.
        Chamber of Commerce of Azerbaijan Republic
        HS Code: 2709.00
        """
        doc_type, confidence = classifier.classify(text)
        assert doc_type == DocumentType.CERTIFICATE_OF_ORIGIN
        assert confidence > 0.3

    def test_classify_packing_list(self, classifier):
        text = """
        PACKING LIST
        Gross Weight: 5,000 kg
        Net Weight: 4,200 kg
        Package: 150 cartons
        Marks and Numbers: ABC-2023
        Dimensions: 120x80x100 cm
        Measurement: 15.5 CBM
        """
        doc_type, confidence = classifier.classify(text)
        assert doc_type == DocumentType.PACKING_LIST
        assert confidence > 0.3

    def test_classify_empty_text(self, classifier):
        doc_type, confidence = classifier.classify("")
        assert doc_type == DocumentType.UNKNOWN
        assert confidence == 0.0

    def test_classify_ambiguous_text(self, classifier):
        text = "Some generic document with no clear trade keywords"
        doc_type, confidence = classifier.classify(text)
        # Should still return something, even if low confidence
        assert isinstance(doc_type, DocumentType)
        assert 0.0 <= confidence <= 1.0

    def test_get_scores_returns_all_types(self, classifier):
        text = "COMMERCIAL INVOICE with bill of lading reference"
        scores = classifier.get_scores(text)
        assert "commercial_invoice" in scores
        assert "bill_of_lading" in scores
        assert "certificate_of_origin" in scores
        assert "packing_list" in scores

    def test_confidence_between_zero_and_one(self, classifier):
        text = "BILL OF LADING shipper consignee vessel port of loading"
        _, confidence = classifier.classify(text)
        assert 0.0 <= confidence <= 1.0
