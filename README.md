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
- **`get_job_statistics`**: Returns a manifest (student names, page counts, word counts) for a job. Critical for verifying correct page aggregation before scrubbing.
- **`scrub_processed_job`**: Automatically redacts student names and PII using pre-defined CSV name lists.
- **`normalize_processed_job`**: (Optional) Uses AI to fix OCR artifacts and typos. Designed for human-in-the-loop verification or agent-triggered cleanup.
- **`process_pdf_document`**: A lightweight tool for single-file processing and immediate feedback.
- **`evaluate_job`**: Grades student essays based on a provided rubric and context material.
- **`add_to_knowledge_base`**: Ingests reference materials (textbooks, rubrics) into a local vector store.
- **`query_knowledge_base`**: Retrieves relevant context chunks for a specific topic/query.

---

## Human-in-the-Loop Inspection

This pipeline prioritizes user control over "black box" automation.

1.  **OCR & Pause:** `batch_process_documents` runs the heavy OCR workload but **does not** automatically proceed to scrubbing. It returns a summary status.
2.  **Inspection (Optional but Recommended):** The Agent (or User) can call `get_job_statistics(job_id)` to view a manifest of the results.
    *   *Verify:* Did we find 15 students as expected?
    *   *Check:* Are any essays suspiciously long (implying a merge error) or short?
3.  **Proceed:** Once validated, the user triggers `scrub_processed_job` to sanitize the data before it is sent to any external evaluation model.

---

## Data Lifecycle & Maintenance

To ensure compliance and manage disk space, the system includes tools for data purging.

### Retention Policy
*   **Student Data (Jobs):** Retained for **7 months (210 days)**. This covers a standard academic semester plus the subsequent grade dispute period.
*   **Knowledge Base (Topics):** Retained indefinitely until manually deleted.

### Maintenance Workflow
This server does not run background cron jobs. Maintenance is **Agent-Driven**.

**Recommended Schedule:** Run weekly (e.g., Sunday nights).
1.  **Agent Instruction:** "Run system maintenance."
2.  **Tool Call:** `cleanup_old_jobs(retention_days=210)`
    *   This deletes the database records and physical files for all expired jobs.
3.  **Manual Cleanup:** To remove obsolete textbooks or rubrics, use `delete_knowledge_topic(topic="Old_Curriculum")`.

---

## RAG & Evaluation Workflow

This system supports **Retrieval-Augmented Generation (RAG)** to provide "Just-in-Time" context for grading essays.

### The "Agent Bridge" Pattern
Unlike monolithic tools, we decouple **Retrieval** from **Evaluation**. The AI Agent acts as the intelligent bridge between these two steps.

#### Note for Agent Design (LangGraph / Orchestrator)
**How does the Agent know what to query?**
The Agent must derive the search query dynamically from the instructor's instructions or the rubric itself.

**Recommended Workflow:**
1.  **Analyze Request:** The Agent receives a prompt: *"Grade these essays on Frost using the 'Poetry 101' textbook."*
2.  **Formulate Query:** The Agent extracts the key subject matter.
    *   *Self-Correction:* If the prompt is vague (e.g., "Grade this"), the Agent should ask the user for context or a rubric.
    *   *Extraction:* "Search for 'Frost themes', 'Mending Wall analysis', 'Road Not Taken summary'."
3.  **Retrieve Context:** Call `query_knowledge_base(query="Frost themes...", topic="Poetry 101")`.
4.  **Inject Context:** Pass the *retrieved text* into the `context_material` argument of the `evaluate_job` tool.

**Why this separation?**
*   **Flexibility:** The Agent can query the knowledge base multiple times or refine its search before grading.
*   **Transparency:** The User can see exactly what "facts" the Agent retrieved before they are used for grading.

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
