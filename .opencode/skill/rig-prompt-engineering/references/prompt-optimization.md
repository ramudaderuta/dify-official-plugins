# Prompt Optimization Guide (Rig + Rust)

## Systematic Refinement Process

Prompt optimization is iterative: baseline -> test -> analyze -> refine -> re-test. The goal is to improve **accuracy and schema compliance** without ballooning tokens or latency.

## Dependencies

- Standard library only

### 1) Baseline Establishment
Start with a clear baseline so improvements are measurable.

```rust
struct Metrics {
    accuracy: f32,
    avg_tokens: f32,
    avg_latency_ms: f32,
    success_rate: f32,
}

fn establish_baseline<F>(prompt: &str, tests: &[(&str, &str)], run: F) -> Metrics
where
    F: Fn(&str) -> String,
{
    let mut accuracy = 0.0;
    let mut tokens = 0.0;
    let mut latency = 0.0;
    let mut success = 0.0;

    for (input, expected) in tests {
        let rendered = prompt.replace("{input}", input);
        let start = std::time::Instant::now();
        let out = run(&rendered);
        let elapsed = start.elapsed().as_millis() as f32;

        latency += elapsed;
        tokens += rendered.split_whitespace().count() as f32;
        tokens += out.split_whitespace().count() as f32;

        if !out.is_empty() { success += 1.0; }
        if out.trim().eq_ignore_ascii_case(expected) { accuracy += 1.0; }
    }

    let n = tests.len() as f32;
    Metrics {
        accuracy: accuracy / n,
        avg_tokens: tokens / n,
        avg_latency_ms: latency / n,
        success_rate: success / n,
    }
}
```

### 2) Iterative Refinement Workflow
```
Baseline -> Test -> Analyze Failures -> Refine -> Test -> Repeat
```

```rust
struct PromptOptimizer {
    prompt: String,
    history: Vec<(String, Metrics)>,
}

impl PromptOptimizer {
    fn new(prompt: String) -> Self {
        Self { prompt, history: Vec::new() }
    }

    fn optimize<F>(&mut self, tests: &[(&str, &str)], run: F, max_iterations: usize) -> String
    where
        F: Fn(&str) -> String,
    {
        let mut best = self.prompt.clone();
        let mut best_score = 0.0;

        for _ in 0..max_iterations {
            let metrics = establish_baseline(&self.prompt, tests, &run);
            self.history.push((self.prompt.clone(), metrics));

            if metrics.accuracy > best_score {
                best_score = metrics.accuracy;
                best = self.prompt.clone();
            }

            if metrics.accuracy >= 0.95 { break; }

            // Example refinement: tighten schema instructions
            self.prompt = format!("{}\n\nReturn JSON only.", self.prompt);
        }

        best
    }
}
```

### 3) A/B Testing Framework
Compare two prompts and choose the best for your target metric (accuracy, latency, schema validity).

```rust
fn ab_test<F>(a: &str, b: &str, tests: &[(&str, &str)], run: F) -> (Metrics, Metrics)
where
    F: Fn(&str) -> String,
{
    let ma = establish_baseline(a, tests, &run);
    let mb = establish_baseline(b, tests, &run);
    (ma, mb)
}
```

### 4) Statistical Significance (t-statistic)
Compute t-statistic on two samples; p-value can be added with a stats crate.

```rust
fn mean(xs: &[f32]) -> f32 {
    xs.iter().sum::<f32>() / xs.len() as f32
}

fn variance(xs: &[f32]) -> f32 {
    let m = mean(xs);
    xs.iter().map(|x| (x - m) * (x - m)).sum::<f32>() / (xs.len() as f32 - 1.0)
}

fn t_statistic(a: &[f32], b: &[f32]) -> f32 {
    let ma = mean(a);
    let mb = mean(b);
    let va = variance(a);
    let vb = variance(b);
    let na = a.len() as f32;
    let nb = b.len() as f32;
    (ma - mb) / ((va / na + vb / nb).sqrt())
}
```

## Optimization Strategies

### Token Reduction
- Remove redundant phrases.
- Compress multi-step instructions into a single list.
- Define abbreviations once, then reuse.

### Latency Reduction
- Reduce prompt length and avoid excessive examples.
- Cache static sections (preamble, schema).
- Avoid tool calls unless required.

### Accuracy Improvement
- Add explicit schema constraints.
- Add 1–2 representative examples (not 10).
- Add a verification step (self-check).

## Performance Metrics

### Core Metrics
- Accuracy
- Token usage
- Latency (avg/p95)
- Success rate (valid output)

### Automated Evaluation (multi-run)
Run each test case multiple times and take best-of or majority:

```rust
fn evaluate_multi<F>(prompt: &str, tests: &[(&str, &str)], run: F, repeats: usize) -> Metrics
where
    F: Fn(&str) -> String,
{
    let mut best_metrics = Metrics { accuracy: 0.0, avg_tokens: 0.0, avg_latency_ms: 0.0, success_rate: 0.0 };
    for _ in 0..repeats {
        let m = establish_baseline(prompt, tests, &run);
        if m.accuracy > best_metrics.accuracy { best_metrics = m; }
    }
    best_metrics
}
```

### Consistency Metric
Measure how often identical inputs produce identical outputs.

```rust
use std::collections::HashMap;

fn consistency_rate(outputs: &[String]) -> f32 {
    if outputs.is_empty() { return 1.0; }
    let mut counts: HashMap<String, usize> = HashMap::new();
    for o in outputs { *counts.entry(o.clone()).or_insert(0) += 1; }
    let max = counts.values().cloned().max().unwrap_or(0) as f32;
    max / outputs.len() as f32
}
```

## Failure Analysis

### Categorizing Failures
- Format errors (invalid JSON, missing field)
- Factual errors (wrong values)
- Logic errors (contradictions)
- Incomplete responses
- Hallucinations
- Off-topic responses

### Generating Fixes
- Format errors -> stricter schema + JSON-only
- Hallucinations -> grounding rules and explicit context limits
- Incomplete -> add checklist or minimum fields

Example fix generator:
```rust
fn suggest_fix(category: &str) -> &'static str {
    match category {
        "format" => "Add JSON-only constraint and re-emit instruction",
        "hallucination" => "Add grounding: use only provided context",
        "incomplete" => "Add checklist of required fields",
        _ => "Add clarifying constraint",
    }
}
```

## Versioning and Rollback

### Prompt Version Control (Rust sketch)
```rust
#[derive(Clone)]
struct PromptVersion {
    id: usize,
    prompt: String,
    metrics: Metrics,
}

struct PromptVC {
    versions: Vec<PromptVersion>,
}

impl PromptVC {
    fn save(&mut self, prompt: String, metrics: Metrics) {
        let id = self.versions.len();
        self.versions.push(PromptVersion { id, prompt, metrics });
    }

    fn rollback(&self, id: usize) -> Option<&String> {
        self.versions.get(id).map(|v| &v.prompt)
    }

    fn compare(&self, a: usize, b: usize) -> Option<(Metrics, Metrics)> {
        Some((self.versions.get(a)?.metrics.clone(), self.versions.get(b)?.metrics.clone()))
    }
}
```

## Best Practices

1. Establish a baseline.
2. Change one thing at a time.
3. Track metrics and failures.
4. Keep prompts concise and explicit.
5. Version prompts like code.

## Common Optimization Patterns

### Pattern 1: Add Structure
```
Before: "Analyze this text"
After: "Analyze for: 1) Topic 2) Key points 3) Conclusion"
```

### Pattern 2: Add Examples
```
Before: "Extract entities"
After: "Extract entities. Example: Input: ... Output: {...}"
```

### Pattern 3: Add Constraints
```
Before: "Summarize this"
After: "Summarize in 3 bullet points, 15 words each"
```

### Pattern 4: Add Verification
```
Before: "Calculate..."
After: "Calculate... Then verify before responding"
```

## Tools and Utilities

- Prompt diffs for version comparison
- Automated test runners
- Metric dashboards
- Token counting utilities
- Latency profilers

## Teaching Notes

- Prefer one strong example over many weak ones.
- Use explicit schemas to prevent drift.
- When testing, keep inputs fixed so comparisons are fair.
- If accuracy is high but schema invalid, fix schema first.
