from typing import Optional

def get_evaluation_prompt(essay_text: str, rubric: str, context_material: str, system_instructions: Optional[str] = None) -> str:
    """
    Constructs the prompt for AI-based essay evaluation.
    Forces detailed, structured JSON output with criteria-specific feedback.
    """
    
    default_instructions = (
        "You are an expert academic evaluator specializing in providing consistent, structured feedback."
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
Evaluate the student's essay strictly according to the provided grading rubric. First, identify the distinct criteria from the rubric (e.g., "grammar", "theme").

For each criterion:
- Assign a score based on the points specified in the rubric.
- Provide feedback in this exact format:
  1. Justification: A 1-2 sentence explanation of WHY this score was assigned (explain what was done well or what was lacking).
  2. Specific examples: Quote 1-3 direct examples from the essay that justify the score.
  3. Advice on improvement: Give 1-2 actionable suggestions.
  4. Rewritten example: Provide a rewritten version of one of the quoted examples.

You must output ONLY a valid JSON object. The JSON must follow this exact structure:

{{
  "criteria": [
    {{
      "name": "Criterion Name",
      "score": "Numeric score or letter grade",
      "feedback": {{
        "justification": "Brief explanation of why this score was given",
        "examples": ["quote 1", "quote 2"],
        "advice": "Actionable advice string",
        "rewritten_example": "Improved version string"
      }}
    }}
  ],
  "overall_score": "Total score as a string (e.g. '95', 'A', '18/20')",
  "summary": "A brief overall summary of the essay's strengths and weaknesses."
}}

Do not add extra keys, explanations, or text outside the JSON.
"""
    return prompt.strip()