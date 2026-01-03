#!/usr/bin/env python
"""
FastMCP server implementation for OCR document processing using Qwen AI.
Replaces the original batchocr CLI (Google Vision) with Qwen-VL via OpenAI compatible API.
"""

from __future__ import annotations

import base64
import io
import os
import sys
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, List, Any

import regex
from fastmcp import FastMCP
from pdf2image import convert_from_path
from openai import (
    OpenAI,
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
)
from dotenv import load_dotenv, find_dotenv

from edmcp.core.name_loader import NameLoader
from edmcp.tools.scrubber import Scrubber, ScrubberTool
from edmcp.tools.ocr import OCRTool
from edmcp.tools.cleanup import CleanupTool
from edmcp.tools.archive import ArchiveTool
from edmcp.tools.converter import DocumentConverter
from edmcp.core.db import DatabaseManager
from edmcp.core.job_manager import JobManager
from edmcp.core.prompts import get_evaluation_prompt
from edmcp.core.knowledge import KnowledgeBaseManager
from edmcp.core.report_generator import ReportGenerator
from edmcp.core.utils import retry_with_backoff, extract_json_from_text
from edmcp.core.student_roster import StudentRoster
from edmcp.core.email_sender import EmailSender
from edmcp.tools.emailer import EmailerTool
from edmcp.tools.name_fixer import NameFixerTool

# Define common AI exceptions for retries
AI_RETRIABLE_EXCEPTIONS = (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    InternalServerError,
)

# Load environment variables from .env file
load_dotenv(find_dotenv())

# Constants from original batchocr
NAME_HEADER_PATTERN = regex.compile(
    r"(?im)^\s*(?:name|id)\s*[:\-]\s*([\p{L}][\p{L}'-]*(?:\s+[\p{L}][\p{L}'-]*)?)"
)
CONTINUE_HEADER_PATTERN = regex.compile(r"(?im)^\s*continue\s*[:\-]\s*(.+)$")

# Initialize Scrubber and Student Roster
NAMES_DIR = Path(__file__).parent / "edmcp/data/names"
loader = NameLoader(NAMES_DIR)
all_names = loader.load_all_names()
SCRUBBER = Scrubber(all_names)

# Load full student names for detection (e.g., "pfour six")
STUDENT_ROSTER = loader.load_full_student_names()
print(f"[DEBUG] Loaded {len(STUDENT_ROSTER)} students into roster: {sorted(list(STUDENT_ROSTER)[:5])}...", file=sys.stderr)

# Initialize DB and JobManager
# Use paths relative to this server.py file, not current working directory
SERVER_DIR = Path(__file__).parent
DB_PATH = SERVER_DIR / "edmcp.db"
JOBS_DIR = SERVER_DIR / "data/jobs"
DB_MANAGER = DatabaseManager(DB_PATH)
JOB_MANAGER = JobManager(JOBS_DIR, DB_MANAGER)
KB_MANAGER = KnowledgeBaseManager(str(SERVER_DIR / "data/vector_store"))
REPORT_GENERATOR = ReportGenerator(str(SERVER_DIR / "data/reports"), db_manager=DB_MANAGER)

# Initialize Email Components
STUDENT_ROSTER_WITH_EMAILS = StudentRoster(NAMES_DIR)
EMAIL_SENDER = EmailSender(
    smtp_host=os.environ.get("SMTP_HOST", "smtp-relay.brevo.com"),
    smtp_port=int(os.environ.get("SMTP_PORT", "587")),
    smtp_user=os.environ.get("SMTP_USER", ""),
    smtp_pass=os.environ.get("SMTP_PASS", ""),
    from_email=os.environ.get("FROM_EMAIL", ""),
    from_name=os.environ.get("FROM_NAME", "Grade Reports"),
    use_tls=os.environ.get("SMTP_TLS", "true").lower() == "true"
)
EMAILER_TOOL = EmailerTool(DB_MANAGER, REPORT_GENERATOR, STUDENT_ROSTER_WITH_EMAILS, EMAIL_SENDER)

# Initialize Name Fixer Tool
NAME_FIXER_TOOL = NameFixerTool(DB_MANAGER, STUDENT_ROSTER_WITH_EMAILS, REPORT_GENERATOR)

# Initialize Cleanup Tool
CLEANUP_TOOL = CleanupTool(DB_MANAGER, KB_MANAGER, JOB_MANAGER)

# Initialize Archive Tool
ARCHIVE_TOOL = ArchiveTool(DB_MANAGER, JOB_MANAGER, REPORT_GENERATOR)

# Initialize Document Converter
CONVERTER = DocumentConverter()

# Initialize the FastMCP server
mcp = FastMCP("OCR-MCP Server")


@dataclass
class PageResult:
    number: int
    text: str
    detected_name: Optional[str]
    continuation_name: Optional[str]


@dataclass
class TestAggregate:
    student_name: str
    start_page: int
    end_page: int
    parts: list[str]

    def append_page(self, text: str, page_number: int) -> None:
        self.parts.append(text)
        if page_number < self.start_page:
            self.start_page = page_number
        if page_number > self.end_page:
            self.end_page = page_number

    def to_json_record(self, original_pdf: str) -> dict:
        return {
            "student_name": self.student_name,
            "text": "\n\n".join(self.parts),
            "metadata": {
                "original_pdf": original_pdf,
                "start_page": self.start_page,
                "end_page": self.end_page,
                "page_count": self.end_page - self.start_page + 1,
            },
        }


def detect_name(text: str) -> Optional[str]:
    """Detect student name in the top portion of the OCR text."""
    # Limit search to the first ~10 lines to reduce false positives deeper in the page.
    lines = text.splitlines()[:10]
    top_section = "\n".join(lines)



    # First, try the traditional "Name:" or "ID:" pattern
    match = NAME_HEADER_PATTERN.search(top_section)
    if match:

        return match.group(1).strip()

    # If no match, check each line against the student roster
    for i, line in enumerate(lines, 1):
        # Normalize the line for case-insensitive comparison
        normalized_line = regex.sub(r"\s+", " ", line.strip()).casefold()

        # Check if this line matches any full student name in the roster
        if normalized_line in STUDENT_ROSTER:

            # Return the original case from the line
            return line.strip()


    return None


def detect_continuation_name(text: str) -> Optional[str]:
    """Detect CONTINUE markers that reference the original student name."""
    top_section = "\n".join(text.splitlines()[:10])
    match = CONTINUE_HEADER_PATTERN.search(top_section)
    if match:
        return match.group(1).strip()
    return None


def aggregate_tests(
    pages: Iterable[PageResult], *, unknown_prefix: str = "Unknown Student"
) -> list[TestAggregate]:
    aggregates: list[TestAggregate] = []
    current: Optional[TestAggregate] = None
    unknown_counter = 0
    aggregates_by_name: dict[str, TestAggregate] = {}
    pending_by_name: dict[str, list[PageResult]] = {}

    def normalize_name(name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        collapsed = regex.sub(r"\s+", " ", name).strip()
        if not collapsed:
            return None
        return collapsed.casefold()

    def attach_pending(name_key: Optional[str], aggregate: TestAggregate) -> None:
        if not name_key:
            return
        pending_pages = pending_by_name.pop(name_key, [])
        for pending_page in sorted(pending_pages, key=lambda item: item.number):
            aggregate.append_page(pending_page.text, pending_page.number)

    for page in pages:
        if page.continuation_name:
            continuation_key = normalize_name(page.continuation_name)
            target = (
                aggregates_by_name.get(continuation_key) if continuation_key else None
            )
            if target is not None:
                target.append_page(page.text, page.number)
            else:
                if continuation_key:
                    pending_by_name.setdefault(continuation_key, []).append(page)
                else:
                    unknown_counter += 1
                    aggregate = TestAggregate(
                        student_name=f"{unknown_prefix} {unknown_counter:02d}",
                        start_page=page.number,
                        end_page=page.number,
                        parts=[page.text],
                    )
                    aggregates.append(aggregate)
            continue

        if page.detected_name:
            if current is not None:
                aggregates.append(current)
            current = TestAggregate(
                student_name=page.detected_name,
                start_page=page.number,
                end_page=page.number,
                parts=[page.text],
            )
            name_key = normalize_name(page.detected_name)
            if name_key:
                aggregates_by_name[name_key] = current
                attach_pending(name_key, current)
            continue

        if current is None:
            unknown_counter += 1
            current = TestAggregate(
                student_name=f"{unknown_prefix} {unknown_counter:02d}",
                start_page=page.number,
                end_page=page.number,
                parts=[page.text],
            )
        else:
            current.append_page(page.text, page.number)

    if current is not None:
        aggregates.append(current)

    for pending_key, pending_pages in pending_by_name.items():
        pending_pages.sort(key=lambda item: item.number)
        continuation_label = pending_pages[0].continuation_name
        if not continuation_label:
            unknown_counter += 1
            continuation_label = f"{unknown_prefix} {unknown_counter:02d}"
        aggregate = TestAggregate(
            student_name=continuation_label,
            start_page=pending_pages[0].number,
            end_page=pending_pages[0].number,
            parts=[],
        )
        for pending_page in pending_pages:
            aggregate.append_page(pending_page.text, pending_page.number)
        aggregates.append(aggregate)
    return aggregates


def get_openai_client(
    api_key: Optional[str] = None, base_url: Optional[str] = None
) -> OpenAI:
    """
    Creates an OpenAI-compatible client.
    Priority: Provided args -> Environment variables -> Default Base URLs.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")

    if not api_key:
        # Fallback for OCR specifically if OPENAI_API_KEY not set
        api_key = os.environ.get("QWEN_API_KEY")

    if not api_key:
        raise ValueError("API Key is required. Please check your .env file.")

    # Auto-detect Base URL if not provided
    if not base_url:
        if api_key.startswith("sk-or-"):
            base_url = "https://openrouter.ai/api/v1"
        elif "dashscope" in (os.environ.get("QWEN_BASE_URL") or ""):
            base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    return OpenAI(api_key=api_key, base_url=base_url)


@retry_with_backoff(retries=3, exceptions=AI_RETRIABLE_EXCEPTIONS)
def _call_chat_completion(
    client: OpenAI, model: str, messages: List[Any], **kwargs: Any
) -> Any:
    """Helper to call OpenAI chat completions with retry logic."""
    return client.chat.completions.create(
        model=model,
        messages=messages,
        **kwargs,  # type: ignore[arg-type]
    )


@retry_with_backoff(retries=3, exceptions=AI_RETRIABLE_EXCEPTIONS)
def ocr_image_with_qwen(
    client: OpenAI, image_bytes: bytes, model: Optional[str] = None
) -> str:
    # Resolve model: Argument -> Env Var -> Default
    model = model or os.environ.get("QWEN_API_MODEL") or "qwen-vl-max"
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all text from this document image. Return only the text found in the image. Do not add any introductory or concluding remarks.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        raise RuntimeError(f"Qwen OCR failed: {str(e)}")


def _process_pdf_core(
    pdf_path: str,
    dpi: int = 220,
    model: Optional[str] = None,
    unknown_label: str = "Unknown Student",
    scrub: bool = True,
) -> dict:
    """Core logic to process a PDF and return raw results."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")

    page_results = []
    used_ocr = False

    # Try native text extraction first
    extracted_texts = OCRTool.extract_text_from_pdf(pdf_path)

    if extracted_texts:
        for i, text in enumerate(extracted_texts, 1):
            name = detect_name(text)
            continuation = detect_continuation_name(text)

            # Scrub PII from text if requested
            final_text = text
            if scrub:
                final_text = SCRUBBER.scrub_text(text)

            page_results.append(
                PageResult(
                    number=i,
                    text=final_text,
                    detected_name=name,
                    continuation_name=continuation,
                )
            )
    else:
        # Fallback to OCR
        used_ocr = True
        # Use OCR-specific configuration
        client = get_openai_client(
            api_key=os.environ.get("QWEN_API_KEY"), base_url=os.environ.get("QWEN_BASE_URL")
        )

        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi)

        for i, image in enumerate(images, 1):
            # Convert to bytes
            buffered = io.BytesIO()
            image.convert("RGB").save(buffered, format="JPEG", quality=85)
            image_bytes = buffered.getvalue()

            # OCR with Qwen
            text = ocr_image_with_qwen(client, image_bytes, model=model)

            # Detect names
            name = detect_name(text)
            continuation = detect_continuation_name(text)

            # Scrub PII from text if requested
            final_text = text
            if scrub:
                final_text = SCRUBBER.scrub_text(text)

            page_results.append(
                PageResult(
                    number=i,
                    text=final_text,
                    detected_name=name,
                    continuation_name=continuation,
                )
            )

    # Aggregate results
    aggregates = aggregate_tests(page_results, unknown_prefix=unknown_label)

    results_json = [agg.to_json_record(pdf_path) for agg in aggregates]

    processing_method = "OCR (scanned/image PDF)" if used_ocr else "Fast text extraction (typed/digital PDF)"

    return {
        "status": "success",
        "file": pdf_path,
        "processing_method": processing_method,
        "used_ocr": used_ocr,
        "total_pages": len(page_results),
        "students_found": len(aggregates),
        "results": results_json,
    }


@mcp.tool
def process_pdf_document(
    pdf_path: str,
    dpi: int = 220,
    model: Optional[str] = None,
    unknown_label: str = "Unknown Student",
) -> dict:
    """
    Process a single PDF document using the fastest available method.
    WARNING: Use this only for individual files. For batches, use batch_process_documents.

    IMPORTANT: This tool automatically detects the PDF type:
    - Typed/digital PDFs: Uses FAST text extraction (no OCR, free, instant)
    - Scanned/image PDFs: Falls back to OCR (slower, uses AI model)

    The return message will clearly indicate which method was used.

    Args:
        pdf_path: Path to the PDF file to process
        dpi: DPI for OCR image conversion (default: 220, only used if OCR is needed)
        model: Qwen model to use for OCR fallback (default: env QWEN_API_MODEL or qwen-vl-max)
        unknown_label: Label for students without detected names

    Returns:
        Dictionary containing extracted text, student data, and processing method used.
    """
    try:
        return _process_pdf_core(pdf_path, dpi, model, unknown_label)
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool
def extract_text_from_image(image_path: str, model: Optional[str] = None) -> dict:
    """
    Extract text from a single image file using Qwen AI OCR.

    Args:
        image_path: Path to the image file
        model: Qwen model to use (default: env QWEN_API_MODEL or qwen-vl-max)

    Returns:
        Dictionary with extracted text
    """
    if not os.path.exists(image_path):
        return {"status": "error", "message": f"File not found: {image_path}"}

    try:
        # Use OCR-specific configuration
        client = get_openai_client(
            api_key=os.environ.get("QWEN_API_KEY"),
            base_url=os.environ.get("QWEN_BASE_URL"),
        )

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        text = ocr_image_with_qwen(client, image_bytes, model=model)

        return {"status": "success", "extracted_text": text, "source": image_path}
    except Exception as e:
        return {"status": "error", "error": str(e)}


import uuid
from datetime import datetime


def _batch_process_documents_core(
    directory_path: str,
    model: Optional[str] = None,
    dpi: int = 220,
    job_name: Optional[str] = None,
) -> dict:
    """Core logic for batch processing documents."""
    input_path = Path(directory_path)
    if not input_path.exists():
        return {"status": "error", "message": f"Directory not found: {directory_path}"}

    # Generate a unique Job ID via JobManager (creates DB record and directory)
    job_id = JOB_MANAGER.create_job(job_name=job_name)
    job_dir = JOB_MANAGER.get_job_directory(job_id)

    # Internal output file (always created by OCRTool)
    internal_jsonl = job_dir / "ocr_results.jsonl"

    files_processed = 0
    files_using_ocr = 0
    files_using_text_extraction = 0
    errors = []

    # Find all PDF files (case-insensitive extension)
    files = sorted(list(input_path.glob("*.[pP][dD][fF]")))

    if not files:
        return {
            "status": "warning",
            "message": f"No PDF files found in {directory_path}. Checked for extensions: .pdf, .PDF, .Pdf, etc.",
        }

    print(
        f"[OCR-MCP] Starting Job {job_id}: Found {len(files)} files in {directory_path}",
        file=sys.stderr,
    )

    # Initialize OCR Tool
    ocr_tool = OCRTool(job_dir=job_dir, job_id=job_id, db_manager=DB_MANAGER, student_roster=STUDENT_ROSTER)

    for file_path in files:
        try:
            print(f"[OCR-MCP] Processing {file_path.name}...", file=sys.stderr)

            # Use OCR Tool to process file (Handles DB + JSONL)
            result = ocr_tool.process_pdf(file_path, dpi=dpi)

            # Track processing method
            if result.get("used_ocr"):
                files_using_ocr += 1
            else:
                files_using_text_extraction += 1

            files_processed += 1

        except Exception as e:
            error_msg = f"{file_path.name}: {str(e)}"
            print(f"[OCR-MCP] Error processing {file_path.name}: {e}", file=sys.stderr)
            errors.append(error_msg)

    # Get student count from DB
    essays = DB_MANAGER.get_job_essays(job_id)
    students_found = len(essays)

    print(
        f"[OCR-MCP] Job {job_id} Completed. {files_processed}/{len(files)} files processed.",
        file=sys.stderr,
    )

    # Build processing method summary
    method_summary = []
    if files_using_text_extraction > 0:
        method_summary.append(f"{files_using_text_extraction} via fast text extraction")
    if files_using_ocr > 0:
        method_summary.append(f"{files_using_ocr} via OCR")
    method_str = " and ".join(method_summary) if method_summary else "unknown method"

    return {
        "status": "success",
        "job_id": job_id,
        "job_name": job_name,
        "summary": f"Processed {files_processed} files ({method_str}). Found {students_found} student records. Run `get_job_statistics` to inspect manifest, or `scrub_processed_job` to proceed.",
        "processing_details": {
            "total_files": files_processed,
            "text_extraction": files_using_text_extraction,
            "ocr": files_using_ocr,
        },
        "output_file": str(internal_jsonl.absolute()),
        "errors": errors if errors else None,
    }


@mcp.tool
def batch_process_documents(
    directory_path: str,
    model: Optional[str] = None,
    dpi: int = 220,
    job_name: Optional[str] = None,
) -> dict:
    """
    Process all PDF documents in a directory using the fastest available method.

    IMPORTANT: This tool automatically detects the PDF type:
    - Typed/digital PDFs: Uses FAST text extraction (no OCR, free, instant)
    - Scanned/image PDFs: Falls back to OCR (slower, uses AI model)

    The return message will clearly indicate which method was used for each file.

    Args:
        directory_path: Directory containing PDF files to process
        model: Qwen model to use for OCR fallback (default: env QWEN_API_MODEL or qwen-vl-max)
        dpi: DPI for OCR image conversion (default: 220, only used if OCR is needed)
        job_name: Optional name/title for the job (e.g., "Fall 2025 Midterm")

    Returns:
        Summary containing Job ID, counts, processing method breakdown, and output file location.
    """
    return _batch_process_documents_core(directory_path, model, dpi, job_name)


def _get_job_statistics_core(job_id: str) -> dict:
    """Core logic for generating job statistics."""
    essays = DB_MANAGER.get_job_essays(job_id)
    if not essays:
        return {"status": "warning", "message": f"No essays found for job {job_id}"}

    manifest = []
    for essay in essays:
        raw_text = essay.get("raw_text", "")
        word_count = len(raw_text.split()) if raw_text else 0
        metadata = essay.get("metadata", {})
        page_count = metadata.get("page_count", "N/A")

        manifest.append(
            {
                "essay_id": essay["id"],
                "student_name": essay["student_name"],
                "page_count": page_count,
                "word_count": word_count,
            }
        )

    return {
        "status": "success",
        "job_id": job_id,
        "total_students": len(essays),
        "manifest": manifest,
    }


@mcp.tool
def get_job_statistics(job_id: str) -> dict:
    """
    Returns a manifest of the job's essays for inspection.
    Useful for verifying that page aggregation worked correctly before scrubbing.

    Args:
        job_id: The ID of the job to inspect.

    Returns:
        Dictionary containing a list of students, page counts, and word counts.
    """
    return _get_job_statistics_core(job_id)


def _scrub_processed_job_core(job_id: str) -> dict:
    """Core logic for scrubbing a job."""
    print(f"[Scrubber-MCP] Scrubbing Job {job_id}...", file=sys.stderr)

    try:
        job_dir = JOB_MANAGER.get_job_directory(job_id)

        # Initialize ScrubberTool with DB Manager
        scrubber_tool = ScrubberTool(
            job_dir=job_dir, names_dir=NAMES_DIR, db_manager=DB_MANAGER
        )

        # Run scrubbing (Handles DB update + JSONL creation)
        output_path = scrubber_tool.scrub_job()

        # Get stats from DB
        essays = DB_MANAGER.get_job_essays(job_id)
        scrubbed_count = len([e for e in essays if e["status"] == "SCRUBBED"])

        print(
            f"[Scrubber-MCP] Job {job_id} Scrubbed. {scrubbed_count} essays processed.",
            file=sys.stderr,
        )

        return {
            "status": "success",
            "job_id": job_id,
            "scrubbed_count": scrubbed_count,
            "total_essays": len(essays),
            "output_file": str(output_path),
        }

    except Exception as e:
        print(f"[Scrubber-MCP] Error scrubbing job {job_id}: {e}", file=sys.stderr)
        return {"status": "error", "message": str(e)}


@mcp.tool
def scrub_processed_job(job_id: str) -> dict:
    """
    Scrubs PII from all essays in a processed job.
    Reads raw text from DB, scrubs it using the configured Scrubber, and updates the database.

    Args:
        job_id: The ID of the job to scrub.

    Returns:
        Summary of scrubbing operation.
    """
    return _scrub_processed_job_core(job_id)


def _normalize_processed_job_core(job_id: str, model: Optional[str] = None) -> dict:
    """Core logic for normalizing text in a job using xAI."""
    print(f"[Cleanup-MCP] Normalizing Job {job_id}...", file=sys.stderr)

    # Resolve model: Argument -> Env Var -> Default
    model = (
        model
        or os.environ.get("CLEANING_API_MODEL")
        or os.environ.get("XAI_API_MODEL")
        or "grok-beta"
    )

    # Get client
    try:
        client = get_openai_client(
            api_key=os.environ.get("CLEANING_API_KEY") or os.environ.get("XAI_API_KEY"),
            base_url=os.environ.get("CLEANING_BASE_URL")
            or os.environ.get("XAI_BASE_URL"),
        )
    except Exception as e:
        return {"status": "error", "message": f"Failed to get AI client: {e}"}

    # 1. Get essays from DB
    essays = DB_MANAGER.get_job_essays(job_id)

    if not essays:
        return {"status": "warning", "message": f"No essays found for job {job_id}"}

    normalized_count = 0
    errors = []

    for essay in essays:
        try:
            essay_id = essay["id"]
            # Prioritize scrubbed text for normalization
            text_to_normalize = essay["scrubbed_text"] or essay["raw_text"]

            if not text_to_normalize:
                continue

            # 2. Call AI for Normalization
            messages = [
                {
                    "role": "system",
                    "content": "You are a text normalization assistant. Your task is to fix OCR errors, typos, and minor grammatical issues while preserving the original meaning and tone of the student's essay. Do not add comments or change the structure significantly. Return ONLY the normalized text.",
                },
                {
                    "role": "user",
                    "content": f"Normalize the following text:\n\n{text_to_normalize}",
                },
            ]
            response = _call_chat_completion(client, model, messages)
            normalized_text = response.choices[0].message.content.strip()

            # 3. Update DB
            DB_MANAGER.update_essay_normalized(essay_id, normalized_text)
            normalized_count += 1

        except Exception as e:
            error_msg = f"Essay {essay['id']}: {str(e)}"
            print(
                f"[Cleanup-MCP] Error normalizing essay {essay['id']}: {e}",
                file=sys.stderr,
            )
            errors.append(error_msg)

    print(
        f"[Cleanup-MCP] Job {job_id} Normalized. {normalized_count}/{len(essays)} essays processed.",
        file=sys.stderr,
    )

    return {
        "status": "success",
        "job_id": job_id,
        "normalized_count": normalized_count,
        "total_essays": len(essays),
        "errors": errors if errors else None,
    }


def _evaluate_job_core(
    job_id: str,
    rubric: str,
    context_material: str,
    model: Optional[str] = None,
    system_instructions: Optional[str] = None,
) -> dict:
    """Core logic for evaluating essays in a job."""
    print(f"[Evaluation-MCP] Evaluating Job {job_id}...", file=sys.stderr)

    # Resolve model
    model = (
        model
        or os.environ.get("EVALUATION_API_MODEL")
        or os.environ.get("XAI_API_MODEL")
        or "grok-beta"
    )

    # Get client
    try:
        client = get_openai_client(
            api_key=os.environ.get("EVALUATION_API_KEY")
            or os.environ.get("XAI_API_KEY"),
            base_url=os.environ.get("EVALUATION_BASE_URL")
            or os.environ.get("XAI_BASE_URL"),
        )
    except Exception as e:
        return {"status": "error", "message": f"Failed to get AI client: {e}"}

    # 1. Get essays from DB
    essays = DB_MANAGER.get_job_essays(job_id)

    if not essays:
        return {"status": "warning", "message": f"No essays found for job {job_id}"}

    evaluated_count = 0
    errors = []

    for essay in essays:
        try:
            essay_id = essay["id"]
            # Selection priority: Normalized -> Scrubbed -> Raw
            text_to_evaluate = (
                essay.get("normalized_text")
                or essay.get("scrubbed_text")
                or essay.get("raw_text")
            )

            if not text_to_evaluate:
                continue

            # 2. Construct Prompt
            prompt = get_evaluation_prompt(
                text_to_evaluate, rubric, context_material, system_instructions
            )

            # 3. Call AI for Evaluation
            messages = [
                {
                    "role": "system",
                    "content": "You are a professional academic evaluator. Extract evaluation criteria and provide structured feedback according to the schema.",
                },
                {"role": "user", "content": prompt},
            ]

            # Define JSON schema for structured outputs (Grok 4+ supports this!)
            evaluation_schema = {
                "type": "object",
                "properties": {
                    "criteria": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Criterion name from the rubric"},
                                "score": {"type": ["string", "number"], "description": "Score for this criterion"},
                                "feedback": {
                                    "type": "object",
                                    "properties": {
                                        "examples": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Direct quotes from the essay"
                                        },
                                        "advice": {"type": "string", "description": "Actionable improvement advice"},
                                        "rewritten_example": {"type": "string", "description": "Improved version of a quoted example"}
                                    },
                                    "required": ["examples", "advice", "rewritten_example"],
                                    "additionalProperties": False
                                }
                            },
                            "required": ["name", "score", "feedback"],
                            "additionalProperties": False
                        }
                    },
                    "overall_score": {"type": "string", "description": "Total score (e.g., '95', 'A', '18/20')"},
                    "summary": {"type": "string", "description": "Brief overall assessment"}
                },
                "required": ["criteria", "overall_score", "summary"],
                "additionalProperties": False
            }

            # Use structured outputs for all models (Grok 4+ and OpenAI both support json_schema)
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "essay_evaluation",
                    "strict": True,  # Strongly enforce schema compliance
                    "schema": evaluation_schema
                }
            }

            response = _call_chat_completion(
                client,
                model,
                messages,
                response_format=response_format,
                max_tokens=4000,      # Ensure complete responses for long evaluations
                temperature=0.1       # Low temperature for deterministic, schema-following behavior
            )
            raw_eval_text = response.choices[0].message.content.strip()

            # 4. Extract and Validate JSON
            # With structured outputs, the response should be valid JSON already
            # but we still use extract_json_from_text as a safety net
            eval_data = extract_json_from_text(raw_eval_text)
            if not eval_data:
                # Log the full response for debugging
                print(
                    f"[Evaluation-MCP] ERROR: Failed to parse JSON for essay {essay_id}. Full response:",
                    file=sys.stderr
                )
                print(f"[Evaluation-MCP] {raw_eval_text}", file=sys.stderr)

                # Save failed response to file for inspection
                job_dir = JOB_MANAGER.get_job_directory(job_id)
                error_file = job_dir / f"failed_eval_essay_{essay_id}.json"
                with open(error_file, "w") as f:
                    f.write(raw_eval_text)
                print(f"[Evaluation-MCP] Saved failed response to {error_file}", file=sys.stderr)

                raise ValueError(
                    f"Failed to extract valid JSON from AI response. Full response saved to {error_file}. Preview: {raw_eval_text[:200]}..."
                )

            # Ensure we save the cleaned JSON back to string for DB
            eval_json_str = json.dumps(eval_data)

            # 5. Extract Grade
            grade = str(eval_data.get("overall_score") or eval_data.get("score") or "")

            # 6. Update DB
            DB_MANAGER.update_essay_evaluation(essay_id, eval_json_str, grade)
            evaluated_count += 1

        except Exception as e:
            error_msg = f"Essay {essay['id']}: {str(e)}"
            print(
                f"[Evaluation-MCP] Error evaluating essay {essay['id']}: {e}",
                file=sys.stderr,
            )
            errors.append(error_msg)

    print(
        f"[Evaluation-MCP] Job {job_id} Evaluated. {evaluated_count}/{len(essays)} essays processed.",
        file=sys.stderr,
    )

    return {
        "status": "success",
        "job_id": job_id,
        "evaluated_count": evaluated_count,
        "total_essays": len(essays),
        "errors": errors if errors else None,
    }


@mcp.tool
def evaluate_job(
    job_id: str,
    rubric: str,
    context_material: str,
    model: Optional[str] = None,
    system_instructions: Optional[str] = None,
) -> dict:
    """
    Evaluates all essays in a processed job using AI based on a rubric and context material.
    Updates the database with scores and detailed comments.

    Args:
        job_id: The ID of the job to evaluate.
        rubric: The grading criteria text.
        context_material: The source material or answer key context.
        model: The AI model to use (default: env EVALUATION_API_MODEL or grok-beta).
        system_instructions: Optional custom instructions for the AI evaluator.

    Returns:
        Summary of evaluation operation.
    """
    return _evaluate_job_core(
        job_id, rubric, context_material, model, system_instructions
    )


@mcp.tool
def add_to_knowledge_base(file_paths: List[str], topic: str) -> dict:
    """
    Adds local files (PDF, TXT, etc.) to the knowledge base for a specific topic.
    The content will be indexed and available for later retrieval.

    Args:
        file_paths: List of absolute or relative paths to files.
        topic: A name for the collection (e.g., 'frost_poetry', 'thermodynamics').

    Returns:
        Summary of ingestion.
    """
    try:
        count = KB_MANAGER.ingest_documents(file_paths, topic)
        return {
            "status": "success",
            "topic": topic,
            "documents_added": count,
            "message": f"Successfully indexed {count} documents into topic '{topic}'.",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def query_knowledge_base(
    query: str, topic: str, include_raw_context: bool = False
) -> dict:
    """
    Queries the knowledge base for information about a specific topic.
    Returns a synthesized answer and optionally raw context chunks.

    Args:
        query: The question or search term.
        topic: The topic collection to search in.
        include_raw_context: If true, returns the raw text chunks used for the answer.

    Returns:
        Synthesized answer and optional context.
    """
    try:
        answer = KB_MANAGER.query_knowledge(query, topic)
        result: dict[str, Any] = {"status": "success", "topic": topic, "answer": answer}

        if include_raw_context:
            chunks = KB_MANAGER.retrieve_context_chunks(query, topic)
            result["context_chunks"] = chunks

        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def generate_gradebook(job_id: str) -> dict:
    """
    Generates a CSV gradebook for a job, reuniting student names with their scores.

    Args:
        job_id: The ID of the job to report on.

    Returns:
        Summary with the path to the CSV file.
    """
    try:
        essays = DB_MANAGER.get_job_essays(job_id)
        if not essays:
            return {"status": "error", "message": f"No essays found for job {job_id}"}

        csv_path = REPORT_GENERATOR.generate_csv_gradebook(job_id, essays)
        return {
            "status": "success",
            "job_id": job_id,
            "csv_path": str(Path(csv_path).absolute()),  # Return absolute path
            "message": f"Gradebook generated at {csv_path}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def generate_student_feedback(job_id: str) -> dict:
    """
    Generates individual PDF feedback reports for each student in a job.

    Args:
        job_id: The ID of the job to report on.

    Returns:
        Summary with the path to the directory containing PDFs.
    """
    try:
        essays = DB_MANAGER.get_job_essays(job_id)
        if not essays:
            return {"status": "error", "message": f"No essays found for job {job_id}"}

        pdf_dir = REPORT_GENERATOR.generate_student_feedback_pdfs(job_id, essays)

        # Zip the directory for easy download
        zip_path = REPORT_GENERATOR.zip_directory(pdf_dir, f"{job_id}_student_feedback")

        return {
            "status": "success",
            "job_id": job_id,
            "pdf_directory": str(Path(pdf_dir).absolute()),  # Return absolute path
            "zip_path": str(Path(zip_path).absolute()),      # Return absolute path
            "message": f"Individual feedback PDFs generated and zipped at {zip_path}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
async def send_student_feedback_emails(
    job_id: str,
    subject: Optional[str] = None,
    template_name: Optional[str] = "default_feedback",
    dry_run: bool = False,
    filter_students: Optional[Any] = None
) -> dict:
    """
    Sends individual PDF feedback reports to students via email.

    IMPORTANT: This sends real emails. Use dry_run=True to preview first.

    The tool will:
    1. Load student email addresses from school_names.csv
    2. Find corresponding PDF feedback reports
    3. Send personalized emails with PDF attachments
    4. Log all sends/failures to email_log.jsonl

    Idempotent: Re-running skips students who already received emails.

    Args:
        job_id: The ID of the graded job to send feedback for.
        subject: Custom email subject (default: "Your Assignment Feedback - {assignment_name}").
        template_name: Optional. Name of the email template. Defaults to 'default_feedback' if omitted or null. Do not provide if using default.
        dry_run: If True, validates emails but doesn't send (default: False).
        filter_students: Optional list of strings. Provide a standard JSON list of names (e.g. ["Name 1", "Name 2"]). Do NOT stringify the list unless absolutely necessary.

    Returns:
        Summary with count of sent/failed/skipped emails and path to log file.

    Example:
        # Preview what would be sent
        send_student_feedback_emails(job_id="job_123", dry_run=True)

        # Send to all students
        send_student_feedback_emails(job_id="job_123")

        # Send to specific students only
        send_student_feedback_emails(job_id="job_123", filter_students=["John Doe", "Jane Smith"])
    """
    import json

    # Handle agent quirks: explicit nulls or stringified lists
    final_template = template_name if template_name else "default_feedback"
    final_filter = None

    if filter_students:
        if isinstance(filter_students, str):
            try:
                # Try to parse string as JSON list
                parsed = json.loads(filter_students)
                if isinstance(parsed, list):
                    final_filter = [str(x) for x in parsed]
                else:
                    # If it's just a single string name, wrap it
                    final_filter = [filter_students]
            except json.JSONDecodeError:
                # Fallback: treat as single student name
                final_filter = [filter_students]
        elif isinstance(filter_students, list):
            final_filter = [str(x) for x in filter_students]

    try:
        # Direct await since tool is now async
        result = await EMAILER_TOOL.send_feedback_emails(
            job_id=job_id,
            subject_template=subject,
            body_template=final_template,
            dry_run=dry_run,
            filter_students=final_filter
        )
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool
def identify_email_problems(job_id: str) -> dict:
    """
    Identifies students who cannot be emailed and why.

    This is the FIRST STEP in preparing to email feedback reports. It checks
    each student to see if they have a valid email in the roster and if their
    PDF report was generated.

    Use this before sending emails to identify students who need name corrections
    or are missing email addresses.

    Args:
        job_id: The ID of the graded job to check.

    Returns:
        Dictionary with:
        - status: "needs_corrections" if problems found, "ready" if all students OK
        - students_needing_help: List of students with problems (name not found, no email, etc.)
        - ready_to_send: Count of students ready to email
        - total_students: Total number of students in job

    Example:
        result = identify_email_problems(job_id="job_123")
        # Shows which students need teacher intervention before emailing
    """
    return NAME_FIXER_TOOL.identify_email_problems(job_id)


@mcp.tool
def verify_student_name_correction(
    job_id: str,
    essay_id: int,
    suggested_name: str
) -> dict:
    """
    Verifies that a suggested name correction exists in the roster.

    This is the SECOND STEP after teacher provides a corrected student name.
    Checks if the suggested name is valid and has an email address.

    Use this after teacher suggests a corrected name for a student who couldn't
    be matched. Shows the matched student info for teacher confirmation.

    Args:
        job_id: The ID of the graded job.
        essay_id: The essay database ID to correct.
        suggested_name: The corrected student name (e.g., "John Doe").

    Returns:
        Dictionary with:
        - status: "match_found", "no_match", "no_email", or "no_exact_match"
        - Match details if found (name, email, grade)
        - Possible matches if no exact match
        - needs_confirmation: True if match found and needs teacher confirmation

    Example:
        # Teacher says "Unknown Student 01" should be "John Doe"
        result = verify_student_name_correction(
            job_id="job_123",
            essay_id=5,
            suggested_name="John Doe"
        )
        # Returns: Found John Doe <john@example.com>, needs confirmation
    """
    return NAME_FIXER_TOOL.verify_student_name_correction(job_id, essay_id, suggested_name)


@mcp.tool
def apply_student_name_correction(
    job_id: str,
    essay_id: int,
    confirmed_name: str
) -> dict:
    """
    Applies a confirmed name correction to the database.

    This is the THIRD STEP after teacher confirms the name match is correct.
    Updates the student_name field in the database WITHOUT re-grading the essay.

    Use this after verify_student_name_correction returns a match and teacher
    confirms it's correct. The grade and evaluation are preserved.

    Args:
        job_id: The ID of the graded job.
        essay_id: The essay database ID to update.
        confirmed_name: The confirmed correct student name.

    Returns:
        Dictionary with:
        - status: "success" or "error"
        - old_name: Previous name in database
        - new_name: Updated name
        - email: Student's email address

    Example:
        # Teacher confirms "John Doe" is correct
        result = apply_student_name_correction(
            job_id="job_123",
            essay_id=5,
            confirmed_name="John Doe"
        )
        # Updates database: "Unknown Student 01" → "John Doe"
    """
    return NAME_FIXER_TOOL.apply_student_name_correction(job_id, essay_id, confirmed_name)


@mcp.tool
def skip_student_email(
    job_id: str,
    essay_id: int,
    reason: str = "Manual delivery"
) -> dict:
    """
    Marks a student to skip for email delivery (manual delivery instead).

    Use this when teacher cannot identify the student or wants to deliver the
    feedback manually. The student will be excluded from email sending.

    The PDF report is still available in the feedback_pdfs directory for manual
    delivery.

    Args:
        job_id: The ID of the graded job.
        essay_id: The essay database ID to skip.
        reason: Reason for skipping (default: "Manual delivery").

    Returns:
        Dictionary with:
        - status: "success"
        - essay_id: The skipped essay ID
        - student_name: Current name in database
        - reason: Why it's being skipped

    Example:
        # Teacher can't identify student, will deliver manually
        result = skip_student_email(
            job_id="job_123",
            essay_id=5,
            reason="Unable to identify student"
        )
    """
    return NAME_FIXER_TOOL.skip_student_email(job_id, essay_id, reason)


@mcp.tool
def cleanup_old_jobs(retention_days: int = 210, dry_run: bool = False) -> dict:
    """
    Deletes jobs older than the specified retention period (default: 210 days / 7 months).
    Removes both the database records and the physical files.

    Args:
        retention_days: Number of days to keep jobs.
        dry_run: If True, lists what would be deleted without taking action.

    Returns:
        Summary of deleted jobs.
    """
    return CLEANUP_TOOL.cleanup_old_jobs(retention_days, dry_run)


@mcp.tool
def delete_knowledge_topic(topic: str) -> dict:
    """
    Manually deletes a Knowledge Base topic (collection).
    Use this to remove obsolete reference materials.

    Args:
        topic: The name of the topic to delete.

    Returns:
        Status of the operation.
    """
    return CLEANUP_TOOL.delete_knowledge_topic(topic)


@mcp.tool
def search_past_jobs(
    query: str, start_date: Optional[str] = None, end_date: Optional[str] = None
) -> dict:
    """
    Searches for past jobs by keyword (student name, job name, or essay content).
    Useful for retrieving jobs when the exact ID is lost.

    Args:
        query: The search keyword.
        start_date: Optional start date (YYYY-MM-DD).
        end_date: Optional end date (YYYY-MM-DD).

    Returns:
        List of matching jobs with metadata and context snippets.
    """
    return ARCHIVE_TOOL.search_past_jobs(query, start_date, end_date)


@mcp.tool
def export_job_archive(job_id: str) -> dict:
    """
    Exports a comprehensive ZIP archive of a job for legal/dispute purposes.
    Includes raw data, gradebook, individual PDFs, and a chain-of-custody manifest.

    Args:
        job_id: The ID of the job to export.

    Returns:
        Path to the generated ZIP file.
    """
    return ARCHIVE_TOOL.export_job_archive(job_id)


@mcp.tool
def convert_pdf_to_text(
    file_path: str, output_path: Optional[str] = None, use_ocr: bool = False
) -> dict:
    """
    Converts a PDF to plain text format.
    Use this for rubrics or reference materials that teachers provide as PDFs.

    Args:
        file_path: Path to the PDF file
        output_path: Optional path for output text file (defaults to same name with .txt extension)
        use_ocr: If True, uses OCR for scanned PDFs (slower but works with images)

    Returns:
        Dictionary with status and path to the text file.
    """
    try:
        txt_path = CONVERTER.convert_pdf_to_text(file_path, output_path, use_ocr)
        return {
            "status": "success",
            "input_file": file_path,
            "output_file": str(txt_path),
            "message": f"Successfully converted to text: {txt_path}",
            "used_ocr": use_ocr,
        }
    except Exception as e:
        return {
            "status": "error",
            "input_file": file_path,
            "error": str(e),
            "suggestion": "If the PDF is scanned/image-based, try setting use_ocr=True",
        }


@mcp.tool
def check_conversion_capabilities() -> dict:
    """
    Checks which document conversion tools are available on the system.
    Returns installation instructions if tools are missing.

    Returns:
        Dictionary with capability status and installation instructions.
    """
    return CONVERTER.get_conversion_info()


@mcp.tool
def convert_image_to_pdf(file_path: str, output_path: Optional[str] = None) -> dict:
    """
    Converts a single image file (JPEG, PNG, etc.) to PDF format.

    Args:
        file_path: Path to the image file (.jpg, .jpeg, .png, etc.)
        output_path: Optional path for output PDF (defaults to same name with .pdf extension)

    Returns:
        Dictionary with status and path to the converted PDF file.
    """
    try:
        pdf_path = CONVERTER.convert_image_to_pdf(file_path, output_path)
        return {
            "status": "success",
            "input_file": file_path,
            "output_file": str(pdf_path),
            "message": f"Successfully converted image to PDF: {pdf_path}",
        }
    except Exception as e:
        return {"status": "error", "input_file": file_path, "error": str(e)}


@mcp.tool
def batch_convert_images_to_pdf(input_dir: str, output_dir: str) -> dict:
    """
    Converts all image files in a directory to individual PDF files.
    Each image becomes a separate single-page PDF.

    Args:
        input_dir: Directory containing image files (.jpg, .jpeg, .png)
        output_dir: Directory to save the converted PDF files

    Returns:
        Dictionary with conversion summary and list of converted files.
    """
    try:
        pdf_paths = CONVERTER.batch_convert_images_to_pdf(input_dir, output_dir)
        return {
            "status": "success",
            "input_directory": input_dir,
            "output_directory": output_dir,
            "files_converted": len(pdf_paths),
            "converted_files": [str(p) for p in pdf_paths],
            "message": f"Successfully converted {len(pdf_paths)} images to PDF.",
        }
    except Exception as e:
        return {"status": "error", "input_directory": input_dir, "error": str(e)}


@mcp.tool
def merge_images_to_pdf(image_paths: List[str], output_path: str) -> dict:
    """
    Merges multiple image files into a single multi-page PDF.
    Useful when a teacher has scanned essay pages as individual image files.

    Args:
        image_paths: List of paths to image files (will be merged in this order)
        output_path: Path for the output multi-page PDF file

    Returns:
        Dictionary with status and path to the merged PDF file.
    """
    try:
        pdf_path = CONVERTER.merge_images_to_pdf(image_paths, output_path)
        return {
            "status": "success",
            "input_files": image_paths,
            "output_file": str(pdf_path),
            "pages": len(image_paths),
            "message": f"Successfully merged {len(image_paths)} images into PDF: {pdf_path}",
        }
    except Exception as e:
        return {"status": "error", "input_files": image_paths, "error": str(e)}


if __name__ == "__main__":
    mcp.run()
