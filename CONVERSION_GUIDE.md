# Document Conversion Guide

This guide explains how to use the document conversion tools when teachers submit materials in non-PDF formats.

## Common Scenarios

### Scenario 1: Teacher Submits Essays as Word Documents

**Problem:** The OCR pipeline requires PDFs, but the teacher has a folder of `.docx` files.

**Solution:**

1. **Check conversion capabilities first:**
   ```
   Agent: Use check_conversion_capabilities()
   ```
   
2. **Convert a single Word document:**
   ```
   Agent: Use convert_word_to_pdf(file_path="/path/to/essay.docx")
   ```
   
3. **Batch convert a directory of Word documents:**
   ```
   Agent: Use batch_convert_word_to_pdf(
       input_dir="/path/to/word_essays",
       output_dir="/path/to/converted_pdfs"
   )
   ```
   
4. **Then proceed with normal workflow:**
   ```
   Agent: Use batch_process_documents(directory_path="/path/to/converted_pdfs")
   ```

---

### Scenario 2: Teacher Provides Rubric as a PDF

**Problem:** The `evaluate_job` tool works best with text rubrics, but the teacher uploaded a PDF.

**Solution:**

1. **Convert PDF rubric to text:**
   ```
   Agent: Use convert_pdf_to_text(file_path="/path/to/rubric.pdf")
   ```
   
   If the PDF is scanned/image-based:
   ```
   Agent: Use convert_pdf_to_text(file_path="/path/to/rubric.pdf", use_ocr=True)
   ```

2. **Read the text file:**
   ```
   Agent: Read the generated .txt file
   ```

3. **Use in evaluation:**
   ```
   Agent: Use evaluate_job(job_id="...", rubric="<content from txt file>", ...)
   ```

---

### Scenario 3: Teacher Submits Essays as Scanned Images

**Problem:** Teacher scanned physical essays as individual JPEG or PNG files.

**Solution A: Convert each image to a separate PDF** (one essay per image)
```
Agent: Use batch_convert_images_to_pdf(
    input_dir="/path/to/scanned_images",
    output_dir="/path/to/pdf_output"
)
Then: batch_process_documents(directory_path="/path/to/pdf_output")
```

**Solution B: Merge multiple images into one PDF** (multi-page essay)
```
Agent: Use merge_images_to_pdf(
    image_paths=[
        "/path/to/essay_page1.jpg",
        "/path/to/essay_page2.jpg",
        "/path/to/essay_page3.jpg"
    ],
    output_path="/path/to/complete_essay.pdf"
)
Then: process_pdf_document(pdf_path="/path/to/complete_essay.pdf")
```

---

### Scenario 4: Mixed Format Submissions

**Problem:** Teacher has Word, PDF, and image files mixed together.

**Workflow:**

1. **Separate and convert by type:**
   - Word files (`.doc`, `.docx`) → `batch_convert_word_to_pdf()`
   - Image files (`.jpg`, `.png`) → `batch_convert_images_to_pdf()`
   - PDF files → Keep as-is

2. **Copy existing PDFs to output directory:**
   ```
   Agent: Use bash to copy PDF files
   ```

3. **Process all PDFs:**
   ```
   Agent: Use batch_process_documents(directory_path="/path/to/pdf_output")
   ```

---

## Installation Requirements

### Ubuntu/Debian
```bash
sudo apt-get install libreoffice poppler-utils
```

### macOS
```bash
brew install --cask libreoffice
brew install poppler
```

### Windows
- LibreOffice: https://www.libreoffice.org/download/
- Poppler: https://blog.alivate.com.au/poppler-windows/

### Python Dependencies
**PIL/Pillow** (for image conversions) should already be installed as `pdf2image` depends on it. If needed:
```bash
pip install Pillow
# or with uv
uv add pillow
```

---

## Tool Reference

### `check_conversion_capabilities()`
- **Purpose:** Checks if conversion tools are installed
- **Returns:** Status and installation instructions
- **When to use:** At the start of any workflow involving non-PDF files

### `convert_word_to_pdf(file_path, output_dir=None)`
- **Purpose:** Converts a single Word document to PDF
- **Supports:** `.doc`, `.docx`
- **Returns:** Path to generated PDF

### `batch_convert_word_to_pdf(input_dir, output_dir)`
- **Purpose:** Converts all Word documents in a directory
- **Supports:** `.doc`, `.docx` (case-insensitive)
- **Returns:** List of converted PDF paths

### `convert_pdf_to_text(file_path, output_path=None, use_ocr=False)`
- **Purpose:** Extracts text from PDF
- **Options:**
  - `use_ocr=False`: Uses `pdftotext` (fast, for native text PDFs)
  - `use_ocr=True`: Uses Qwen-VL OCR (slower, for scanned/image PDFs)
- **Returns:** Path to generated text file

### `convert_image_to_pdf(file_path, output_path=None)`
- **Purpose:** Converts a single image to PDF
- **Supports:** `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`, `.tiff`
- **Returns:** Path to generated PDF

### `batch_convert_images_to_pdf(input_dir, output_dir)`
- **Purpose:** Converts all images in a directory to individual PDFs
- **Supports:** `.jpg`, `.jpeg`, `.png` (case-insensitive)
- **Returns:** List of converted PDF paths
- **Note:** Each image becomes a separate single-page PDF

### `merge_images_to_pdf(image_paths, output_path)`
- **Purpose:** Merges multiple images into one multi-page PDF
- **Supports:** Any image format (`.jpg`, `.png`, etc.)
- **Use case:** Combining scanned essay pages into a single document
- **Returns:** Path to the merged PDF
- **Note:** Images are merged in the order provided in the list

---

## Error Handling

### "LibreOffice is not installed"
**Solution:** Install LibreOffice (see Installation Requirements above)

### "pdftotext is not installed"
**Solution:** Either:
1. Install poppler-utils (see Installation Requirements)
2. Use `use_ocr=True` parameter instead

### "Conversion appeared to succeed but output file not found"
**Possible causes:**
- LibreOffice failed silently (check disk space)
- File permissions issue
- Unsupported Word document format (very old .doc files)

---

## Best Practices

1. **Always check capabilities first:**
   - Prevents runtime errors
   - Provides clear user guidance

2. **Preserve original files:**
   - Convert to a separate output directory
   - Don't overwrite teacher's originals

3. **Verify conversion success:**
   - Check that PDF files were created
   - Verify file sizes are reasonable (not 0 bytes)

4. **Choose the right text extraction method:**
   - Use `pdftotext` (default) for typed/native PDFs
   - Use `use_ocr=True` only for scanned documents

5. **Batch when possible:**
   - More efficient than converting files one-by-one
   - Provides summary of all conversions
