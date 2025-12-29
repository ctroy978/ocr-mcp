import regex
from typing import Set, List, Union, Optional
from pathlib import Path
from edmcp.core.jsonl_utils import read_jsonl, write_jsonl
from edmcp.core.name_loader import NameLoader
from edmcp.core.db import DatabaseManager

class Scrubber:
    """
    Scrubs PII (names) from the first 20 lines of text.
    """
    
    def __init__(self, names: Set[str], replacement: str = "[STUDENT_NAME]"):
        self.names = names
        self.replacement = replacement
        # Compile a regex that matches any of the names as whole words, case-insensitive
        if names:
            # Sort names by length descending to match longer names first if there are overlaps 
            # (though we are doing atomic scrubbing, it's good practice)
            sorted_names = sorted(list(names), key=len, reverse=True)
            pattern = r"\b(" + "|".join(regex.escape(n) for n in sorted_names) + r")\b"
            self.regex = regex.compile(pattern, regex.IGNORECASE)
        else:
            self.regex = None

    def scrub_text(self, text: str, line_limit: int = 20) -> str:
        """
        Scrubs names from the first line_limit lines of the text.
        """
        if not self.regex or not text:
            return text
            
        lines = text.splitlines()
        scrubbed_lines = []
        
        for i, line in enumerate(lines):
            if i < line_limit:
                scrubbed_line = self.regex.sub(self.replacement, line)
                scrubbed_lines.append(scrubbed_line)
            else:
                scrubbed_lines.append(line)
                
        # Handle trailing newline if original text had one
        result = "\n".join(scrubbed_lines)
        if text.endswith("\n") and not result.endswith("\n"):
            result += "\n"
        return result

class ScrubberTool:
    """
    Modular tool to scrub PII from OCR results in a job directory.
    """
    def __init__(self, job_dir: Union[str, Path], names_dir: Optional[Union[str, Path]] = None, db_manager: Optional[DatabaseManager] = None):
        self.job_dir = Path(job_dir)
        self.job_id = self.job_dir.name
        self.db_manager = db_manager
        
        # Resolve names directory
        if names_dir is None:
            # Default to edmcp/data/names relative to this file
            self.names_dir = Path(__file__).parent.parent / "data" / "names"
        else:
            self.names_dir = Path(names_dir)
            
        # Load names and initialize scrubber
        loader = NameLoader(self.names_dir)
        names = loader.load_all_names()
        self.scrubber = Scrubber(names)

    def scrub_job(self, input_filename: str = "ocr_results.jsonl", output_filename: str = "scrubbed_results.jsonl") -> Path:
        """
        Reads OCR results (from DB or JSONL), scrubs them, and writes to a new JSONL file + DB.
        
        Args:
            input_filename: Name of the input JSONL file in the job directory (fallback source).
            output_filename: Name of the output JSONL file to create.
            
        Returns:
            Path to the scrubbed results file.
        """
        output_path = self.job_dir / output_filename
        scrubbed_records = []

        if self.db_manager:
            # 1. Read from DB
            essays = self.db_manager.get_job_essays(self.job_id)
            
            for essay in essays:
                raw_text = essay.get("raw_text", "")
                scrubbed_text = self.scrubber.scrub_text(raw_text)
                
                # Update DB
                self.db_manager.update_essay_scrubbed(essay["id"], scrubbed_text)
                
                # Add to list for JSONL output
                scrubbed_records.append({
                    "job_id": self.job_id,
                    "essay_id": essay["id"],
                    "student_name": essay.get("student_name"),
                    "text": scrubbed_text,
                    "metadata": essay.get("metadata")
                })
        else:
            # 2. Fallback to JSONL
            input_path = self.job_dir / input_filename
            if not input_path.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")
                
            records = list(read_jsonl(input_path))
            for record in records:
                if "text" in record:
                    record["text"] = self.scrubber.scrub_text(record["text"])
                scrubbed_records.append(record)
        
        # Write to JSONL
        write_jsonl(output_path, scrubbed_records)
        return output_path
