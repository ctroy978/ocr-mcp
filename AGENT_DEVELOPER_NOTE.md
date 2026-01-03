# Note for AI Agent Developer

## Issue Summary

During testing, the AI agent incorrectly told the user that typed PDFs were being processed with OCR, when in fact they were using fast text extraction. The user complained:

> "these were typed essays. We don't need to use ocr here"

The agent had said:
> "I'm processing them with OCR to extract the text and detect student names."

But the server logs showed:
```
[PDF Extract] 097d8555-1784-4a16-a883-9c5b15f9b7a3.pdf: Text extracted successfully (1170 chars/page)
```

The PDFs were correctly processed using **fast text extraction**, not OCR.

## Root Cause Analysis

The MCP server's tool descriptions were **misleading**. The `batch_process_documents` tool description emphasized OCR-specific parameters (`model`, `dpi`) without clarifying that text extraction is attempted first:

```python
# OLD description
"""
Args:
    model: Qwen model to use (default: env QWEN_API_MODEL or qwen-vl-max)
    dpi: DPI for scanning
"""
```

This caused the agent to infer that OCR was always being used.

## MCP Server Fixes Applied

I've updated the MCP server code to provide clear, accurate information:

### 1. Enhanced Tool Descriptions
Both `batch_process_documents` and `process_pdf_document` now clearly state:

```python
"""
IMPORTANT: This tool automatically detects the PDF type:
- Typed/digital PDFs: Uses FAST text extraction (no OCR, free, instant)
- Scanned/image PDFs: Falls back to OCR (slower, uses AI model)

The return message will clearly indicate which method was used.
"""
```

### 2. Enhanced Return Messages
The tools now return explicit information about which method was used:

**Batch processing:**
```json
{
  "summary": "Processed 3 files (3 via fast text extraction). Found 3 student records...",
  "processing_details": {
    "total_files": 3,
    "text_extraction": 3,
    "ocr": 0
  }
}
```

**Single file processing:**
```json
{
  "processing_method": "Fast text extraction (typed/digital PDF)",
  "used_ocr": false
}
```

## Action Required: Check Agent Code

**Please check if the agent has any hardcoded messaging that assumes OCR is always being used.**

Common places to check:
- Pre-written responses about "processing with OCR"
- Status messages mentioning "OCR extraction"
- Any logic that assumes all PDF processing = OCR

The agent should now **rely on the MCP tool's return messages** to inform the user about which method was used, rather than making assumptions.

## Expected Agent Behavior (After Fix)

**For typed PDFs:**
> "Great! I've processed your 3 typed essays using fast text extraction. Found 3 student records..."

**For scanned PDFs:**
> "I've processed your essays using OCR (since they're scanned/image-based). Found X student records..."

**For mixed batch:**
> "Processed 5 files: 3 via fast text extraction and 2 via OCR. Found 5 student records..."

## Files Changed

- `edmcp/tools/ocr.py` - Updated `process_pdf()` to return processing method metadata
- `server.py` - Updated both tool descriptions and return messages
- `tests/tools/test_ocr.py` - Updated tests to match new return format

---

**Summary:** The MCP server now provides accurate information about processing methods. Please verify the agent isn't overriding this with hardcoded OCR messaging.
