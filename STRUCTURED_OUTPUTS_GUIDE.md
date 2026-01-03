# Structured Outputs Guide for AI API Calls

## ⚠️ CRITICAL: Always Use Structured Outputs for JSON Responses

When calling AI models (Grok 4+, OpenAI, etc.) and expecting **structured JSON responses**, you **MUST** use the `json_schema` response format with a strict schema definition. Never rely on prompt-only instructions like "return valid JSON".

---

## ✅ Correct Implementation

### Example: Essay Evaluation (server.py:870-924)

```python
# 1. Define a strict JSON schema
evaluation_schema = {
    "type": "object",
    "properties": {
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Criterion name"},
                    "score": {"type": ["string", "number"], "description": "Score"},
                    "feedback": {
                        "type": "object",
                        "properties": {
                            "examples": {"type": "array", "items": {"type": "string"}},
                            "advice": {"type": "string"},
                            "rewritten_example": {"type": "string"}
                        },
                        "required": ["examples", "advice", "rewritten_example"],
                        "additionalProperties": False
                    }
                },
                "required": ["name", "score", "feedback"],
                "additionalProperties": False
            }
        },
        "overall_score": {"type": "string"},
        "summary": {"type": "string"}
    },
    "required": ["criteria", "overall_score", "summary"],
    "additionalProperties": False
}

# 2. Use json_schema response format
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "essay_evaluation",      # Required: name for the schema
        "strict": True,                   # CRITICAL: Strongly enforces schema
        "schema": evaluation_schema
    }
}

# 3. Call the API with proper parameters
response = client.chat.completions.create(
    model="grok-4",                       # Or grok-beta, gpt-4, etc.
    messages=messages,
    response_format=response_format,      # ✅ Schema enforcement
    max_tokens=4000,                      # ✅ Prevent truncation
    temperature=0.1                       # ✅ Deterministic output
)

# 4. The response is GUARANTEED to be valid JSON matching the schema
result = json.loads(response.choices[0].message.content)
```

---

## ❌ WRONG: What NOT to Do

### Anti-Pattern 1: Prompt-Only Instructions
```python
# ❌ WRONG: No schema enforcement
messages = [
    {"role": "system", "content": "Return your response in valid JSON format."},
    {"role": "user", "content": "Evaluate this essay..."}
]

response = client.chat.completions.create(
    model="grok-4",
    messages=messages
    # No response_format parameter!
)
# Result: May return incomplete, malformed, or text-wrapped JSON
```

### Anti-Pattern 2: Using `json_object` Instead of `json_schema`
```python
# ❌ WRONG: json_object doesn't enforce a schema
response_format = {"type": "json_object"}  # Too loose!

# Result: Returns valid JSON, but structure may not match your expectations
```

### Anti-Pattern 3: Disabling for Specific Models
```python
# ❌ WRONG: Disabling structured outputs for certain models
response_format = (
    {"type": "json_object"} if "grok" not in model.lower() else None
)
# Result: Grok gets no enforcement → failures like Essay ID 55 error
```

### Anti-Pattern 4: No max_tokens Limit
```python
# ❌ WRONG: No token limit
response = client.chat.completions.create(
    model="grok-4",
    messages=messages,
    response_format=response_format
    # Missing max_tokens!
)
# Result: Long responses get truncated mid-JSON → unparseable
```

---

## 📋 Required Parameters Checklist

When calling AI APIs for structured responses, **ALWAYS include**:

- [ ] `response_format` with `type: "json_schema"`
- [ ] `json_schema.strict: True` for strong enforcement
- [ ] `json_schema.schema` with a complete schema definition
- [ ] `max_tokens` appropriate for response length (e.g., 4000 for evaluations)
- [ ] `temperature` set low (0.1-0.2) for deterministic output
- [ ] Schema includes `"additionalProperties": False` to prevent extra fields
- [ ] All required fields marked in schema `"required": [...]`

---

## 🔍 Audit Results: Current Codebase Status

### ✅ No Issues Found in Other Parts of Codebase

After auditing all AI API calls in the codebase:

| File/Function | Purpose | Needs JSON? | Status |
|---------------|---------|-------------|--------|
| `server.py:_evaluate_job_core` | Essay evaluation | ✅ Yes | ✅ **FIXED** (lines 870-924) |
| `server.py:_normalize_processed_job_core` | Text normalization | ❌ No (plain text) | ✅ Correct (line 776) |
| `server.py:ocr_image_with_qwen` | OCR text extraction | ❌ No (plain text) | ✅ Correct (line 324) |
| `edmcp/tools/ocr.py:ocr_image` | OCR text extraction | ❌ No (plain text) | ✅ Correct (line 150) |

**Conclusion:** The evaluation code was the **only** place requiring structured JSON outputs, and it has been fixed.

---

## 🛠️ When to Use Structured Outputs

### Use structured outputs when:
- ✅ You need **guaranteed JSON structure** (evaluation scores, metadata extraction)
- ✅ You're **parsing the response programmatically**
- ✅ The response will be **stored in a database** with a schema
- ✅ **Errors from malformed JSON** would break your workflow

### DON'T use structured outputs when:
- ❌ You only need **plain text** (normalization, OCR, summaries)
- ❌ Response is **for human reading only**
- ❌ Flexibility in format is acceptable

---

## 📚 Additional Resources

### Official Documentation
- **xAI Structured Outputs**: https://docs.x.ai/docs/guides/structured-outputs
- **OpenAI Structured Outputs**: https://platform.openai.com/docs/guides/structured-outputs

### Schema Design Tips
1. Keep schemas **simple and clear** (avoid deep nesting)
2. Add **descriptions** to properties for better AI understanding
3. Mark fields as `"required"` to guarantee presence
4. Use `"additionalProperties": False` to prevent unexpected fields
5. Test schemas with simple examples first

### Debugging Failed JSON Responses
If JSON parsing still fails despite using structured outputs:

1. **Check the full response** (don't just log first 100 chars)
   ```python
   print(f"Full response: {response.choices[0].message.content}", file=sys.stderr)
   ```

2. **Save to file for inspection**
   ```python
   with open("failed_response.json", "w") as f:
       f.write(response.choices[0].message.content)
   ```

3. **Verify model supports json_schema**
   - Grok 4+ ✅
   - Grok Beta ✅ (as of 2026)
   - GPT-4+ ✅
   - Older models ❌

4. **Check for token truncation**
   - Increase `max_tokens` if responses are incomplete
   - Monitor actual token usage in response metadata

---

## 🚨 Common Mistakes & Fixes

### Mistake 1: Schema doesn't match prompt expectations
```python
# ❌ Prompt asks for "grade", schema expects "score"
schema = {"properties": {"score": {"type": "string"}}}
prompt = "Return the grade as a number"
# Fix: Align terminology
schema = {"properties": {"grade": {"type": "number"}}}
```

### Mistake 2: Schema too restrictive
```python
# ❌ Model can't generate valid responses
schema = {
    "properties": {
        "score": {"type": "number", "minimum": 0, "maximum": 100}
    }
}
# But rubric uses letter grades (A, B, C...)
# Fix: Allow both
schema = {
    "properties": {
        "score": {"type": ["string", "number"]}  # Accepts "A" or 95
    }
}
```

### Mistake 3: Missing error handling
```python
# ❌ No fallback if JSON parsing fails
eval_data = json.loads(response.choices[0].message.content)

# ✅ Better: Use extract_json_from_text as safety net
eval_data = extract_json_from_text(response.choices[0].message.content)
if not eval_data:
    # Log full response, save to file, raise informative error
    ...
```

---

## 📝 Code Review Checklist

Before merging code that calls AI APIs:

- [ ] If expecting JSON, does it use `json_schema` response format?
- [ ] Is `strict: True` set in the schema?
- [ ] Does the schema match the expected response structure?
- [ ] Is `max_tokens` set appropriately (4000+ for complex responses)?
- [ ] Is `temperature` set low (0.1-0.2) for structured outputs?
- [ ] Are there error handlers that log the **full** response on failure?
- [ ] Are failed responses saved to files for debugging?
- [ ] Does the prompt align with the schema field names/types?

---

## 🎯 Quick Reference: Copy-Paste Template

```python
# Define your schema
my_schema = {
    "type": "object",
    "properties": {
        # Add your fields here
        "field1": {"type": "string", "description": "..."},
        "field2": {"type": "number", "description": "..."}
    },
    "required": ["field1", "field2"],
    "additionalProperties": False
}

# Call API with structured outputs
response = client.chat.completions.create(
    model="grok-4",                       # Or your preferred model
    messages=[
        {"role": "system", "content": "System prompt here"},
        {"role": "user", "content": "User prompt here"}
    ],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "my_response_schema",
            "strict": True,
            "schema": my_schema
        }
    },
    max_tokens=4000,
    temperature=0.1
)

# Parse result (should always be valid)
result = json.loads(response.choices[0].message.content)
```

---

**Last Updated:** 2026-01-02
**Applies to:** Grok 4+, Grok Beta, OpenAI GPT-4+, and compatible models
