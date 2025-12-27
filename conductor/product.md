# OCR-MCP Server & Essay Grading Pipeline

## Initial Concept
Modular FastMCP system for automated essay grading and reporting.

## Product Vision
A modular, high-scale system for automated essay grading that evolves the initial OCR prototype into a robust pipeline. The system decomposes the workflow into specialized tools (OCR, cleanup, evaluation, reporting, email) that operate independently and hand off data via structured JSONL packages, allowing for efficient processing of large batches (40+ essays) and potential distributed execution.

## Target Users
- **AI Agents:** Designed for agents to orchestrate a complex, multi-stage grading workflow by invoking specific tools as needed.

## Core Goals
- **Modularity:** Refactor the existing monolithic test server into discrete, single-purpose tools (OCR, Cleanup, Evaluation, Reporting, Email).
- **Scalable Pipeline:** Enable efficient handling of large batches (40+ essays) with a robust file-based handoff mechanism using unique IDs.
- **Performance:** Support concurrent or distributed processing ("broadcasting") to minimize latency for large jobs.
- **Extensibility:** Allow for multiple evaluation tools and custom rubrics.

## Key Features
- **Specialized Toolchain:**
    - **OCR Tool:** Extracts text from handwritten essays.
    - **Cleanup Tool:** Normalizes and prepares text for analysis.
    - **Evaluation Tools:** Pluggable modules for scoring based on custom rubrics.
    - **Report Tool:** Generates formatted grade reports.
    - **Email Tool:** Distributes reports to students and teachers.
- **JSONL Handoff Protocol:** Standardized intermediate data format (JSONL) stored in uniquely identified folders to manage state between tool executions.
- **Distributed Processing:** Architecture supports broadcasting tasks to multiple workers/servers to speed up batch processing.
