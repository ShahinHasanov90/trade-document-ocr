"""Tests for the field validator."""

import pytest

from src.ocr.field_validator import FieldValidator
from src.ocr.schemas import DocumentType


@pytest.fixture
def validator():
    """Create a validator instance."""
    return FieldValidator()


class TestDateValidation:

    def test_valid_iso_date(self, validator):
        assert validator.validate_date("2023-06-15") is None

    def test_valid_slash_date(self, validator):
        assert validator.validate_date("15/06/2023") is None

    def test_valid_dot_date(self, validator):
        assert validator.validate_date("01.12.2022") is None

    def test_invalid_date_format(self, validator):
        error = validator.validate_date("not-a-date")
        assert error is not None
        assert "does not match" in error

    def test_out_of_range_year(self, validator):
        error = validator.validate_date("1850-01-01")
        assert error is not None
        assert "outside plausible range" in error

    def test_empty_date(self, validator):
        error = validator.validate_date("")
        assert error is not None


class TestAmountValidation:

    def test_valid_amount(self, validator):
        assert validator.validate_amount("USD 12,345.67") is None

    def test_valid_plain_amount(self, validator):
        assert validator.validate_amount("5000.00") is None

    def test_exceeds_max_amount(self, validator):
        error = validator.validate_amount("9999999999999")
        assert error is not None
        assert "exceeds maximum" in error

    def test_empty_amount(self, validator):
        error = validator.validate_amount("")
        assert error is not None


class TestHSCodeValidation:

    def test_valid_hs_code_6_digit(self, validator):
        assert validator.validate_hs_code("8471.30") is None

    def test_valid_hs_code_10_digit(self, validator):
        assert validator.validate_hs_code("8471.30.0100") is None

    def test_hs_code_too_short(self, validator):
        error = validator.validate_hs_code("84")
        assert error is not None

    def test_hs_code_non_numeric(self, validator):
        error = validator.validate_hs_code("ABCD.EF")
        assert error is not None
        assert "non-numeric" in error

    def test_empty_hs_code(self, validator):
        error = validator.validate_hs_code("")
        assert error is not None


class TestCountryCodeValidation:

    def test_valid_country_code(self, validator):
        assert validator.validate_country_code("AZ") is None

    def test_valid_country_code_us(self, validator):
        assert validator.validate_country_code("US") is None

    def test_invalid_country_code(self, validator):
        error = validator.validate_country_code("XX")
        assert error is not None
        assert "not a recognized" in error

    def test_wrong_length_country_code(self, validator):
        error = validator.validate_country_code("USA")
        assert error is not None


class TestFullValidation:

    def test_validate_valid_invoice_fields(self, validator):
        fields = {
            "date": "2023-06-15",
            "total_amount": "USD 5000.00",
            "hs_codes": ["8471.30.0100"],
            "country_codes": ["AZ", "TR"],
            "invoice_number": "INV-2023-001",
        }
        errors = validator.validate(fields, DocumentType.COMMERCIAL_INVOICE)
        assert len(errors) == 0

    def test_validate_invalid_fields_returns_errors(self, validator):
        fields = {
            "date": "not-a-date",
            "total_amount": "9999999999999",
            "hs_codes": ["AB"],
            "country_codes": ["XX"],
        }
        errors = validator.validate(fields, DocumentType.COMMERCIAL_INVOICE)
        assert len(errors) >= 3

    def test_validate_packing_list_weight_mismatch(self, validator):
        fields = {
            "gross_weight": "100",
            "net_weight": "200",
        }
        errors = validator.validate(fields, DocumentType.PACKING_LIST)
        assert any("exceeds gross" in e for e in errors)

    def test_validate_container_number_format(self, validator):
        fields = {
            "container_numbers": ["MSKU1234567", "INVALID"],
        }
        errors = validator.validate(fields, DocumentType.BILL_OF_LADING)
        assert any("INVALID" in e for e in errors)
