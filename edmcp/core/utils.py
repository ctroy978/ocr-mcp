
import json
import re
import sys
from typing import Any, Optional, Callable, Type, Union, Tuple
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

# Configure a logger for retries
logger = logging.getLogger("edmcp.utils")

def extract_json_from_text(text: str) -> Optional[dict]:
    """
    Extracts and parses the first JSON object found in a string.
    Handles Markdown code fences (```json ... ```) and leading/trailing text.
    """
    if not text:
        return None

    # Try to find JSON within Markdown code blocks first
    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block_match:
        json_str = code_block_match.group(1).strip()
    else:
        # Fallback: Find anything that looks like a JSON object using curly braces
        # This finds the first '{' and the last '}'
        start_index = text.find('{')
        end_index = text.rfind('}')
        
        if start_index == -1 or end_index == -1 or end_index <= start_index:
            return None
        
        json_str = text[start_index:end_index + 1].strip()

    try:
        # Basic cleanup: remove common LLM-injected artifacts if necessary
        # (Though json.loads is usually strict, we could add more cleanup here if needed)
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Last ditch effort: try to handle some common trailing comma issues if they occur
        try:
            # This is a very basic fix for trailing commas in simple objects
            # For complex nested objects, a real parser like dirtyjson or orjson might be better
            fixed_json = re.sub(r',\s*([\]}])', r'\1', json_str)
            return json.loads(fixed_json)
        except json.JSONDecodeError:
            return None

def retry_with_backoff(
    retries: int = 3,
    backoff_in_seconds: int = 1,
    max_wait_in_seconds: int = 10,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
) -> Callable:
    """
    A decorator that retries a function with exponential backoff.
    """
    return retry(
        stop=stop_after_attempt(retries),
        wait=wait_exponential(multiplier=backoff_in_seconds, max=max_wait_in_seconds),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.INFO),
        reraise=True
    )
