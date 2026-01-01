# Quick Start: Document Conversions

## TL;DR for Agents

When teachers provide non-PDF files, use these tools:

### 1. Single Word → PDF
```
convert_word_to_pdf(file_path="essay.docx")
```

### 2. Batch Word → PDF
```
batch_convert_word_to_pdf(
    input_dir="/path/to/word/files",
    output_dir="/path/to/output"
)
```

### 3. Single Image → PDF
```
convert_image_to_pdf(file_path="essay.jpg")
```

### 4. Batch Images → PDFs (separate)
```
batch_convert_images_to_pdf(
    input_dir="/path/to/images",
    output_dir="/path/to/output"
)
```

### 5. Merge Images → Single PDF (multi-page)
```
merge_images_to_pdf(
    image_paths=["page1.jpg", "page2.jpg", "page3.jpg"],
    output_path="complete_essay.pdf"
)
```

### 6. PDF → Text (native)
```
convert_pdf_to_text(file_path="rubric.pdf")
```

### 7. PDF → Text (scanned/OCR)
```
convert_pdf_to_text(file_path="rubric.pdf", use_ocr=True)
```

### 8. Check Installation
```
check_conversion_capabilities()
```

## Decision Tree

```
What format is the input?
├─ Word (.docx, .doc)
│   ├─ Single file → convert_word_to_pdf()
│   └─ Multiple files → batch_convert_word_to_pdf()
│
├─ Image (.jpg, .png)
│   ├─ Single file → convert_image_to_pdf()
│   ├─ Multiple separate essays → batch_convert_images_to_pdf()
│   └─ Multiple pages of same essay → merge_images_to_pdf()
│
├─ PDF (need as text)
│   ├─ Native/typed PDF → convert_pdf_to_text()
│   └─ Scanned/image PDF → convert_pdf_to_text(use_ocr=True)
│
└─ Already PDF for OCR → Proceed with batch_process_documents()
```

## Installation (if needed)

**Ubuntu/Debian:**
```bash
sudo apt-get install libreoffice poppler-utils
```

**macOS:**
```bash
brew install --cask libreoffice && brew install poppler
```

**Check first:**
```
check_conversion_capabilities()
```

## Common Patterns

### Pattern 1: Mixed Format Directory
```
1. batch_convert_word_to_pdf(input_dir, output_dir)
2. Copy existing PDFs to output_dir
3. batch_process_documents(output_dir)
```

### Pattern 2: PDF Rubric for Evaluation
```
1. convert_pdf_to_text("rubric.pdf")
2. Read "rubric.txt"
3. evaluate_job(job_id, rubric=<text>, ...)
```

### Pattern 3: Scanned Images (Multi-page Essay)
```
1. merge_images_to_pdf(["p1.jpg", "p2.jpg", "p3.jpg"], "essay.pdf")
2. process_pdf_document("essay.pdf")
3. Continue with normal workflow
```

### Pattern 4: Safe Conversion
```
1. check_conversion_capabilities() # Verify tools installed
2. Convert if available, else guide user to install
3. Proceed with workflow
```
