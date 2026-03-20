"""
Validates extracted document fields.

Checks date formats, amount ranges, HS code format, country codes,
and other domain-specific validation rules.
"""

from __future__ import annotations

import re
import logging
from datetime import datetime
from typing import Any

from .schemas import DocumentType

logger = logging.getLogger(__name__)

# ISO 3166-1 alpha-2 country codes (common trade-relevant subset)
VALID_COUNTRY_CODES = {
    "AD", "AE", "AF", "AG", "AL", "AM", "AO", "AR", "AT", "AU", "AZ",
    "BA", "BB", "BD", "BE", "BF", "BG", "BH", "BI", "BJ", "BN", "BO",
    "BR", "BS", "BT", "BW", "BY", "BZ", "CA", "CD", "CF", "CG", "CH",
    "CI", "CL", "CM", "CN", "CO", "CR", "CU", "CV", "CY", "CZ", "DE",
    "DJ", "DK", "DM", "DO", "DZ", "EC", "EE", "EG", "ER", "ES", "ET",
    "FI", "FJ", "FR", "GA", "GB", "GD", "GE", "GH", "GM", "GN", "GQ",
    "GR", "GT", "GW", "GY", "HK", "HN", "HR", "HT", "HU", "ID", "IE",
    "IL", "IN", "IQ", "IR", "IS", "IT", "JM", "JO", "JP", "KE", "KG",
    "KH", "KI", "KM", "KN", "KP", "KR", "KW", "KZ", "LA", "LB", "LC",
    "LI", "LK", "LR", "LS", "LT", "LU", "LV", "LY", "MA", "MC", "MD",
    "ME", "MG", "MK", "ML", "MM", "MN", "MO", "MR", "MT", "MU", "MV",
    "MW", "MX", "MY", "MZ", "NA", "NE", "NG", "NI", "NL", "NO", "NP",
    "NR", "NZ", "OM", "PA", "PE", "PG", "PH", "PK", "PL", "PT", "PW",
    "PY", "QA", "RO", "RS", "RU", "RW", "SA", "SB", "SC", "SD", "SE",
    "SG", "SI", "SK", "SL", "SM", "SN", "SO", "SR", "SS", "ST", "SV",
    "SY", "SZ", "TD", "TG", "TH", "TJ", "TL", "TM", "TN", "TO", "TR",
    "TT", "TV", "TW", "TZ", "UA", "UG", "US", "UY", "UZ", "VA", "VC",
    "VE", "VN", "VU", "WS", "YE", "ZA", "ZM", "ZW",
}

# Date formats to try when validating
DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%B %d, %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%d %b %Y",
]


class FieldValidator:
    """Validates extracted fields from trade documents."""

    def __init__(self, max_amount: float = 1_000_000_000.0, min_amount: float = 0.0):
        """
        Initialize the validator.

        Args:
            max_amount: Maximum plausible monetary amount.
            min_amount: Minimum plausible monetary amount.
        """
        self.max_amount = max_amount
        self.min_amount = min_amount

    def validate(self, fields: dict[str, Any], doc_type: DocumentType) -> list[str]:
        """
        Validate all extracted fields.

        Args:
            fields: Dictionary of extracted field name -> value.
            doc_type: Document type for type-specific validation.

        Returns:
            List of validation error messages. Empty list means all valid.
        """
        errors: list[str] = []

        # Validate dates
        if "date" in fields:
            error = self.validate_date(fields["date"])
            if error:
                errors.append(error)

        if "dates" in fields:
            for date_str in fields["dates"]:
                error = self.validate_date(date_str)
                if error:
                    errors.append(error)

        # Validate amounts
        if "total_amount" in fields:
            error = self.validate_amount(fields["total_amount"])
            if error:
                errors.append(error)

        if "amounts" in fields:
            for amount_str in fields["amounts"]:
                error = self.validate_amount(amount_str)
                if error:
                    errors.append(error)

        # Validate HS codes
        if "hs_codes" in fields:
            for code in fields["hs_codes"]:
                error = self.validate_hs_code(code)
                if error:
                    errors.append(error)

        # Validate country codes
        if "country_codes" in fields:
            for code in fields["country_codes"]:
                error = self.validate_country_code(code)
                if error:
                    errors.append(error)

        # Type-specific validation
        if doc_type == DocumentType.COMMERCIAL_INVOICE:
            errors.extend(self._validate_invoice_fields(fields))
        elif doc_type == DocumentType.BILL_OF_LADING:
            errors.extend(self._validate_bol_fields(fields))
        elif doc_type == DocumentType.PACKING_LIST:
            errors.extend(self._validate_packing_list_fields(fields))

        return errors

    def validate_date(self, date_str: str) -> str | None:
        """
        Validate a date string against known formats.

        Returns:
            Error message if invalid, None if valid.
        """
        if not date_str or not isinstance(date_str, str):
            return "Date value is empty or not a string."

        for fmt in DATE_FORMATS:
            try:
                parsed = datetime.strptime(date_str.strip(), fmt)
                # Sanity check: year between 1990 and 2040
                if parsed.year < 1990 or parsed.year > 2040:
                    return f"Date year {parsed.year} is outside plausible range (1990-2040)."
                return None
            except ValueError:
                continue

        return f"Date '{date_str}' does not match any recognized format."

    def validate_amount(self, amount_str: str) -> str | None:
        """
        Validate a monetary amount string.

        Returns:
            Error message if invalid, None if valid.
        """
        if not amount_str:
            return "Amount value is empty."

        # Strip currency symbols and codes
        cleaned = re.sub(r"[A-Za-z$€£\s]", "", str(amount_str))
        cleaned = cleaned.replace(",", "")

        try:
            value = float(cleaned)
        except ValueError:
            return f"Amount '{amount_str}' could not be parsed as a number."

        if value < self.min_amount:
            return f"Amount {value} is below minimum ({self.min_amount})."
        if value > self.max_amount:
            return f"Amount {value} exceeds maximum ({self.max_amount})."

        return None

    def validate_hs_code(self, code: str) -> str | None:
        """
        Validate an HS code format.

        Valid formats: 4-10 digits, optionally separated by dots.
        Example: 8471.30.0100, 847130, 8471.30

        Returns:
            Error message if invalid, None if valid.
        """
        if not code:
            return "HS code is empty."

        digits = code.replace(".", "")
        if not digits.isdigit():
            return f"HS code '{code}' contains non-numeric characters."

        if len(digits) < 4 or len(digits) > 10:
            return f"HS code '{code}' has {len(digits)} digits (expected 4-10)."

        # First two digits must be a valid HS chapter (01-99)
        chapter = int(digits[:2])
        if chapter < 1 or chapter > 99:
            return f"HS code '{code}' has invalid chapter {chapter:02d}."

        return None

    def validate_country_code(self, code: str) -> str | None:
        """
        Validate an ISO 3166-1 alpha-2 country code.

        Returns:
            Error message if invalid, None if valid.
        """
        if not code:
            return "Country code is empty."

        code_upper = code.strip().upper()
        if len(code_upper) != 2:
            return f"Country code '{code}' is not 2 characters."

        if code_upper not in VALID_COUNTRY_CODES:
            return f"Country code '{code}' is not a recognized ISO 3166-1 code."

        return None

    def _validate_invoice_fields(self, fields: dict[str, Any]) -> list[str]:
        """Validate invoice-specific fields."""
        errors = []
        if "invoice_number" in fields:
            inv = fields["invoice_number"]
            if len(inv) < 2:
                errors.append(f"Invoice number '{inv}' is suspiciously short.")
            if len(inv) > 50:
                errors.append(f"Invoice number '{inv}' is suspiciously long.")
        return errors

    def _validate_bol_fields(self, fields: dict[str, Any]) -> list[str]:
        """Validate bill of lading-specific fields."""
        errors = []
        if "container_numbers" in fields:
            for container in fields["container_numbers"]:
                if not re.match(r"^[A-Z]{4}\d{7}$", container):
                    errors.append(f"Container number '{container}' does not match standard format (XXXX1234567).")
        return errors

    def _validate_packing_list_fields(self, fields: dict[str, Any]) -> list[str]:
        """Validate packing list-specific fields."""
        errors = []
        if "package_count" in fields:
            count = fields["package_count"]
            if isinstance(count, int) and count <= 0:
                errors.append(f"Package count {count} must be positive.")
            if isinstance(count, int) and count > 100_000:
                errors.append(f"Package count {count} is unusually large.")

        if "gross_weight" in fields and "net_weight" in fields:
            try:
                gross = float(str(fields["gross_weight"]).replace(",", ""))
                net = float(str(fields["net_weight"]).replace(",", ""))
                if net > gross:
                    errors.append(f"Net weight ({net}) exceeds gross weight ({gross}).")
            except ValueError:
                pass

        return errors
