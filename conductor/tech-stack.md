# Technology Stack

## Core Technology
- **Programming Language:** Python (>=3.10)
- **Dependency Management:** UV
- **MCP Framework:** FastMCP (>=2.0.0)

## AI Services
- **OCR Engine:** Qwen-VL (via `openai` Python library) for reading handwritten text.
- **Cleanup & Evaluation:** xAI APIs (Grok) for text normalization, PII scrubbing, and essay grading.

## Data Storage
- **Primary:** SQLite (Embedded)
  - Managed via `edmcp/core/db.py`
  - Stores job status, student metadata, raw text, scrubbed text, and evaluation results.
  - Simplifies tool handoffs (Agent passes Job IDs, not full data).
- **Intermediary:** JSONL (Legacy/Backup) - Used for initial prototypes or export.
- **Files:**
  - PDFs: `data/raw_pdfs/`
  - Images: `data/images/`
  - Logs: `logs/`

## Data Processing
- **Document Handling:** `pdf2image` (for converting PDFs to images for OCR), `regex` (for text pattern matching).
- **Environment Management:** `python-dotenv` for managing API keys and configuration secrets.
