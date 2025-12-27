import uuid
from datetime import datetime
from pathlib import Path
from typing import Union

class JobManager:
    """
    Manages job IDs and directory structures for the OCR-MCP pipeline.
    """

    @staticmethod
    def generate_job_id() -> str:
        """
        Generates a unique job ID combining a timestamp and a UUID short code.
        Format: YYYYMMDD_HHMMSS_shortuuid
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_suffix = str(uuid.uuid4())[:8]
        return f"{timestamp}_{unique_suffix}"

    @staticmethod
    def create_job_directory(job_id: str, base_path: Union[str, Path]) -> Path:
        """
        Creates a dedicated directory for a job.
        
        Args:
            job_id: The unique identifier for the job.
            base_path: The root directory where jobs are stored.
            
        Returns:
            Path: The path to the created job directory.
        """
        base = Path(base_path)
        job_dir = base / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    @staticmethod
    def get_job_directory(job_id: str, base_path: Union[str, Path]) -> Path:
        """
        Constructs the path for a job directory without creating it.
        
        Args:
            job_id: The unique identifier for the job.
            base_path: The root directory where jobs are stored.
            
        Returns:
            Path: The path to the job directory.
        """
        return Path(base_path) / job_id
