from typing import Optional

def get_evaluation_prompt(essay_text: str, rubric: str, context_material: str, system_instructions: Optional[str] = None) -> str:
    """
    Constructs the prompt for AI-based essay evaluation.
    Forces JSON output for easier parsing of score and comments.
    """
    
    default_instructions = (
        "You are an expert academic evaluator. Your task is to grade the provided student essay "
        "based strictly on the grading rubric and the provided context/source material. "
        "Maintain high standards and provide constructive, specific feedback."
    )
    
    instructions = system_instructions or default_instructions
    
    prompt = f"""
{instructions}

---
# GRADING RUBRIC:
{rubric}

---
# CONTEXT / SOURCE MATERIAL:
{context_material}

---
# STUDENT ESSAY:
{essay_text}

---
# OUTPUT INSTRUCTIONS:
Return your evaluation in JSON format with the following keys:
1. "score": A numeric value or letter grade as defined by the rubric.
2. "comments": A detailed explanation of the score, referencing specific parts of the essay and the rubric.
3. "summary": A brief (1-2 sentence) summary of the student's performance.

Return ONLY the JSON object. Do not add any introductory or concluding text.
"""
    return prompt.strip()
