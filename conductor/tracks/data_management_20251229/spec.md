# Track Spec: Data Management & Cleanup

## Overview
This track implements tools to manage the lifecycle of data within the EDMCP system. As the system processes more jobs and ingests more knowledge, a mechanism is needed to purge old student data and manually remove obsolete reference materials.

## Requirements

### 1. Job Lifecycle Management
- **Goal:** Automatically purge student data that is no longer needed for active grading or disputes.
- **Policy:** **7-Month Retention (210 Days)**.
    - Jobs older than 210 days (based on `created_at`) will be targeted for deletion.
- **Scope of Deletion:**
    - **Database:** Remove the `jobs` record and all associated `essays`.
    - **Filesystem:** Recursively delete the `data/jobs/{job_id}` directory.
- **Tool:** `cleanup_old_jobs(retention_days: int = 210, dry_run: bool = False)`
    - *dry_run:* If True, returns a list of what *would* be deleted without taking action.

### 2. Knowledge Base Management
- **Goal:** Allow manual removal of RAG collections that are no longer relevant (e.g., last year's curriculum).
- **Policy:** **Manual Deletion Only**. Reference materials persist until explicitly removed.
- **Scope of Deletion:**
    - **Vector Store:** Delete the specific ChromaDB collection.
- **Tool:** `delete_knowledge_topic(topic: str)`

## Technical Implementation
- **Location:** New tool module `edmcp/tools/cleanup.py` or extend `server.py`.
- **Database:** `DatabaseManager` needs a `delete_job(job_id)` method.
- **Knowledge:** `KnowledgeBaseManager` needs a `delete_topic(topic)` method.
