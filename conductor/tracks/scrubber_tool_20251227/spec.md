# Track Spec: Scrubber Tool

## Overview
The Scrubber Tool is a local privacy-preserving component designed to remove student names from essays before they are sent to external AI APIs for cleanup and evaluation.

## Requirements
- **Input:** JSONL from OCR tool.
- **Output:** JSONL with redacted text.
- **Scope:** Scrubbing is restricted to the first 20 lines of text.
- **Data Sources:** 
    - `school_names.csv`: List of current students.
    - `common_names.csv`: List of common first/last names (Romanized).
- **Replacement:** Detected names will be replaced with `[STUDENT_NAME]`.

## Matching Logic
- **Case-Insensitivity:** Matching must ignore case (e.g., "john" matches "John").
- **Atomic Scrubbing:** First and last names are treated independently. If "John Doe" is in the list, both "John" and "Doe" should be scrubbed individually wherever they appear in the target zone.

## Technical Details
- **Location:** `edmcp/tools/scrubber.py`
- **Lists:** `edmcp/data/names/*.csv`