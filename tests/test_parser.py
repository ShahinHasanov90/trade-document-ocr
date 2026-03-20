"""Tests for the document field parser."""

import pytest

from src.ocr.parser import DocumentFieldParser
from src.ocr.schemas import DocumentType


@pytest.fixture
def parser():
    """Create a parser instance with no custom rules file."""
    return DocumentFieldParser(rules_path=None)


# --- Date extraction tests ---

class TestDateExtraction:

    def test_extract_iso_date(self, parser):
        text = "Invoice date: 2023-06-15"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "date" in fields
        assert "2023-06-15" in fields["dates"]

    def test_extract_slash_date(self, parser):
        text = "Date: 15/06/2023"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "15/06/2023" in fields["dates"]

    def test_extract_dot_date(self, parser):
        text = "Document dated 01.12.2022"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "01.12.2022" in fields["dates"]

    def test_extract_written_date(self, parser):
        text = "Issued on January 15, 2023"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert len(fields.get("dates", [])) >= 1


# --- Amount extraction tests ---

class TestAmountExtraction:

    def test_extract_usd_amount(self, parser):
        text = "Total: USD 12,345.67"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "amounts" in fields
        assert any("12,345.67" in a for a in fields["amounts"])

    def test_extract_dollar_sign_amount(self, parser):
        text = "Grand total: $5,000.00"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "amounts" in fields

    def test_extract_euro_amount(self, parser):
        text = "Amount: EUR 8500.00"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "amounts" in fields

    def test_extract_total_keyword_amount(self, parser):
        text = "TOTAL AMOUNT: 25000.00 USD"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "amounts" in fields


# --- HS code extraction tests ---

class TestHSCodeExtraction:

    def test_extract_hs_code_with_label(self, parser):
        text = "HS Code: 8471.30.0100"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "hs_codes" in fields
        assert "8471.30.0100" in fields["hs_codes"]

    def test_extract_tariff_code(self, parser):
        text = "Tariff: 6204.62"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "hs_codes" in fields


# --- Invoice-specific field tests ---

class TestInvoiceFieldExtraction:

    def test_extract_invoice_number(self, parser):
        text = "Invoice No: INV-2023-0456\nSeller: ABC Trading Co."
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "invoice_number" in fields
        assert "INV-2023-0456" in fields["invoice_number"]

    def test_extract_seller(self, parser):
        text = "Seller: Global Export Ltd.\nBuyer: Local Import Inc."
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "seller" in fields
        assert "Global Export" in fields["seller"]

    def test_extract_buyer(self, parser):
        text = "Seller: Someone\nBuyer: Azerbaijan Trading House LLC"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "buyer" in fields
        assert "Azerbaijan Trading" in fields["buyer"]

    def test_extract_weights(self, parser):
        text = "Gross Weight: 1500.50 kg\nNet Weight: 1200 kg"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert "weights" in fields
        assert len(fields["weights"]) >= 1


# --- Bill of Lading field tests ---

class TestBOLFieldExtraction:

    def test_extract_bl_number(self, parser):
        text = "Bill of Lading No: MAEU123456789"
        fields = parser.parse(text, DocumentType.BILL_OF_LADING)
        assert "bl_number" in fields

    def test_extract_vessel(self, parser):
        text = "Vessel: MSC OSCAR\nVoyage: 123E"
        fields = parser.parse(text, DocumentType.BILL_OF_LADING)
        assert "vessel" in fields
        assert "MSC OSCAR" in fields["vessel"]

    def test_extract_ports(self, parser):
        text = "Port of Loading: Shanghai\nPort of Discharge: Baku"
        fields = parser.parse(text, DocumentType.BILL_OF_LADING)
        assert "port_of_loading" in fields
        assert "Shanghai" in fields["port_of_loading"]
        assert "port_of_discharge" in fields
        assert "Baku" in fields["port_of_discharge"]

    def test_extract_container_numbers(self, parser):
        text = "Container: MSKU1234567, TCLU7654321"
        fields = parser.parse(text, DocumentType.BILL_OF_LADING)
        assert "container_numbers" in fields
        assert "MSKU1234567" in fields["container_numbers"]
        assert "TCLU7654321" in fields["container_numbers"]


# --- Packing List field tests ---

class TestPackingListFieldExtraction:

    def test_extract_package_count(self, parser):
        text = "Total Packages: 150"
        fields = parser.parse(text, DocumentType.PACKING_LIST)
        assert "package_count" in fields
        assert fields["package_count"] == 150

    def test_extract_gross_net_weight(self, parser):
        text = "Gross Weight: 5000.50\nNet Weight: 4200.00"
        fields = parser.parse(text, DocumentType.PACKING_LIST)
        assert "gross_weight" in fields
        assert "net_weight" in fields

    def test_extract_dimensions(self, parser):
        text = "Dimensions: 120x80x100 cm"
        fields = parser.parse(text, DocumentType.PACKING_LIST)
        assert "dimensions" in fields


# --- Edge cases ---

class TestEdgeCases:

    def test_empty_text(self, parser):
        fields = parser.parse("", DocumentType.COMMERCIAL_INVOICE)
        assert isinstance(fields, dict)

    def test_no_matching_fields(self, parser):
        text = "This is just random text with no trade document fields."
        fields = parser.parse(text, DocumentType.UNKNOWN)
        assert isinstance(fields, dict)

    def test_multiple_dates(self, parser):
        text = "Invoice date: 2023-01-15\nShipment date: 2023-02-01\nDue date: 2023-03-15"
        fields = parser.parse(text, DocumentType.COMMERCIAL_INVOICE)
        assert len(fields.get("dates", [])) >= 3
