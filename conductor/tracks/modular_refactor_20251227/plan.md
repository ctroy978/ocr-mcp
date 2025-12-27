# Track Plan: Refactor for Modularity and Implement OCR & Cleanup Tools

## Phase 1: Modular Framework & Job Management [checkpoint: 39c3182]
- [x] Task: Design and implement the `JobManager` for unique IDs and directory handling 1ebecb6
- [x] Task: Implement common JSONL reader/writer utilities 742ad5c
- [x] Task: Conductor - User Manual Verification 'Phase 1: Modular Framework & Job Management' (Protocol in workflow.md) 39c3182
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Modular Framework & Job Management' (Protocol in workflow.md)

## Phase 2: OCR Tool Implementation
- [x] Task: Write Tests for the modular OCR tool 0561e19
- [x] Task: Implement the OCR tool by refactoring existing logic in `server.py` 809cdfd
- [ ] Task: Conductor - User Manual Verification 'Phase 2: OCR Tool Implementation' (Protocol in workflow.md)

## Phase 3: Cleanup Tool Implementation
- [ ] Task: Write Tests for the Cleanup tool (PII scrubbing & normalization)
- [ ] Task: Implement the Cleanup tool using xAI API
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Cleanup Tool Implementation' (Protocol in workflow.md)

## Phase 4: Integration & Batch Processing
- [ ] Task: Implement a coordinator tool or script to chain OCR and Cleanup
- [ ] Task: Test the pipeline with a batch of 40+ sample essays
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Integration & Batch Processing' (Protocol in workflow.md)
