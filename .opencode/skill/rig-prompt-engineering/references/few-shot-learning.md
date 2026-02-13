# Few-Shot Learning Guide (Rig + Rust)

## Overview

Few-shot learning enables LLMs to perform tasks by providing a small number of examples. It is especially effective for structured JSON outputs and tool-using Rig agents. The goal is to teach format, constraints, and edge cases with minimal tokens.

## Dependencies

- Standard library only

## Example Selection Strategies

### 1) Semantic Similarity (token overlap)
Select examples most similar to the input using token overlap.

```rust
use std::collections::HashSet;

#[derive(Clone)]
struct Example {
    input: String,
    output: String,
    tags: Vec<String>,
    difficulty: u8,
}

fn token_overlap_score(a: &str, b: &str) -> f32 {
    let sa: HashSet<_> = a.split_whitespace().collect();
    let sb: HashSet<_> = b.split_whitespace().collect();
    let inter = sa.intersection(&sb).count() as f32;
    let union = sa.union(&sb).count() as f32;
    if union == 0.0 { 0.0 } else { inter / union }
}

fn select_by_similarity(examples: &[Example], query: &str, k: usize) -> Vec<Example> {
    let mut scored: Vec<(f32, Example)> = examples
        .iter()
        .cloned()
        .map(|ex| (token_overlap_score(&ex.input, query), ex))
        .collect();

    scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
    scored.into_iter().take(k).map(|(_, ex)| ex).collect()
}
```

**Best for:** QA, classification, extraction

### 2) Diversity Sampling (round-robin by tag)
Choose examples that cover different tags.

```rust
use std::collections::HashMap;

fn select_diverse(examples: &[Example], k: usize) -> Vec<Example> {
    let mut buckets: HashMap<String, Vec<Example>> = HashMap::new();
    for ex in examples {
        let tag = ex.tags.get(0).cloned().unwrap_or_else(|| "default".to_string());
        buckets.entry(tag).or_default().push(ex.clone());
    }

    let mut selected = Vec::new();
    while selected.len() < k {
        let mut progress = false;
        for bucket in buckets.values_mut() {
            if let Some(ex) = bucket.pop() {
                selected.push(ex);
                progress = true;
                if selected.len() >= k { break; }
            }
        }
        if !progress { break; }
    }

    selected
}
```

**Best for:** showing variability and edge cases

### 3) Difficulty-Based Selection
Arrange examples from easy to hard to scaffold behavior.

```rust
fn select_progressive(examples: &[Example], k: usize) -> Vec<Example> {
    let mut v = examples.to_vec();
    v.sort_by_key(|e| e.difficulty);
    v.into_iter().take(k).collect()
}
```

**Best for:** complex reasoning or code tasks

### 4) Error-Based Selection
Include examples that address known failure modes.

```rust
fn select_error_guided(examples: &[Example], k: usize, tag: &str) -> Vec<Example> {
    examples
        .iter()
        .cloned()
        .filter(|e| e.tags.iter().any(|t| t == tag))
        .take(k)
        .collect()
}
```

**Best for:** safety-critical or high-precision tasks

## Example Construction Best Practices

### Format Consistency
All examples must share the same format.

```
Input: "What is the capital of France?"
Output: "Paris"
```

### Input-Output Alignment
Ensure outputs match the exact task, not an explanation.

```
Input: "Sentiment: The movie was terrible."
Output: "Negative"
```

### Complexity Balance
Include simple, moderate, and tricky examples.

```
Input: "2 + 2"
Output: "4"

Input: "(12 + 8) * 3 - 15 / 5"
Output: "57"
```

## Context Window Management

### Token Budget Allocation (typical)
```
System: 500 tokens
Few-shot: 1500 tokens
User input: 500 tokens
Response: 1500 tokens
```

### Dynamic Example Truncation
Keep only what fits:

```rust
fn truncate_examples(examples: &[Example], max_tokens: usize) -> Vec<Example> {
    let mut selected = Vec::new();
    let mut total = 0usize;

    for ex in examples {
        let tokens = ex.input.split_whitespace().count() + ex.output.split_whitespace().count();
        if total + tokens > max_tokens { break; }
        selected.push(ex.clone());
        total += tokens;
    }

    selected
}
```

### Token-Aware Selector (rank + trim)
Rank by relevance, then trim to budget:

```rust
fn select_token_aware(ranked: &[Example], max_tokens: usize) -> Vec<Example> {
    let mut selected = Vec::new();
    let mut total = 0usize;

    for ex in ranked {
        let tokens = ex.input.split_whitespace().count() + ex.output.split_whitespace().count();
        if total + tokens > max_tokens { break; }
        selected.push(ex.clone());
        total += tokens;
    }

    selected
}
```

## Failure-Mode Guided Examples

Common failure modes and example fixes:
- **Schema drift** -> include JSON-only example with exact schema
- **Hallucination** -> include refusal/insufficient example
- **Tool misuse** -> include tool-call example and non-tool example
- **Overlong output** -> include length-constrained example

## Edge Case Handling

Include explicit boundary examples:

```
Input: ""
Output: "insufficient input"

Input: "bank"
Output: "ambiguous"
```

## Few-Shot Prompt Templates

### Classification Template
```
Classify into one of: {labels}

{examples}

Input: {input}
Output:
```

### Extraction Template
```
Extract fields: {fields}

{examples}

Input: {input}
Output (JSON):
```

### Tool-Using Template
```
Call tools only if required. Otherwise answer directly.

{examples}

Input: {input}
Output (JSON):
```

### RAG Template (grounded)
```
Use only the provided context. If insufficient, say so.

{examples}

Context: {context}
Question: {question}
Answer (JSON):
```

## Dynamic Truncation Strategies (extended)

### Rank-then-trim
1. Rank by relevance.
2. Add examples until budget hit.
3. Drop the lowest impact example.

### Trim-by-section
If examples are long, remove optional fields first (extra notes, long rationales) before dropping the example entirely.

## Evaluation Guidance

- Track schema validity rate per example set.
- Compare accuracy with and without examples.
- If few-shot hurts accuracy, reduce or change examples.

## Best Practices

1. Keep examples short and realistic.
2. Use exact output schema in each example.
3. Include one refusal/insufficient example when appropriate.
4. Test against diverse inputs and log failures.
5. Version examples as part of prompt changes.

## Common Pitfalls

- Inconsistent formatting across examples.
- Examples that are too long or off-topic.
- Examples that contradict the schema.
- Too many examples crowding out the task.

## When to Use Few-Shot

**Use few-shot for:**
- Structured JSON outputs
- Tool call behaviors
- Edge-case-sensitive tasks

**Skip few-shot for:**
- Simple lookup tasks
- Extremely low-latency flows
- When token budget is too tight

## Teaching Notes

- Good examples are more valuable than many examples.
- Keep example distributions similar to real traffic.
- If failures persist, add one targeted example rather than broadening all examples.
- When adding examples, re-check token budget and output stability.
