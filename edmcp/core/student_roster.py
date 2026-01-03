import csv
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
from edmcp.core.name_loader import NameLoader


@dataclass
class StudentInfo:
    """Data class representing a student record from school_names.csv"""
    id: int
    first_name: str
    last_name: str
    full_name: str
    grade: str
    email: str


class StudentRoster:
    """
    Extended student roster management with email lookup capabilities.
    Builds on NameLoader to provide email address mapping for student notifications.
    """

    def __init__(self, names_dir: Path):
        self.names_dir = Path(names_dir)
        self.name_loader = NameLoader(names_dir)
        self._student_map: Dict[str, StudentInfo] = {}
        self._load_roster()

    def _normalize(self, name: str) -> str:
        """Normalize name for case-insensitive matching"""
        return name.strip().lower()

    def _load_roster(self):
        """
        Loads school_names.csv with full student information including emails.
        Populates internal student map keyed by normalized full name.
        """
        self._student_map.clear()
        school_file = self.names_dir / "school_names.csv"

        if not school_file.exists():
            return

        with open(school_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Extract fields from CSV
                student_id = row.get("id", "")
                first = row.get("first_name", "").strip()
                last = row.get("last_name", "").strip()
                grade = row.get("grade", "").strip()
                email = row.get("email", "").strip()

                if first and last:
                    full_name = f"{first} {last}"
                    normalized_name = self._normalize(full_name)

                    # Create StudentInfo object
                    student_info = StudentInfo(
                        id=int(student_id) if student_id.isdigit() else 0,
                        first_name=first,
                        last_name=last,
                        full_name=full_name,
                        grade=grade,
                        email=email
                    )

                    # Map normalized name to student info
                    self._student_map[normalized_name] = student_info

    def get_email_for_student(self, student_name: str) -> Optional[str]:
        """
        Looks up email address for a student by their full name.
        Handles normalization for case-insensitive matching.

        Args:
            student_name: Student's full name (e.g., "John Doe")

        Returns:
            Email address if found, None otherwise
        """
        normalized = self._normalize(student_name)
        student_info = self._student_map.get(normalized)

        if student_info and student_info.email:
            return student_info.email
        return None

    def get_student_info(self, student_name: str) -> Optional[StudentInfo]:
        """
        Returns full student record including grade, email, etc.

        Args:
            student_name: Student's full name (e.g., "John Doe")

        Returns:
            StudentInfo object if found, None otherwise
        """
        normalized = self._normalize(student_name)
        return self._student_map.get(normalized)

    def get_all_students(self) -> Dict[str, StudentInfo]:
        """
        Returns the complete student roster.

        Returns:
            Dictionary mapping normalized names to StudentInfo objects
        """
        return self._student_map.copy()

    def get_students_with_emails(self) -> Dict[str, StudentInfo]:
        """
        Returns only students who have email addresses in the roster.

        Returns:
            Dictionary mapping normalized names to StudentInfo objects (email field non-empty)
        """
        return {
            name: info
            for name, info in self._student_map.items()
            if info.email
        }
