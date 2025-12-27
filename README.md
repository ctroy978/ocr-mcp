# OCR-MCP Server

## Project Overview

This project implements a **Model Context Protocol (MCP)** server for batch OCR processing of student documents. It is a modernization of a legacy CLI tool (`batchocr`), refactored to work seamlessly with AI agents while maintaining the efficiency required for processing large batches of files.

**Key Technology Stack:**
- **FastMCP:** For rapid server development.
- **Qwen-VL:** Replaces Google Vision for superior handwritten text recognition via an OpenAI-compatible API.
- **UV:** For blazing fast, reproducible dependency management.
- **PDF2Image & Regex:** Preserved legacy logic for robust document parsing.

---

## Architecture: The "Heavy Lifter" Pattern

This server is designed to handle high-volume data (e.g., 40+ student essays) without flooding the AI agent's context window.

1.  **Agent Request:** The agent triggers `batch_process_documents` pointing to a directory.
2.  **Server Processing:** The server processes the files locally, performing OCR and logic aggregation.
3.  **Structured Output:** Results are streamed to a **JSONL** file on the local filesystem.
    - Each batch gets a unique **Job ID**.
    - Each record in the file is tagged with this `job_id` for traceability.
4.  **Lightweight Response:** The server returns *only* a summary to the agent (e.g., "Job `job_123` complete. 40 files processed. Output at `/tmp/out/job_123.jsonl`").
5.  **Chaining:** The agent can pass this file path to downstream tools for further analysis.

---

## Usage

### 1. Environment Setup
Ensure you have `uv` installed.
```bash
# Clone and install dependencies
uv sync

# Set your API Key
export QWEN_API_KEY="your_key_here"
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

## Migration Guide (Template for Future Tools)

Use this "Recipe" to convert other legacy CLI tools in this suite into MCP servers.

### Phase 1: Environment & Dependencies (UV)
1.  **Initialize:** Start with a fresh `uv` project or add to the existing workspace.
    ```bash
    uv init
    uv add fastmcp
    ```
2.  **Port Dependencies:** Identify the *critical* libraries from the old tool (e.g., `pandas`, `scipy`) and add them using `uv`.
    - *Tip:* Remove obsolete dependencies (like we replaced `google-cloud-vision` with `openai` for Qwen).

### Phase 2: Logic Extraction (Refactor)
1.  **Isolate Core Logic:** Move the main processing code into helper functions (e.g., `_process_core(...)`) that return raw data structures (dicts/lists), NOT text output.
2.  **Remove CLI Artifacts:** Strip out `argparse`, `sys.stdout.write`, and manual logging. The MCP server handles input/output.
3.  **Preserve Business Logic:** Keep critical regex patterns, math formulas, or data transformations exactly as they were to ensure consistency.

### Phase 3: Tool Design (Token Economy)
1.  **Atomic Tools:** Create simple wrappers for single-item operations (good for debugging).
2.  **Batch Tools (Crucial):** For tools handling large datasets:
    - **Input:** Accept `directory_path` and `output_directory`.
    - **Process:** Iterate and process internally.
    - **Output:** Write results to a persistent file (JSONL/CSV).
    - **Return:** Return a dictionary with:
        - `status`: "success"
        - `job_id`: A unique ID for the run.
        - `summary`: "Processed X items."
        - `output_file`: Path to the generated data.
    - **Traceability:** Inject the `job_id` into every record in the file.

### Phase 4: Verification
1.  **Check Dependencies:** Run `uv sync` to lock versions.
2.  **Inspect:** Use `uv run fastmcp dev server.py` to manually verify the tools.
3.  **Test:** Ensure the output files are generated correctly and the agent receives the correct file paths.