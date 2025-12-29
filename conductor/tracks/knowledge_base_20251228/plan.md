# Track Plan: Knowledge Base Integration

## Phase 1: Environment & Dependencies
- [x] Task: Add `llama-index`, `llama-index-embeddings-huggingface`, `sentence-transformers` to `pyproject.toml`.
- [x] Task: Verify installation and environment compatibility.

## Phase 2: Core Logic (`KnowledgeBaseManager`)
- [x] Task: Create `edmcp/core/knowledge.py`.
- [x] Task: Implement `initialize_index` (load/create persistent store).
- [x] Task: Implement `ingest_documents` (load PDF/Text -> Embed -> Save).
- [x] Task: Implement `query_index` (Retrieve chunks).

## Phase 3: MCP Tool Integration
- [x] Task: Create `edmcp/tools/knowledge.py` or update `server.py` with new tools.
- [x] Task: Implement `add_to_knowledge_base` tool.
- [x] Task: Implement `query_knowledge_base` tool.

## Phase 4: Verification
- [x] Task: Create a test script `verify_rag.py`.
- [x] Task: Test: Ingest a sample PDF.
- [x] Task: Test: Query the PDF for specific facts.
- [x] Task: Test: Combine with `evaluate_job` (Simulated workflow).