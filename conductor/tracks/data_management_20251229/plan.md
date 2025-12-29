# Track Plan: Data Management & Cleanup

## Phase 1: Database & Knowledge Core
- [x] Task: Add `delete_job(job_id)` method to `DatabaseManager` in `edmcp/core/db.py` (ensure cascading delete of essays).
- [x] Task: Add `delete_topic(topic)` method to `KnowledgeBaseManager` in `edmcp/core/knowledge.py`.
- [x] Task: Conductor - User Manual Verification 'Phase 1: Database & Knowledge Core' (Protocol in workflow.md)

## Phase 2: Tool Implementation
- [x] Task: Create `edmcp/tools/cleanup.py` (or add to `server.py`).
- [x] Task: Implement `cleanup_old_jobs` tool with logic to check date diffs and delete DB records + directories.
- [x] Task: Implement `delete_knowledge_topic` tool.
- [x] Task: Conductor - User Manual Verification 'Phase 2: Tool Implementation' (Protocol in workflow.md)

## Phase 3: Integration & Testing
- [x] Task: Register new tools in `server.py`.
- [x] Task: Create `tests/tools/test_cleanup_tool.py` to verify:
    - Jobs older than threshold are deleted.
    - Jobs newer than threshold are kept.
    - Directories are removed.
    - Topics are removed from ChromaDB.
- [x] Task: Conductor - User Manual Verification 'Phase 3: Integration & Testing' (Protocol in workflow.md)
