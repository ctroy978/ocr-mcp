import regex
from typing import Set, List

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
