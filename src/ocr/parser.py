"""
Document field parser: regex + heuristic extraction for trade document fields.

Extracts invoice numbers, dates, parties (shipper/consignee/seller/buyer),
monetary amounts, HS codes, weights, and other domain-specific fields from
raw OCR text.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from .schemas import DocumentType

logger = logging.getLogger(__name__)

DEFAULT_RULES_PATH = Path(__file__).parent.parent.parent / "config" / "extraction_rules.yaml"


class DocumentFieldParser:
    """Parses structured fields from raw OCR text using regex patterns and heuristics."""

    def __init__(self, rules_path: Optional[str] = None):
        """
        Initialize the parser with extraction rules.

        Args:
            rules_path: Path to the YAML extraction rules file.
        """
        rules_file = Path(rules_path) if rules_path else DEFAULT_RULES_PATH
        self.rules = self._load_rules(rules_file)

    @staticmethod
    def _load_rules(rules_path: Path) -> dict:
        """Load extraction rules from YAML file."""
        if not rules_path.exists():
            logger.warning("Rules file not found at %s, using empty rules", rules_path)
            return {}
        with open(rules_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def parse(self, text: str, doc_type: DocumentType) -> dict[str, Any]:
        """
        Parse fields from raw text based on document type.

        Args:
            text: Raw OCR text.
            doc_type: Classified document type.

        Returns:
            Dictionary of extracted field name -> value mappings.
        """
        fields: dict[str, Any] = {}

        # Common fields across all document types
        fields.update(self._extract_dates(text))
        fields.update(self._extract_amounts(text))
        fields.update(self._extract_hs_codes(text))
        fields.update(self._extract_countries(text))

        # Type-specific extraction
        if doc_type == DocumentType.COMMERCIAL_INVOICE:
            fields.update(self._extract_invoice_fields(text))
        elif doc_type == DocumentType.BILL_OF_LADING:
            fields.update(self._extract_bol_fields(text))
        elif doc_type == DocumentType.CERTIFICATE_OF_ORIGIN:
            fields.update(self._extract_coo_fields(text))
        elif doc_type == DocumentType.PACKING_LIST:
            fields.update(self._extract_packing_list_fields(text))

        # Apply custom regex rules from YAML
        fields.update(self._apply_custom_rules(text, doc_type))

        return fields

    def _extract_dates(self, text: str) -> dict[str, Any]:
        """Extract date fields from text."""
        dates = []
        # ISO format: 2023-01-15
        iso_pattern = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
        dates.extend(iso_pattern.findall(text))

        # Common formats: 15/01/2023, 01/15/2023, 15.01.2023
        slash_pattern = re.compile(r"\b(\d{1,2}[/\.]\d{1,2}[/\.]\d{4})\b")
        dates.extend(slash_pattern.findall(text))

        # Written format: January 15, 2023 / 15 January 2023
        month_names = (
            r"(?:January|February|March|April|May|June|July|August|September|"
            r"October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        )
        written_pattern = re.compile(
            rf"\b({month_names}\s+\d{{1,2}},?\s+\d{{4}}|\d{{1,2}}\s+{month_names}\s+\d{{4}})\b",
            re.IGNORECASE,
        )
        dates.extend(written_pattern.findall(text))

        result = {}
        if dates:
            result["dates"] = dates
            result["date"] = dates[0]  # Primary date is the first found
        return result

    def _extract_amounts(self, text: str) -> dict[str, Any]:
        """Extract monetary amounts and currency codes."""
        amounts = []

        # Currency symbol + amount: $1,234.56 or EUR 1234.56
        currency_pattern = re.compile(
            r"(?:USD|EUR|GBP|AZN|RUB|TRY|\$|€|£)\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)"
        )
        for match in currency_pattern.finditer(text):
            amounts.append(match.group(0).strip())

        # Amount + currency: 1,234.56 USD
        amount_currency_pattern = re.compile(
            r"(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)\s*(?:USD|EUR|GBP|AZN|RUB|TRY)"
        )
        for match in amount_currency_pattern.finditer(text):
            amounts.append(match.group(0).strip())

        # Total/amount keywords
        total_pattern = re.compile(
            r"(?:total|amount|sum|value)[:\s]*[^\d]*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)",
            re.IGNORECASE,
        )
        for match in total_pattern.finditer(text):
            amounts.append(match.group(1).strip())

        result = {}
        if amounts:
            result["amounts"] = list(set(amounts))
            result["total_amount"] = amounts[0]
        return result

    def _extract_hs_codes(self, text: str) -> dict[str, Any]:
        """Extract HS (Harmonized System) codes."""
        # HS codes are 6-10 digit codes, often with dots: 8471.30.0100
        hs_pattern = re.compile(
            r"\b(\d{4}(?:\.\d{2}(?:\.\d{2,4})?)?)\b"
        )

        # Filter: look for context clues near the code
        hs_context = re.compile(
            r"(?:HS|H\.S\.|tariff|commodity|code|heading)[:\s#]*(\d{4}(?:\.\d{2}(?:\.\d{2,4})?)?)",
            re.IGNORECASE,
        )

        codes = []
        for match in hs_context.finditer(text):
            codes.append(match.group(1))

        # Fallback: standalone 6+ digit patterns that look like HS codes
        if not codes:
            for match in hs_pattern.finditer(text):
                code = match.group(1)
                if len(code.replace(".", "")) >= 6:
                    codes.append(code)

        result = {}
        if codes:
            result["hs_codes"] = list(set(codes))
        return result

    def _extract_countries(self, text: str) -> dict[str, Any]:
        """Extract country codes and names."""
        # ISO 3166-1 alpha-2 codes in context
        country_context = re.compile(
            r"(?:country|origin|destination|port)[:\s]*([A-Z]{2})\b",
            re.IGNORECASE,
        )
        codes = [m.group(1).upper() for m in country_context.finditer(text)]

        result = {}
        if codes:
            result["country_codes"] = list(set(codes))
        return result

    def _extract_invoice_fields(self, text: str) -> dict[str, Any]:
        """Extract fields specific to commercial invoices."""
        fields: dict[str, Any] = {}

        # Invoice number
        inv_pattern = re.compile(
            r"(?:invoice|inv)[.\s#:]*(?:no|number|num|nr)?[.\s#:]*([A-Za-z0-9\-/]+)",
            re.IGNORECASE,
        )
        match = inv_pattern.search(text)
        if match:
            fields["invoice_number"] = match.group(1).strip()

        # Seller / exporter
        seller_pattern = re.compile(
            r"(?:seller|exporter|shipper|from)[:\s]*([^\n]{5,80})", re.IGNORECASE
        )
        match = seller_pattern.search(text)
        if match:
            fields["seller"] = match.group(1).strip()

        # Buyer / importer
        buyer_pattern = re.compile(
            r"(?:buyer|importer|consignee|to|bill\s*to)[:\s]*([^\n]{5,80})", re.IGNORECASE
        )
        match = buyer_pattern.search(text)
        if match:
            fields["buyer"] = match.group(1).strip()

        # Weights
        weight_pattern = re.compile(
            r"(?:gross\s*weight|net\s*weight|weight)[:\s]*([\d.,]+)\s*(?:kg|KG|kgs|tons?|MT)",
            re.IGNORECASE,
        )
        weights = []
        for match in weight_pattern.finditer(text):
            weights.append(match.group(0).strip())
        if weights:
            fields["weights"] = weights

        return fields

    def _extract_bol_fields(self, text: str) -> dict[str, Any]:
        """Extract fields specific to bills of lading."""
        fields: dict[str, Any] = {}

        # B/L number
        bl_pattern = re.compile(
            r"(?:b/?l|bill\s*of\s*lading)[.\s#:]*(?:no|number|num|nr)?[.\s#:]*([A-Za-z0-9\-/]+)",
            re.IGNORECASE,
        )
        match = bl_pattern.search(text)
        if match:
            fields["bl_number"] = match.group(1).strip()

        # Vessel name
        vessel_pattern = re.compile(
            r"(?:vessel|ship|carrier)[:\s]*([^\n]{3,60})", re.IGNORECASE
        )
        match = vessel_pattern.search(text)
        if match:
            fields["vessel"] = match.group(1).strip()

        # Port of loading
        pol_pattern = re.compile(
            r"(?:port\s*of\s*loading|loading\s*port|POL)[:\s]*([^\n]{3,60})", re.IGNORECASE
        )
        match = pol_pattern.search(text)
        if match:
            fields["port_of_loading"] = match.group(1).strip()

        # Port of discharge
        pod_pattern = re.compile(
            r"(?:port\s*of\s*discharge|discharge\s*port|POD)[:\s]*([^\n]{3,60})", re.IGNORECASE
        )
        match = pod_pattern.search(text)
        if match:
            fields["port_of_discharge"] = match.group(1).strip()

        # Container numbers (e.g., MSKU1234567)
        container_pattern = re.compile(r"\b([A-Z]{4}\d{7})\b")
        containers = container_pattern.findall(text)
        if containers:
            fields["container_numbers"] = list(set(containers))

        # Shipper
        shipper_pattern = re.compile(
            r"(?:shipper|consignor)[:\s]*([^\n]{5,80})", re.IGNORECASE
        )
        match = shipper_pattern.search(text)
        if match:
            fields["shipper"] = match.group(1).strip()

        # Consignee
        consignee_pattern = re.compile(
            r"(?:consignee)[:\s]*([^\n]{5,80})", re.IGNORECASE
        )
        match = consignee_pattern.search(text)
        if match:
            fields["consignee"] = match.group(1).strip()

        return fields

    def _extract_coo_fields(self, text: str) -> dict[str, Any]:
        """Extract fields specific to certificates of origin."""
        fields: dict[str, Any] = {}

        # Certificate number
        cert_pattern = re.compile(
            r"(?:certificate|cert)[.\s#:]*(?:no|number|num|nr)?[.\s#:]*([A-Za-z0-9\-/]+)",
            re.IGNORECASE,
        )
        match = cert_pattern.search(text)
        if match:
            fields["certificate_number"] = match.group(1).strip()

        # Country of origin
        origin_pattern = re.compile(
            r"(?:country\s*of\s*origin|origin)[:\s]*([^\n]{2,60})", re.IGNORECASE
        )
        match = origin_pattern.search(text)
        if match:
            fields["country_of_origin"] = match.group(1).strip()

        # Manufacturer
        manufacturer_pattern = re.compile(
            r"(?:manufacturer|producer)[:\s]*([^\n]{5,80})", re.IGNORECASE
        )
        match = manufacturer_pattern.search(text)
        if match:
            fields["manufacturer"] = match.group(1).strip()

        # Certifying authority
        authority_pattern = re.compile(
            r"(?:certif(?:ying|ied)\s*(?:by|authority)|chamber\s*of\s*commerce|authority)[:\s]*([^\n]{5,80})",
            re.IGNORECASE,
        )
        match = authority_pattern.search(text)
        if match:
            fields["certifying_authority"] = match.group(1).strip()

        return fields

    def _extract_packing_list_fields(self, text: str) -> dict[str, Any]:
        """Extract fields specific to packing lists."""
        fields: dict[str, Any] = {}

        # Package count
        package_pattern = re.compile(
            r"(?:packages?|cartons?|boxes?|pieces?|pcs)[:\s]*(\d+)", re.IGNORECASE
        )
        match = package_pattern.search(text)
        if match:
            fields["package_count"] = int(match.group(1))

        # Gross weight
        gross_pattern = re.compile(
            r"(?:gross\s*weight|G\.?W\.?)[:\s]*([\d.,]+)\s*(?:kg|KG|kgs|MT)?",
            re.IGNORECASE,
        )
        match = gross_pattern.search(text)
        if match:
            fields["gross_weight"] = match.group(1).strip()

        # Net weight
        net_pattern = re.compile(
            r"(?:net\s*weight|N\.?W\.?)[:\s]*([\d.,]+)\s*(?:kg|KG|kgs|MT)?",
            re.IGNORECASE,
        )
        match = net_pattern.search(text)
        if match:
            fields["net_weight"] = match.group(1).strip()

        # Dimensions
        dim_pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)\s*(?:cm|mm|m)?"
        )
        dimensions = []
        for match in dim_pattern.finditer(text):
            dimensions.append(match.group(0).strip())
        if dimensions:
            fields["dimensions"] = dimensions

        return fields

    def _apply_custom_rules(self, text: str, doc_type: DocumentType) -> dict[str, Any]:
        """Apply custom regex rules from the YAML configuration."""
        fields: dict[str, Any] = {}

        type_key = doc_type.value
        doc_rules = self.rules.get("document_types", {}).get(type_key, {})
        custom_fields = doc_rules.get("fields", {})

        for field_name, field_config in custom_fields.items():
            patterns = field_config.get("patterns", [])
            for pattern_str in patterns:
                try:
                    match = re.search(pattern_str, text, re.IGNORECASE)
                    if match:
                        fields[field_name] = match.group(1).strip() if match.groups() else match.group(0).strip()
                        break
                except re.error as exc:
                    logger.warning("Invalid regex pattern for %s: %s", field_name, exc)

        return fields
