# Chain-of-Thought Prompting (Rig + Rust)

## Overview

Chain-of-Thought (CoT) prompting helps with complex reasoning, math, and multi-step logic. In production settings, **do not request full chain-of-thought output**. Instead, instruct internal reasoning and return a concise final answer or short rationale.

## Dependencies

- Standard library only

## Core Techniques

### Zero-shot CoT (internal reasoning)
Ask for reasoning implicitly, output only final answer:

```
Solve the problem. Do your reasoning internally, then output only the final answer.
```

### Few-shot CoT (short rationale)
Provide short rationales instead of full steps:

```
Q: Roger has 5 tennis balls. He buys 2 cans. Each can has 3 balls. How many now?
A: 11. (5 + 2*3)

Q: The cafeteria had 23 apples. Used 20 and bought 6. How many now?
A: 9. (23 - 20 + 6)

Q: {user_query}
A:
```

### Self-consistency (majority vote)
Run multiple samples and pick the most common answer:

```rust
use std::collections::HashMap;

fn self_consistency<F>(prompt: &str, n: usize, mut run: F) -> Option<(String, f32)>
where
    F: FnMut(&str) -> String,
{
    let mut counts: HashMap<String, usize> = HashMap::new();

    for _ in 0..n {
        let out = run(prompt);
        *counts.entry(out.clone()).or_insert(0) += 1;
    }

    let (best, best_count) = counts.into_iter().max_by_key(|(_, c)| *c)?;
    let confidence = best_count as f32 / n as f32;
    Some((best, confidence))
}
```

## Advanced Patterns

### Least-to-Most Prompting
Break complex problems into simpler subproblems, solve, then integrate:

```rust
fn least_to_most(problem: &str, decompose: impl Fn(&str) -> Vec<String>, solve: impl Fn(&str) -> String) -> String {
    let subproblems = decompose(problem);
    let mut context = String::new();

    for sub in &subproblems {
        let solution = solve(sub);
        context.push_str(&format!("Subproblem: {sub}\nSolution: {solution}\n\n"));
    }

    solve(&format!("Given these solutions:\n{context}\nFinal answer:"))
}
```

### Tree-of-Thought (ToT)
Generate multiple reasoning branches, score, and pick best:

```rust
fn tree_of_thought(problem: &str, expand: impl Fn(&str) -> Vec<String>, score: impl Fn(&str) -> f32, depth: usize) -> Option<String> {
    let mut frontier = vec![problem.to_string()];

    for _ in 0..depth {
        let mut next = Vec::new();
        for node in frontier {
            for child in expand(&node) {
                next.push(child);
            }
        }
        frontier = next;
    }

    frontier
        .into_iter()
        .max_by(|a, b| score(a).partial_cmp(&score(b)).unwrap_or(std::cmp::Ordering::Equal))
}
```

### ToT Scoring Rubric (detailed)
Score each branch on multiple axes and compute a weighted total:
- Correctness (0-10)
- Completeness (0-10)
- Logical coherence (0-10)
- Constraint adherence (0-10)
- Minimal verbosity (0-10)

Example weighting:
- correctness 0.35
- completeness 0.20
- coherence 0.20
- constraints 0.20
- verbosity 0.05

### ToT Search Strategy (expanded)
1. Generate candidate next steps.
2. Score each candidate.
3. Keep top-k for the next depth.
4. Repeat until depth limit or score threshold.
5. Choose best path and produce final answer.

### Verification Step
Add verification without exposing reasoning:

```
Provide the final answer. Then silently verify key steps and correct if needed.
```

## Domain-Specific CoT (short rationale forms)

### Math Problems
```
Problem: {problem}
Answer: {final_answer} (brief justification)
```

### Code Debugging
```
Code: {code}
Error: {error}
Answer: {fix_summary} (why it works)
```

### Logical Reasoning
```
Premises: {premises}
Question: {question}
Answer: {final_answer} (short rationale)
```

## Performance Optimization

### Caching Reasoning Patterns
Store short rationales for repeated tasks:

```rust
use std::collections::HashMap;

struct ReasoningCache {
    cache: HashMap<String, String>,
}

impl ReasoningCache {
    fn get(&self, key: &str) -> Option<&String> {
        self.cache.get(key)
    }

    fn add(&mut self, key: String, rationale: String) {
        self.cache.insert(key, rationale);
    }
}
```

### Adaptive Reasoning Depth
Increase depth only when needed:

```rust
fn adaptive_depth(problem: &str, mut solve: impl FnMut(&str, usize) -> String) -> String {
    let mut depth = 2usize;
    loop {
        let out = solve(problem, depth);
        if !out.is_empty() { return out; }
        depth += 2;
        if depth > 10 { return out; }
    }
}
```

## Evaluation Metrics

```rust
struct CotMetrics {
    coherence: f32,
    completeness: f32,
    correctness: f32,
    efficiency: f32,
    clarity: f32,
}
```

## Best Practices

1. Use short rationale instead of full chain-of-thought.
2. Verify calculations or logic silently.
3. Keep prompts consistent across examples.
4. Add edge cases to test reasoning robustness.
5. Use multiple runs for uncertain problems.

## Common Pitfalls

- Asking for full chain-of-thought output.
- Inconsistent output formats.
- Overcomplicated reasoning instructions.
- Using CoT for trivial questions.

## When to Use CoT

**Use CoT for:**
- Math and arithmetic problems
- Logical reasoning tasks
- Multi-step planning
- Code generation and debugging
- Complex decision making

**Skip CoT for:**
- Simple factual queries
- Direct lookups
- Tasks requiring strict JSON-only output
- Real-time, latency-sensitive applications

## Resources

- Reasoning verification checklists
- Few-shot rationale templates
- Multi-branch evaluation tooling
- Error analysis rubrics
