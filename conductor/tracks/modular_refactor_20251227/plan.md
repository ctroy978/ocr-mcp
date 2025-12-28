# Track Plan: Refactor for Modularity and Implement OCR & Cleanup Tools

## Phase 1: Modular Framework & Job Management [checkpoint: 39c3182]
- [x] Task: Design and implement the `JobManager` for unique IDs and directory handling 1ebecb6
- [x] Task: Implement common JSONL reader/writer utilities 742ad5c
- [x] Task: Conductor - User Manual Verification 'Phase 1: Modular Framework & Job Management' (Protocol in workflow.md) 39c3182
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Modular Framework & Job Management' (Protocol in workflow.md)

## Phase 2: OCR Tool Implementation [checkpoint: ba0cc83]
- [x] Task: Write Tests for the modular OCR tool 0561e19
- [x] Task: Implement the OCR tool by refactoring existing logic in `server.py` 809cdfd
- [x] Task: Conductor - User Manual Verification 'Phase 2: OCR Tool Implementation' (Protocol in workflow.md) ba0cc83

## Phase 3: Database Infrastructure & Migration [checkpoint: 84133c2]
- [x] Task: Design and implement `DatabaseManager` with SQLite schema (jobs, essays) 0094a68
- [x] Task: Refactor `JobManager` to utilize `DatabaseManager` cbdcb76
- [x] Task: Refactor `OCRTool` (server.py logic) to write results to SQLite eb9ea15
- [x] Task: Update `Scrubber` integration to read/write from SQLite ce61bd1
- [x] Task: Conductor - User Manual Verification 'Phase 3: Database Infrastructure & Migration' (Protocol in workflow.md) d54da71
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Database Infrastructure & Migration' (Protocol in workflow.md)

## Phase 4: Cleanup Tool (Normalization) [checkpoint: 2fc410c]
- [x] Task: Write Tests for the Cleanup tool (Normalization logic) 00ce8be
- [x] Task: Implement the Cleanup tool using xAI API for text normalization (typo fixing) 00ce8be
- [x] Task: Conductor - User Manual Verification 'Phase 4: Cleanup Tool (Normalization)' (Protocol in workflow.md) 656fb73

## Phase 5: Integration & Batch Processing [checkpoint: 2cf215c]
- [x] Task: Implement a coordinator tool to manage the DB-driven pipeline (Handled by Evaluation Pipeline) 8eeb1a7
- [x] Task: Test the full pipeline (OCR -> Scrub -> Normalize) with sample data 8eeb1a7
- [x] Task: Conductor - User Manual Verification 'Phase 5: Integration & Batch Processing' (Protocol in workflow.md) 8eeb1a7
