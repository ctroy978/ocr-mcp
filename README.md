# OCR-MCP Server

## Project Overview

This project implements a **Model Context Protocol (MCP)** server for batch OCR processing of student documents. It is a modular pipeline designed to handle large-scale handwriting recognition while ensuring data privacy and maintaining high text quality.

**Key Technology Stack:**
- **FastMCP:** For rapid server development.
- **Qwen-VL:** Superior handwritten text recognition (OCR) via an OpenAI-compatible API.
- **SQLite (Embedded):** For robust data storage, state management, and tool handoffs.
- **xAI (Grok):** Optional AI-based text normalization (Human-in-the-loop).
- **UV:** For blazing fast, reproducible dependency management.
- **Regex Scrubber:** Atomic, list-based PII redaction for student privacy.

---

## Architecture: The "Database-First" Pipeline

This server follows a modular "Heavy Lifter" pattern to manage high-volume data without flooding the AI agent's context window.

1.  **Job Orchestration:** Each batch processing run creates a unique **Job ID** and a dedicated directory for file artifacts.
2.  **Stateful Storage:** All extracted text and student metadata are stored in an embedded **SQLite** database (`edmcp.db`). This ensures data integrity and allows tools to track their progress (e.g., `PENDING` -> `SCRUBBED` -> `NORMALIZED`).
3.  **Modular Handoffs:** Instead of passing massive text blobs in the chat, the agent only passes a `job_id` between tools. Each tool queries the database for the required data, performs its task, and updates the record.
4.  **Human-in-the-Loop Cleanup:** Modern models like Qwen-VL produce high-quality OCR by default. For batches with poor handwriting, an optional `normalize_processed_job` tool can be triggered to fix typos using xAI, allowing for a verified cleanup pass before final evaluation.

---

## Modular Toolset

- **`batch_process_documents`**: The entry point. Converts PDFs to images, performs OCR via Qwen-VL, and saves **raw text** to the database.
- **`scrub_processed_job`**: Automatically redacts student names and PII using pre-defined CSV name lists.
- **`normalize_processed_job`**: (Optional) Uses AI to fix OCR artifacts and typos. Designed for human-in-the-loop verification or agent-triggered cleanup.
- **`process_pdf_document`**: A lightweight tool for single-file processing and immediate feedback.

---

## Usage

### 1. Environment Setup
Ensure you have `uv` installed.
```bash
# Clone and install dependencies
uv sync

# Set your API Keys in a .env file
# QWEN_API_KEY, XAI_API_KEY, etc.
```

### 2. Development & Inspection
Run the server with the built-in MCP Inspector to test tools interactively:
```bash
uv run fastmcp dev server.py
```
This opens a browser interface at `http://localhost:5173`.

### 3. Running in Production
Connect this server to your AI client (e.g., Claude Desktop, custom agent):
```bash
uv run python server.py
```

---

## Migration Guide

This project serves as a reference for converting legacy CLI tools into modular MCP pipelines.

### Phase 1: Storage & State
Replace file-passing with a structured database (like SQLite). Use **Job IDs** to manage state and allow tools to operate independently on specific batches.

### Phase 2: Logic Isolation
Isolate core logic into discrete tools. Ensure each tool does one thing well (e.g., OCR, Scrubbing, Normalization) and communicates primarily through database updates.

### Phase 3: Token Economy
Avoid returning large data blocks to the agent. Return status summaries and IDs, keeping the "heavy lifting" on the server.
