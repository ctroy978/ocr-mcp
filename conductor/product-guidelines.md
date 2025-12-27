# Product Guidelines

## Architectural Principles
- **Loose Coupling & Independence:** Tools must be designed as discrete units that communicate solely through standardized JSONL packages. Each tool should perform exactly one task (e.g., OCR, Cleanup, Evaluation).
- **Stateless Operation:** Tools must not maintain state between executions. All necessary context for a job must be contained within the input JSONL file and the uniquely identified job directory.
- **Fail-Fast Validation:** Each tool must validate its input immediately. If a fatal error occurs that prevents the tool from performing its core function, it should halt and report the error to avoid contaminating the pipeline.

## Data Handoff Protocol
- **JSONL Extensibility:** The JSONL format is the primary medium for data exchange. While common fields (like `job_id`) are required, tools should be able to append new data fields dynamically to support evolving requirements (e.g., an Evaluation tool adding scores to an OCR-generated record).
- **Unique Job Directories:** All handoffs must occur within a directory named with a unique Job ID. This prevents data mix-ups and allows for clean cleanup of finished jobs.

## Error Handling & Reliability
- **Isolated Error Reporting:** Errors encountered during processing should be logged to a dedicated error file (e.g., `errors.jsonl`) within the job directory, keeping the primary data file clean.
- **Graceful Batch Processing:** The failure of an individual record (e.g., one essay failing OCR) should not crash the entire batch job. The system should skip the failed record, log the error, and continue processing the remaining items.

## Privacy & Security
- **PII Scrubbing:** Before student essays are sent to any external AI APIs (like Qwen-VL or LLMs for evaluation), names and other personally identifiable information must be scrubbed using provided name lists to ensure student privacy.
- **Data Minimization:** Only the essential data required for each processing step should be extracted and transmitted.

## Performance & Concurrency
- **Resource Management:** To ensure system stability, the number of parallel workers must be capped. Processing should be handled in manageable chunks or throttled to avoid overwhelming system resources or external API rate limits.
- **Transparency:** The system should provide feedback to the user regarding the expected processing time for large batches, acknowledging that accuracy and reliability are prioritized over raw speed.
