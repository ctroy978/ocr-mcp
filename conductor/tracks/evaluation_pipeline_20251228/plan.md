# Track Plan: Evaluation Pipeline

## Phase 1: Database Schema Updates [checkpoint: f7b6f89]
- [x] Task: Update `DatabaseManager` to include `evaluation` and `grade` columns in `essays` table d3375f4
- [x] Task: Migrate existing database (add columns if missing) d3375f4
- [x] Task: Conductor - User Manual Verification 'Phase 1: Database Schema Updates' (Protocol in workflow.md) 2576c58

## Phase 2: Evaluation Tool Implementation [checkpoint: daa0aa9]
- [x] Task: Design the Evaluation Prompt structure (Essay + Rubric + Context) 09c9b43
- [x] Task: Write Tests for `evaluate_job` logic (mocking AI) 1cabef6
- [x] Task: Implement `evaluate_job` tool in `server.py` 1cabef6
- [x] Task: Conductor - User Manual Verification 'Phase 2: Evaluation Tool Implementation' (Protocol in workflow.md) d388dea

## Phase 3: Integration & Testing [checkpoint: 2cf215c]
- [x] Task: Create a full end-to-end test script (OCR -> Scrub -> Evaluate) 8eeb1a7
- [x] Task: Conductor - User Manual Verification 'Phase 3: Integration & Testing' (Protocol in workflow.md) 8eeb1a7
