#!/usr/bin/env python
"""
FastMCP server implementation for OCR document processing using Qwen AI.
Replaces the original batchocr CLI (Google Vision) with Qwen-VL via OpenAI compatible API.
"""

from __future__ import annotations

import base64
import io
import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, List

import regex
from fastmcp import FastMCP
from pdf2image import convert_from_path
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

from edmcp.core.name_loader import NameLoader
from edmcp.tools.scrubber import Scrubber
from edmcp.core.db import DatabaseManager
from edmcp.core.job_manager import JobManager
from edmcp.core.prompts import get_evaluation_prompt

# Load environment variables from .env file
load_dotenv(find_dotenv())

# Constants from original batchocr
NAME_HEADER_PATTERN = regex.compile(
    r"(?im)^\s*(?:name|id)\s*[:\-]\s*([\p{L}][\p{L}'-]*(?:\s+[\p{L}][\p{L}'-]*)?)"
)
CONTINUE_HEADER_PATTERN = regex.compile(r"(?im)^\s*continue\s*[:\-]\s*(.+)$")

# Initialize Scrubber
NAMES_DIR = Path(__file__).parent / "edmcp/data/names"
loader = NameLoader(NAMES_DIR)
all_names = loader.load_all_names()
SCRUBBER = Scrubber(all_names)

# Initialize DB and JobManager
DB_PATH = "edmcp.db"
JOBS_DIR = Path("data/jobs")
DB_MANAGER = DatabaseManager(DB_PATH)
JOB_MANAGER = JobManager(JOBS_DIR, DB_MANAGER)

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
    top_section = "\n".join(text.splitlines()[:10])
    match = NAME_HEADER_PATTERN.search(top_section)
    if match:
        return match.group(1).strip()
    return None

def detect_continuation_name(text: str) -> Optional[str]:
    """Detect CONTINUE markers that reference the original student name."""
    top_section = "\n".join(text.splitlines()[:10])
    match = CONTINUE_HEADER_PATTERN.search(top_section)
    if match:
        return match.group(1).strip()
    return None

def aggregate_tests(pages: Iterable[PageResult], *, unknown_prefix: str = "Unknown Student") -> list[TestAggregate]:
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
            target = aggregates_by_name.get(continuation_key) if continuation_key else None
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

def get_openai_client() -> OpenAI:
    api_key = os.environ.get("QWEN_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("QWEN_BASE_URL")
    
    if not api_key:
        raise ValueError("QWEN_API_KEY or OPENAI_API_KEY environment variable is required.")

    # Auto-detect OpenRouter based on key prefix
    if not base_url:
        if api_key.startswith("sk-or-"):
            base_url = "https://openrouter.ai/api/v1"
        else:
            base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
    return OpenAI(api_key=api_key, base_url=base_url)

def ocr_image_with_qwen(client: OpenAI, image_bytes: bytes, model: Optional[str] = None) -> str:
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
                        {"type": "text", "text": "Extract all text from this document image. Return only the text found in the image. Do not add any introductory or concluding remarks."},
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

def _process_pdf_core(pdf_path: str, dpi: int = 220, model: Optional[str] = None, unknown_label: str = "Unknown Student", scrub: bool = True) -> dict:
    """Core logic to process a PDF and return raw results."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"File not found: {pdf_path}")

    client = get_openai_client()
    
    # Convert PDF to images
    images = convert_from_path(pdf_path, dpi=dpi)
    
    page_results = []
    
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
            PageResult(number=i, text=final_text, detected_name=name, continuation_name=continuation)
        )
        
    # Aggregate results
    aggregates = aggregate_tests(page_results, unknown_prefix=unknown_label)
    
    results_json = [agg.to_json_record(pdf_path) for agg in aggregates]
    
    return {
        "status": "success",
        "file": pdf_path,
        "total_pages": len(images),
        "students_found": len(aggregates),
        "results": results_json
    }

@mcp.tool
def process_pdf_document(
    pdf_path: str, 
    dpi: int = 220, 
    model: Optional[str] = None,
    unknown_label: str = "Unknown Student"
) -> dict:
    """
    Process a single PDF document and return the full results in the response.
    WARNING: Use this only for individual files. For batches, use batch_process_documents.

    Args:
        pdf_path: Path to the PDF file to process
        dpi: Resolution for PDF to image conversion (default: 220)
        model: Qwen model to use (default: env QWEN_API_MODEL or qwen-vl-max)
        unknown_label: Label for students without detected names

    Returns:
        Dictionary containing extracted text and student data.
    """
    try:
        return _process_pdf_core(pdf_path, dpi, model, unknown_label)
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool
def extract_text_from_image(
    image_path: str, 
    model: Optional[str] = None
) -> dict:
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
        client = get_openai_client()
        
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            
        text = ocr_image_with_qwen(client, image_bytes, model=model)
        
        return {
            "status": "success",
            "extracted_text": text,
            "source": image_path
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

import sys
import uuid
from datetime import datetime

@mcp.tool
def batch_process_documents(
    directory_path: str,
    output_directory: str,
    model: Optional[str] = None,
    dpi: int = 220
) -> dict:
    """
    Process all PDF documents in a directory.
    Saves raw results to SQLite database and legacy JSONL backup.
    Returns a Job ID and summary to the agent.

    Args:
        directory_path: Directory containing PDF files to process
        output_directory: Directory where the unique JSONL output will be stored (Legacy/Backup)
        model: Qwen model to use (default: env QWEN_API_MODEL or qwen-vl-max)
        dpi: DPI for scanning

    Returns:
        Summary containing Job ID, counts, and the location of the output file.
    """
    input_path = Path(directory_path)
    if not input_path.exists():
        return {"status": "error", "message": f"Directory not found: {directory_path}"}

    # Generate a unique Job ID via JobManager (creates DB record and directory)
    job_id = JOB_MANAGER.create_job()
    
    out_dir = Path(output_directory)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{job_id}.jsonl"

    files_processed = 0
    students_found = 0
    errors = []

    # Find all PDF files (case-insensitive extension)
    files = sorted(list(input_path.glob("*.[pP][dD][fF]")))
    
    if not files:
        return {
            "status": "warning", 
            "message": f"No PDF files found in {directory_path}. Checked for extensions: .pdf, .PDF, .Pdf, etc."
        }

    print(f"[OCR-MCP] Starting Job {job_id}: Found {len(files)} files in {directory_path}", file=sys.stderr)

    # Open the output file for writing (JSON Lines) - Backup
    with open(output_path, "w", encoding="utf-8") as f_out:
        for file_path in files:
            try:
                print(f"[OCR-MCP] Processing {file_path.name}...", file=sys.stderr)
                
                # Process the PDF using the core logic (SCRUB=FALSE for DB storage)
                result = _process_pdf_core(str(file_path), dpi=dpi, model=model, scrub=False)
                
                # Write each student record to DB and JSONL
                for record in result.get("results", []):
                    # Add Job ID to the record
                    record["job_id"] = job_id
                    
                    # Save to SQLite
                    DB_MANAGER.add_essay(
                        job_id=job_id,
                        student_name=record['student_name'],
                        raw_text=record['text'],
                        metadata=record['metadata']
                    )
                    
                    # Save to JSONL (Raw text for now)
                    f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                    students_found += 1
                
                files_processed += 1
                
            except Exception as e:
                error_msg = f"{file_path.name}: {str(e)}"
                print(f"[OCR-MCP] Error processing {file_path.name}: {e}", file=sys.stderr)
                errors.append(error_msg)

    print(f"[OCR-MCP] Job {job_id} Completed. {files_processed}/{len(files)} files processed.", file=sys.stderr)

    return {
        "status": "success",
        "job_id": job_id,
        "summary": f"Processed {files_processed} files. Found {students_found} student records. Saved to DB and {output_path}",
        "output_file": str(output_path.absolute()),
        "errors": errors if errors else None
    }

def _scrub_processed_job_core(job_id: str) -> dict:
    """Core logic for scrubbing a job."""
    print(f"[Scrubber-MCP] Scrubbing Job {job_id}...", file=sys.stderr)
    
    # 1. Get essays from DB
    essays = DB_MANAGER.get_job_essays(job_id)
    
    if not essays:
        return {"status": "warning", "message": f"No essays found for job {job_id}"}
    
    scrubbed_count = 0
    errors = []
    
    for essay in essays:
        try:
            essay_id = essay['id']
            raw_text = essay['raw_text']
            
            # 2. Scrub
            if raw_text:
                scrubbed_text = SCRUBBER.scrub_text(raw_text)
            else:
                scrubbed_text = ""

            # 3. Update DB
            DB_MANAGER.update_essay_scrubbed(essay_id, scrubbed_text)
            scrubbed_count += 1
            
        except Exception as e:
            error_msg = f"Essay {essay['id']}: {str(e)}"
            print(f"[Scrubber-MCP] Error scrubbing essay {essay['id']}: {e}", file=sys.stderr)
            errors.append(error_msg)
            
    print(f"[Scrubber-MCP] Job {job_id} Scrubbed. {scrubbed_count}/{len(essays)} essays processed.", file=sys.stderr)
    
    return {
        "status": "success",
        "job_id": job_id,
        "scrubbed_count": scrubbed_count,
        "total_essays": len(essays),
        "errors": errors if errors else None
    }

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
    model = model or os.environ.get("XAI_API_MODEL") or "grok-beta"
    
    # Get client
    try:
        client = get_openai_client()
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
            essay_id = essay['id']
            # Prioritize scrubbed text for normalization
            text_to_normalize = essay['scrubbed_text'] or essay['raw_text']
            
            if not text_to_normalize:
                continue

            # 2. Call AI for Normalization
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a text normalization assistant. Your task is to fix OCR errors, typos, and minor grammatical issues while preserving the original meaning and tone of the student's essay. Do not add comments or change the structure significantly. Return ONLY the normalized text."
                    },
                    {
                        "role": "user",
                        "content": f"Normalize the following text:\n\n{text_to_normalize}"
                    }
                ],
            )
            normalized_text = response.choices[0].message.content.strip()
            
            # 3. Update DB
            DB_MANAGER.update_essay_normalized(essay_id, normalized_text)
            normalized_count += 1
            
        except Exception as e:
            error_msg = f"Essay {essay['id']}: {str(e)}"
            print(f"[Cleanup-MCP] Error normalizing essay {essay['id']}: {e}", file=sys.stderr)
            errors.append(error_msg)
            
    print(f"[Cleanup-MCP] Job {job_id} Normalized. {normalized_count}/{len(essays)} essays processed.", file=sys.stderr)
    
    return {
        "status": "success",
        "job_id": job_id,
        "normalized_count": normalized_count,
        "total_essays": len(essays),
        "errors": errors if errors else None
    }

def _evaluate_job_core(job_id: str, rubric: str, context_material: str, model: Optional[str] = None, system_instructions: Optional[str] = None) -> dict:
    """Core logic for evaluating essays in a job."""
    print(f"[Evaluation-MCP] Evaluating Job {job_id}...", file=sys.stderr)
    
    # Resolve model
    model = model or os.environ.get("EVALUATION_API_MODEL") or os.environ.get("XAI_API_MODEL") or "grok-beta"
    
    # Get client
    try:
        client = get_openai_client()
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
            essay_id = essay['id']
            # Selection priority: Normalized -> Scrubbed -> Raw
            text_to_evaluate = (
                essay.get('normalized_text') or 
                essay.get('scrubbed_text') or 
                essay.get('raw_text')
            )
            
            if not text_to_evaluate:
                continue

            # 2. Construct Prompt
            prompt = get_evaluation_prompt(text_to_evaluate, rubric, context_material, system_instructions)

            # 3. Call AI for Evaluation
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a professional academic evaluator. Return your response in strictly valid JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"} if "grok" not in model.lower() else None # Grok-beta might not support JSON mode yet via OpenAI client, but we asked for it in prompt
            )
            eval_json_str = response.choices[0].message.content.strip()
            
            # 4. Extract Grade (simple parse)
            grade = None
            try:
                eval_data = json.loads(eval_json_str)
                grade = str(eval_data.get("score", ""))
            except json.JSONDecodeError:
                pass # Fallback to None grade, but keep raw JSON
            
            # 5. Update DB
            DB_MANAGER.update_essay_evaluation(essay_id, eval_json_str, grade)
            evaluated_count += 1
            
        except Exception as e:
            error_msg = f"Essay {essay['id']}: {str(e)}"
            print(f"[Evaluation-MCP] Error evaluating essay {essay['id']}: {e}", file=sys.stderr)
            errors.append(error_msg)
            
    print(f"[Evaluation-MCP] Job {job_id} Evaluated. {evaluated_count}/{len(essays)} essays processed.", file=sys.stderr)
    
    return {
        "status": "success",
        "job_id": job_id,
        "evaluated_count": evaluated_count,
        "total_essays": len(essays),
        "errors": errors if errors else None
    }

@mcp.tool
def evaluate_job(
    job_id: str, 
    rubric: str, 
    context_material: str, 
    model: Optional[str] = None, 
    system_instructions: Optional[str] = None
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
    return _evaluate_job_core(job_id, rubric, context_material, model, system_instructions)

if __name__ == "__main__":
    mcp.run()