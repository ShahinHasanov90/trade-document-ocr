"""
Pydantic models for extracted document data.

Defines the structured output schemas for the OCR extraction pipeline.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Supported trade document types."""

    BILL_OF_LADING = "bill_of_lading"
    COMMERCIAL_INVOICE = "commercial_invoice"
    CERTIFICATE_OF_ORIGIN = "certificate_of_origin"
    PACKING_LIST = "packing_list"
    UNKNOWN = "unknown"


class ExtractionResult(BaseModel):
    """Result of the OCR extraction pipeline for a single document."""

    source_file: str = Field(..., description="Path or identifier of the source image file.")
    document_type: DocumentType = Field(..., description="Classified document type.")
    raw_text: str = Field("", description="Raw OCR text extracted from the image.")
    fields: dict[str, Any] = Field(default_factory=dict, description="Extracted structured fields.")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Classification confidence score.")
    validation_errors: list[str] = Field(default_factory=list, description="List of validation error messages.")


class PartyInfo(BaseModel):
    """Information about a trade party (seller, buyer, shipper, consignee)."""

    name: Optional[str] = Field(None, description="Party name.")
    address: Optional[str] = Field(None, description="Party address.")
    country: Optional[str] = Field(None, description="ISO 3166-1 alpha-2 country code.")
    tax_id: Optional[str] = Field(None, description="Tax identification number.")


class LineItem(BaseModel):
    """A single line item in an invoice or packing list."""

    description: Optional[str] = Field(None, description="Item description.")
    quantity: Optional[float] = Field(None, description="Quantity.")
    unit: Optional[str] = Field(None, description="Unit of measurement.")
    unit_price: Optional[float] = Field(None, description="Unit price.")
    total_price: Optional[float] = Field(None, description="Total price for the line.")
    hs_code: Optional[str] = Field(None, description="HS tariff code.")
    weight: Optional[float] = Field(None, description="Weight in kg.")


class InvoiceData(BaseModel):
    """Structured data for a commercial invoice."""

    invoice_number: Optional[str] = None
    date: Optional[str] = None
    seller: Optional[PartyInfo] = None
    buyer: Optional[PartyInfo] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    line_items: list[LineItem] = Field(default_factory=list)
    payment_terms: Optional[str] = None
    incoterms: Optional[str] = None


class BillOfLadingData(BaseModel):
    """Structured data for a bill of lading."""

    bl_number: Optional[str] = None
    date: Optional[str] = None
    shipper: Optional[PartyInfo] = None
    consignee: Optional[PartyInfo] = None
    notify_party: Optional[PartyInfo] = None
    vessel: Optional[str] = None
    voyage: Optional[str] = None
    port_of_loading: Optional[str] = None
    port_of_discharge: Optional[str] = None
    container_numbers: list[str] = Field(default_factory=list)
    description_of_goods: Optional[str] = None
    gross_weight: Optional[float] = None
    measurement: Optional[str] = None


class CertificateOfOriginData(BaseModel):
    """Structured data for a certificate of origin."""

    certificate_number: Optional[str] = None
    date: Optional[str] = None
    exporter: Optional[PartyInfo] = None
    manufacturer: Optional[PartyInfo] = None
    country_of_origin: Optional[str] = None
    hs_codes: list[str] = Field(default_factory=list)
    description_of_goods: Optional[str] = None
    certifying_authority: Optional[str] = None


class PackingListData(BaseModel):
    """Structured data for a packing list."""

    date: Optional[str] = None
    shipper: Optional[PartyInfo] = None
    consignee: Optional[PartyInfo] = None
    invoice_reference: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)
    total_packages: Optional[int] = None
    gross_weight: Optional[float] = None
    net_weight: Optional[float] = None
    dimensions: Optional[str] = None


class ClassificationResult(BaseModel):
    """Result of document type classification."""

    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    scores: dict[str, float] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """API health check response."""

    status: str = "ok"
    version: str = "0.1.0"
    tesseract_available: bool = False
