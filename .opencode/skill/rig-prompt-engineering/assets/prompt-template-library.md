# Prompt Template Library (Rig + Rust)

These templates are designed for **Rig agents** and prioritize explicit structure, strict schemas, and tool clarity.
Use them as starting points, then add task-specific constraints and validation rules.

---

## 1) Classification Templates

### Sentiment (JSON output)
```
You are a concise classifier.
Classify sentiment as one of: Positive, Negative, Neutral.
Return JSON only: {"label":"Positive|Negative|Neutral","confidence":0.0}

Text: {text}
```

### Intent Detection
```
Determine intent from the message.
Allowed intents: {intent_list}
Return JSON only: {"intent":"<one of intent_list>","confidence":0.0}

Message: {message}
```

### Topic Classification
```
Classify the article into one category.
Categories: {categories}
Return JSON only: {"category":"<one of categories>"}

Article:
{article}
```

---

## 2) Extraction Templates

### Named Entity Extraction
```
Extract named entities and return JSON only.
Schema: {"persons":[],"organizations":[],"locations":[],"dates":[],"products":[]}

Text: {text}
```

### Structured Data Extraction
```
Extract structured information from the posting.
Return JSON only:
{"title":"","company":"","location":"","salary_range":"","requirements":[],"responsibilities":[]}

Job posting:
{posting}
```

---

## 3) Generation Templates

### Email Draft
```
Write a professional {email_type} email.
Constraints: {constraints}
Return JSON only: {"subject":"...","body":"..."}

To: {recipient}
Context: {context}
Key points: {key_points}
```

### Code Generation (Rust)
```
Generate Rust code for the task.
Requirements: {requirements}
Include error handling and input validation.
Return JSON only: {"code":"..."}

Task: {task_description}
```

---

## 4) Transformation Templates

### Summarization
```
Summarize the text in {num_sentences} sentences.
Return JSON only: {"summary":"..."}

Text:
{text}
```

### Format Conversion
```
Convert {source_format} to {target_format}.
Rules: {rules}
Return JSON only: {"output":"..."}

Input:
{input_data}
```

---

## 5) RAG + Citation Constraints (Expanded)

### RAG (strict grounding + citations)
```
Answer using only the provided context. If insufficient, say so.
Cite sources by filename and page: "<filename> p<page>:".
Return JSON only: {"answer":"...","citations":["file.pdf p2:","report.pdf p5:"],"grounded":true|false}

Context:
{context}

Question: {question}
```

### RAG (multi-snippet aggregation)
```
Use multiple snippets to answer if needed.
If answer requires assumptions, set grounded=false and explain briefly.
Return JSON only:
{"answer":"...","citations":["..."],"grounded":true|false,"notes":"..."}

Snippets:
{snippets}

Question: {question}
```

---

## 6) Tool Calling + Schema Validation (Expanded)

### Tool criteria + JSON schema guard
```
Call tools only when required input is missing or computation is external.
If no tool is needed, answer directly.
Return JSON only: {"status":"approved|pending|rejected","evidence":"<50 chars, include filename p<page>:"}
If invalid, fix and re-emit JSON only.
```

### Tool-then-answer pattern (Rig-native wording)
```
If required data is missing, call an available tool and then answer using returned context only.
Return JSON only: {"status":"...","evidence":"..."}
```

### Tool error handling
```
If tool fails or returns empty:
Return JSON only: {"status":"pending","evidence":"insufficient context"}
Do not invent data.
```

---

## 7) Structured Output + Self-correction (Expanded)

### JSON-only with retry
```
Return JSON only: {"field1":"...","field2":0}
If JSON is invalid or missing fields, fix and re-emit JSON only.
```

### Validation checklist embedded
```
Output JSON only with fields: {fields}.
Check:
- JSON parses
- required fields present
- enums valid
If any check fails, correct and re-emit JSON only.
```

---

## 8) Review / Audit Templates (Expanded)

### Code Review (Rig-style)
```
Review the code for:
- Bugs
- Performance
- Security
- Maintainability
Return JSON only:
{"issues":[{"severity":"blocking|important|nit","note":"...","file":"...","line":0}]}

Code:
{code}
```

### Change Review (diff)
```
Review the diff for correctness, scope, and tests.
Return JSON only:
{"issues":[{"severity":"blocking|important|nit","note":"...","path":"..."}],"verdict":"pass|mixed|fail"}

Diff:
{diff}
```

### Document Review (evidence required)
```
Review requirements against the document.
Evidence format: "filename p<page>:" and <= 50 chars.
Return JSON only:
{"status":"approved|pending|rejected","evidence":"..."}

Document:
{document}
```

---

## 9) Notes
- Keep schemas strict and minimal.
- Add validation instructions: “If invalid, fix and re-emit JSON only.”
- Add tool call criteria where tools are available.
- Prefer explicit evidence/citation formats.

## Use these templates by filling in the {variables}
