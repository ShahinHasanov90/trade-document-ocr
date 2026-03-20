# Trade Document OCR

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Overview

OCR and structured extraction pipeline for customs trade documents. Processes bills of lading, commercial invoices, certificates of origin, and packing lists. Extracts key fields (parties, commodities, values, dates) into structured JSON output.

Supports multi-language document processing: English, Russian, and Azerbaijani (EN/RU/AZ).

## Features

- **Document Classification** -- Automatically identifies document type (bill of lading, commercial invoice, certificate of origin, packing list)
- **Image Preprocessing** -- Deskew, denoise, binarization, and contrast enhancement for reliable OCR
- **Text Extraction** -- Tesseract OCR integration with multi-language support
- **Field Parsing** -- Regex and heuristic-based extraction for invoice numbers, dates, parties, amounts, HS codes, and weights
- **Field Validation** -- Validates date formats, amount ranges, HS code structure, and ISO country codes
- **Structured Output** -- Pydantic-modeled JSON output for downstream integration
- **REST API** -- FastAPI endpoints for single/batch extraction, classification, and health checks

## Project Structure

```
trade-document-ocr/
├── src/ocr/
│   ├── __init__.py
│   ├── pipeline.py            # Main OCR pipeline orchestration
│   ├── preprocessor.py        # Image preprocessing
│   ├── extractor.py           # Tesseract OCR wrapper
│   ├── parser.py              # Document field parser
│   ├── document_classifier.py # Document type classifier
│   ├── field_validator.py     # Extracted field validation
│   ├── schemas.py             # Pydantic data models
│   └── api.py                 # FastAPI endpoints
├── tests/
│   ├── test_parser.py
│   ├── test_classifier.py
│   └── test_validator.py
├── config/
│   └── extraction_rules.yaml
├── requirements.txt
├── setup.py
├── Makefile
├── Dockerfile
└── LICENSE
```

## Quick Start

```bash
# Install dependencies
make install

# Run tests
make test

# Start API server
make serve
```

## API Endpoints

| Endpoint         | Method | Description                        |
|------------------|--------|------------------------------------|
| `/extract`       | POST   | Extract fields from a single image |
| `/extract/batch` | POST   | Batch extraction from multiple images |
| `/classify`      | POST   | Classify document type             |
| `/health`        | GET    | Service health check               |

## Supported Document Types

- **Bill of Lading** -- Shipper, consignee, vessel, port of loading/discharge, container numbers
- **Commercial Invoice** -- Seller, buyer, invoice number, date, line items, total amount, currency
- **Certificate of Origin** -- Exporter, manufacturer, country of origin, HS codes, certifying authority
- **Packing List** -- Shipper, consignee, package count, gross/net weight, dimensions

## License

MIT License. See [LICENSE](LICENSE) for details.
