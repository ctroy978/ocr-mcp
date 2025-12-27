# Technology Stack

## Core Technology
- **Programming Language:** Python (>=3.10)
- **Dependency Management:** UV
- **MCP Framework:** FastMCP (>=2.0.0)

## AI Services
- **OCR Engine:** Qwen-VL (via `openai` Python library) for reading handwritten text.
- **Cleanup & Evaluation:** xAI APIs (Grok) for text normalization, PII scrubbing, and essay grading.

## Data Processing
- **Document Handling:** `pdf2image` (for converting PDFs to images for OCR), `regex` (for text pattern matching).
- **Data Exchange:** JSONL (JSON Lines) for structured, streaming handoffs between modular tools.
- **Environment Management:** `python-dotenv` for managing API keys and configuration secrets.
