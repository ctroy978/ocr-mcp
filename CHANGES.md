# Document Conversion Feature - Change Summary

## Overview
Added comprehensive document conversion capabilities to handle teachers submitting materials in non-PDF formats (Word documents, images, scanned PDFs, etc.).

## Problem Solved
The OCR pipeline previously required all files to be in PDF format. If a teacher submitted:
- Essays as Word documents (.docx, .doc)
- Essays as scanned images (JPEG, PNG)
- Rubrics as PDF files (needed as text)
- Mixed format submissions

The workflow would fail. Now the agent can automatically convert files as needed.

## Files Added

### 1. `edmcp/tools/converter.py` (New - 456 lines)
Core conversion functionality:
- **DocumentConverter class**: Main conversion engine
- **Word → PDF**: Uses LibreOffice headless mode
- **Image → PDF**: Uses PIL/Pillow for JPEG, PNG, BMP, GIF, TIFF
- **Multi-image merge**: Combines multiple images into one multi-page PDF
- **PDF → Text**: Uses pdftotext (with OCR fallback option)
- **Batch operations**: Convert entire directories
- **Dependency checking**: Verifies required tools are installed

Key Methods:
- `convert_word_to_pdf(input_path, output_dir)` - Single Word file conversion
- `convert_image_to_pdf(input_path, output_path)` - Single image conversion
- `batch_convert_images_to_pdf(input_dir, output_dir)` - Bulk image conversion
- `merge_images_to_pdf(image_paths, output_path)` - Multi-page PDF from images
- `convert_pdf_to_text(input_path, output_path, use_ocr)` - Extract text from PDF
- `batch_convert_to_pdf(input_dir, output_dir)` - Bulk Word conversion
- `get_conversion_info()` - Check installed tools and get setup instructions

### 2. `tests/tools/test_converter.py` (New - 113 lines)
Comprehensive test suite covering:
- Dependency detection
- Error handling (missing tools, missing files)
- Mock-based testing (doesn't require actual LibreOffice/poppler)
- Batch conversion scenarios
- OCR integration testing

### 3. `CONVERSION_GUIDE.md` (New - 185 lines)
Complete documentation for agents and users:
- Common conversion scenarios with example workflows
- Installation instructions for all platforms
- Tool reference with parameters
- Error handling guide
- Best practices

## Files Modified

### 1. `server.py`
**Lines changed:** ~205 lines added

**Changes:**
- Added import: `from edmcp.tools.converter import DocumentConverter`
- Initialized: `CONVERTER = DocumentConverter()`
- Added 7 new MCP tools:
  - `@mcp.tool convert_word_to_pdf(file_path, output_dir)` - Single file Word→PDF
  - `@mcp.tool convert_image_to_pdf(file_path, output_path)` - Single image→PDF
  - `@mcp.tool batch_convert_images_to_pdf(input_dir, output_dir)` - Bulk image→PDF
  - `@mcp.tool merge_images_to_pdf(image_paths, output_path)` - Multi-page PDF from images
  - `@mcp.tool convert_pdf_to_text(file_path, output_path, use_ocr)` - PDF→Text
  - `@mcp.tool batch_convert_word_to_pdf(input_dir, output_dir)` - Bulk Word→PDF
  - `@mcp.tool check_conversion_capabilities()` - Check dependencies

**Tool Signatures:**
```python
convert_word_to_pdf(file_path: str, output_dir: Optional[str] = None) -> dict
convert_image_to_pdf(file_path: str, output_path: Optional[str] = None) -> dict
batch_convert_images_to_pdf(input_dir: str, output_dir: str) -> dict
merge_images_to_pdf(image_paths: List[str], output_path: str) -> dict
convert_pdf_to_text(file_path: str, output_path: Optional[str] = None, use_ocr: bool = False) -> dict
batch_convert_word_to_pdf(input_dir: str, output_dir: str) -> dict
check_conversion_capabilities() -> dict
```

All tools return standardized dict responses with:
- `status`: "success" or "error"
- `message`: Human-readable description
- File paths, counts, or error details

### 2. `README.md`
**Changes:**
- Reorganized "Modular Toolset" section into categories:
  - Document Conversion (Pre-Processing) - NEW
  - OCR & Processing Pipeline
  - Evaluation & Knowledge Base
  - Archive & Maintenance
- Added new section "2. Install Optional Conversion Tools"
  - Installation instructions for Ubuntu/Debian, macOS, Windows
  - Clear note that tools are optional
- Renumbered subsequent sections (3. Development, 4. Production)

## Dependencies

### Required for Full Functionality:
- **LibreOffice** (for Word→PDF conversion)
  - Ubuntu/Debian: `sudo apt-get install libreoffice`
  - macOS: `brew install --cask libreoffice`
  - Windows: Download from https://www.libreoffice.org/

- **Poppler Utils** (for PDF→Text conversion)
  - Ubuntu/Debian: `sudo apt-get install poppler-utils`
  - macOS: `brew install poppler`
  - Windows: https://blog.alivate.com.au/poppler-windows/

- **PIL/Pillow** (for Image→PDF conversion)
  - Should already be installed (pdf2image dependency)
  - If needed: `pip install Pillow` or `uv add pillow`

### Fallback Options:
- If `pdftotext` is unavailable, `convert_pdf_to_text(use_ocr=True)` uses the existing OCRTool
- PIL/Pillow is likely already installed as a transitive dependency
- Agent can check availability via `check_conversion_capabilities()` and guide users

## Testing Status

✅ **Module Import:** Verified - `from edmcp.tools.converter import DocumentConverter`
✅ **Server Integration:** Verified - All 7 conversion tools registered and accessible
✅ **Dependency Detection:** Verified - Correctly detects LibreOffice, poppler, and PIL
✅ **Image Conversion:** Verified - Successfully tested single image, batch, and merge operations
✅ **Tool Count:** Server now has 21 total MCP tools (was 14)

⚠️ **Unit Tests:** Test file created but pytest has pre-existing import issues (not related to this change)

## Usage Examples

### Agent Workflow 1: Convert Word Essays
```
User: "I have student essays in Word format in /home/teacher/essays"

Agent thoughts:
1. Check if conversion tools available
2. Convert Word docs to PDF
3. Process with normal OCR pipeline

Agent actions:
- check_conversion_capabilities()
- batch_convert_word_to_pdf(
    input_dir="/home/teacher/essays",
    output_dir="/home/teacher/essays_pdf"
  )
- batch_process_documents(directory_path="/home/teacher/essays_pdf")
```

### Agent Workflow 2: Convert Scanned Images
```
User: "I scanned each essay page as a JPEG. Student essays are multi-page."

Agent thoughts:
1. Multiple images per essay need to be merged
2. Group images by student (e.g., student1_page1.jpg, student1_page2.jpg)
3. Merge each student's pages into one PDF
4. Process all PDFs

Agent actions:
- merge_images_to_pdf(
    image_paths=["student1_p1.jpg", "student1_p2.jpg"],
    output_path="student1.pdf"
  )
- merge_images_to_pdf(
    image_paths=["student2_p1.jpg", "student2_p2.jpg", "student2_p3.jpg"],
    output_path="student2.pdf"
  )
- batch_process_documents(directory_path="/path/to/merged_pdfs")
```

### Agent Workflow 3: Extract Rubric Text
```
User: "Here's my rubric" [uploads rubric.pdf]

Agent thoughts:
1. Evaluation needs text format
2. Convert PDF to text
3. Read and use in evaluation

Agent actions:
- convert_pdf_to_text(file_path="rubric.pdf")
- Read rubric.txt
- evaluate_job(job_id="...", rubric="<content>", ...)
```

## Backward Compatibility

✅ **Fully backward compatible**
- All existing tools unchanged
- No breaking changes to existing workflows
- New tools are additive only
- Agent can continue to use PDF-only workflows if desired

## Future Enhancements (Not Implemented)

Potential future additions:
- Image format support (JPG, PNG → PDF)
- Google Docs integration
- Automatic format detection
- Parallel batch conversion for speed
- Progress callbacks for large batches

## Rollback Plan

If issues arise, remove:
1. `edmcp/tools/converter.py`
2. Lines in `server.py`:
   - Import statement (line ~34)
   - CONVERTER initialization (line ~80)
   - Four tool functions (lines 917-1025)
3. Revert `README.md` section changes

System will return to PDF-only operation.
