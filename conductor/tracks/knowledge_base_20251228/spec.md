# Track Spec: Knowledge Base Integration (RAG)

## Overview
Implement a local Retrieval-Augmented Generation (RAG) system using `llama-index` to allow instructors to upload reference materials (PDFs, Text). These materials will serve as "context" for the `evaluate_job` tool, ensuring the AI evaluates student essays against accurate subject matter.

## Goals
1.  **Local & Private:** Use local embeddings (`HuggingFaceEmbeddings`) to keep data secure and avoid extra API costs for embeddings.
2.  **Simple Management:** Tools to easy `add` files and `query` information.
3.  **Agent-Driven:** The Agent acts as the bridge, deciding when to fetch context to pass to the evaluator.

## Architecture

### 1. `KnowledgeBaseManager`
- **Library:** `llama-index` (core), `langchain-huggingface` (embeddings).
- **Storage:** Persist indices locally in `./edmcp.db_vector_store` (or similar folder).
- **Model:** `sentence-transformers/all-MiniLM-L6-v2` (Fast, lightweight, effectively standard for local CPU).

### 2. New MCP Tools
- **`add_to_knowledge_base(files: List[str], topic: str)`**
  - **Input:** List of file paths, a `topic` (collection name) to organize data.
  - **Process:**
    1.  Load documents.
    2.  Split into chunks.
    3.  Generate embeddings (locally).
    4.  Save to vector store under `topic`.
  
- **`query_knowledge_base(query: str, topic: str)`**
  - **Input:** Natural language query (e.g., "Summary of 'The Road Not Taken'"), `topic`.
  - **Process:**
    1.  Embed query.
    2.  Search vector store.
    3.  Return top k text chunks.

## Workflow Example
1.  **User:** "Here is the textbook chapter on Thermodynamics." -> `add_to_knowledge_base`
2.  **User:** "Grade these essays on Entropy. Use the textbook."
3.  **Agent:** 
    - Calls `query_knowledge_base("Explain Entropy and the Second Law", topic="textbook")`.
    - Receives text chunks.
    - Calls `evaluate_job(rubric=..., context=retrieved_chunks)`.

## Dependencies
- `llama-index`
- `llama-index-embeddings-huggingface`
- `sentence-transformers`
