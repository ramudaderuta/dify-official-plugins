// Prompt Optimization Script (Rig + Rust)
//
// A 1:1 Rust port of the Python teaching script:
// - Parallel evaluation of test cases
// - Metrics (accuracy, latency, p95, token count, success rate)
// - Iterative optimization with variations
// - A/B testing
// - Export results to JSON

use std::fs::File;
use std::io::Write;
use std::sync::Arc;
use std::thread;
use std::time::Instant;

#[derive(Clone)]
struct TestCase {
    input: std::collections::HashMap<String, String>,
    expected_output: String,
}

#[derive(Clone, Default)]
struct Metrics {
    avg_accuracy: f32,
    avg_latency: f32,
    p95_latency: f32,
    avg_tokens: f32,
    success_rate: f32,
}

#[derive(Clone)]
struct HistoryEntry {
    iteration: usize,
    prompt: String,
    metrics: Metrics,
}

trait LlmClient: Send + Sync {
    fn complete(&self, prompt: &str) -> String;
}

struct PromptOptimizer {
    client: Arc<dyn LlmClient>,
    test_suite: Vec<TestCase>,
    results_history: Vec<HistoryEntry>,
}

impl PromptOptimizer {
    fn new(client: Arc<dyn LlmClient>, test_suite: Vec<TestCase>) -> Self {
        Self { client, test_suite, results_history: Vec::new() }
    }

    fn evaluate_prompt(&self, prompt_template: &str, test_cases: Option<&[TestCase]>) -> Metrics {
        let cases = test_cases.unwrap_or(&self.test_suite);

        // Run test cases in parallel threads
        let mut handles = Vec::new();
        for case in cases.iter().cloned() {
            let client = Arc::clone(&self.client);
            let template = prompt_template.to_string();
            let handle = thread::spawn(move || {
                let start = Instant::now();

                // Render prompt with test case inputs
                let mut rendered = template.clone();
                for (k, v) in case.input.iter() {
                    rendered = rendered.replace(&format!("{{{}}}", k), v);
                }

                // Get response
                let response = client.complete(&rendered);
                let latency = start.elapsed().as_secs_f32();

                // Token count (rough)
                let token_count = rendered.split_whitespace().count() + response.split_whitespace().count();
                let success = if response.is_empty() { 0.0 } else { 1.0 };
                let accuracy = PromptOptimizer::calculate_accuracy(&response, &case.expected_output);

                (latency, token_count as f32, success, accuracy)
            });
            handles.push(handle);
        }

        let mut latencies = Vec::new();
        let mut token_counts = Vec::new();
        let mut successes = Vec::new();
        let mut accuracies = Vec::new();

        for h in handles {
            let (lat, tok, suc, acc) = h.join().unwrap();
            latencies.push(lat);
            token_counts.push(tok);
            successes.push(suc);
            accuracies.push(acc);
        }

        Metrics {
            avg_accuracy: mean(&accuracies),
            avg_latency: mean(&latencies),
            p95_latency: percentile(&latencies, 0.95),
            avg_tokens: mean(&token_counts),
            success_rate: mean(&successes),
        }
    }

    fn calculate_accuracy(response: &str, expected: &str) -> f32 {
        if response.trim().eq_ignore_ascii_case(expected.trim()) {
            return 1.0;
        }

        let response_words: std::collections::HashSet<_> = response.to_lowercase().split_whitespace().collect();
        let expected_words: std::collections::HashSet<_> = expected.to_lowercase().split_whitespace().collect();

        if expected_words.is_empty() { return 0.0; }
        let overlap = response_words.intersection(&expected_words).count() as f32;
        overlap / expected_words.len() as f32
    }

    fn optimize(&mut self, base_prompt: &str, max_iterations: usize) -> (String, f32) {
        let mut current_prompt = base_prompt.to_string();
        let mut best_prompt = current_prompt.clone();
        let mut best_score = 0.0f32;

        for i in 0..max_iterations {
            let metrics = self.evaluate_prompt(&current_prompt, None);
            println!("\nIteration {}/{}", i + 1, max_iterations);
            println!("Accuracy: {:.2}, Latency: {:.2}s", metrics.avg_accuracy, metrics.avg_latency);

            self.results_history.push(HistoryEntry {
                iteration: i,
                prompt: current_prompt.clone(),
                metrics: metrics.clone(),
            });

            if metrics.avg_accuracy > best_score {
                best_score = metrics.avg_accuracy;
                best_prompt = current_prompt.clone();
            }

            if metrics.avg_accuracy > 0.95 {
                println!("Achieved target accuracy!");
                break;
            }

            let variations = self.generate_variations(&current_prompt);
            let mut best_variation = current_prompt.clone();
            let mut best_variation_score = metrics.avg_accuracy;

            for variation in variations {
                let var_metrics = self.evaluate_prompt(&variation, None);
                if var_metrics.avg_accuracy > best_variation_score {
                    best_variation_score = var_metrics.avg_accuracy;
                    best_variation = variation;
                }
            }

            current_prompt = best_variation;
        }

        (best_prompt, best_score)
    }

    fn generate_variations(&self, prompt: &str) -> Vec<String> {
        let mut variations = Vec::new();

        variations.push(format!("{}\n\nProvide your answer in a clear, concise format.", prompt));
        variations.push(format!("Let's solve this step by step.\n\n{}", prompt));
        variations.push(format!("{}\n\nVerify your answer before responding.", prompt));

        let concise = self.make_concise(prompt);
        if concise != prompt { variations.push(concise); }

        if !prompt.to_lowercase().contains("example") {
            variations.push(self.add_examples(prompt));
        }

        variations.truncate(3);
        variations
    }

    fn make_concise(&self, prompt: &str) -> String {
        let replacements = [
            ("in order to", "to"),
            ("due to the fact that", "because"),
            ("at this point in time", "now"),
            ("in the event that", "if"),
        ];

        let mut result = prompt.to_string();
        for (old, new) in replacements.iter() {
            result = result.replace(old, new);
        }
        result
    }

    fn add_examples(&self, prompt: &str) -> String {
        format!(
            "{prompt}\n\nExample:\nInput: Sample input\nOutput: Sample output\n"
        )
    }

    fn compare_prompts(&self, prompt_a: &str, prompt_b: &str) -> (Metrics, Metrics, String, f32) {
        println!("Testing Prompt A...");
        let metrics_a = self.evaluate_prompt(prompt_a, None);

        println!("Testing Prompt B...");
        let metrics_b = self.evaluate_prompt(prompt_b, None);

        let winner = if metrics_a.avg_accuracy > metrics_b.avg_accuracy { "A" } else { "B" };
        let improvement = (metrics_a.avg_accuracy - metrics_b.avg_accuracy).abs();

        (metrics_a, metrics_b, winner.to_string(), improvement)
    }

    fn export_results(&self, filename: &str) {
        let json = history_to_json(&self.results_history);
        let mut file = File::create(filename).expect("failed to open file");
        file.write_all(json.as_bytes()).expect("failed to write file");
    }
}

fn mean(values: &[f32]) -> f32 {
    if values.is_empty() { return 0.0; }
    values.iter().sum::<f32>() / values.len() as f32
}

fn percentile(values: &[f32], p: f32) -> f32 {
    if values.is_empty() { return 0.0; }
    let mut sorted = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
    let idx = ((sorted.len() - 1) as f32 * p).round() as usize;
    sorted[idx]
}

fn history_to_json(history: &[HistoryEntry]) -> String {
    let mut out = String::from("[");
    for (i, h) in history.iter().enumerate() {
        if i > 0 { out.push(','); }
        out.push_str(&format!(
            "{{\"iteration\":{},\"prompt\":{},\"metrics\":{{\"avg_accuracy\":{:.4},\"avg_latency\":{:.4},\"p95_latency\":{:.4},\"avg_tokens\":{:.4},\"success_rate\":{:.4}}}}}",
            h.iteration,
            json_escape(&h.prompt),
            h.metrics.avg_accuracy,
            h.metrics.avg_latency,
            h.metrics.p95_latency,
            h.metrics.avg_tokens,
            h.metrics.success_rate
        ));
    }
    out.push(']');
    out
}

fn json_escape(s: &str) -> String {
    let mut out = String::from("\"");
    for ch in s.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            _ => out.push(ch),
        }
    }
    out.push('"');
    out
}

// Example usage
struct MockLlmClient;
impl LlmClient for MockLlmClient {
    fn complete(&self, prompt: &str) -> String {
        if prompt.contains("amazing") {
            "Positive".to_string()
        } else if prompt.to_lowercase().contains("worst") {
            "Negative".to_string()
        } else {
            "Neutral".to_string()
        }
    }
}

fn main() {
    let test_suite = vec![
        TestCase {
            input: map_of(vec![("text", "This movie was amazing!")]),
            expected_output: "Positive".to_string(),
        },
        TestCase {
            input: map_of(vec![("text", "Worst purchase ever.")]),
            expected_output: "Negative".to_string(),
        },
        TestCase {
            input: map_of(vec![("text", "It was okay, nothing special.")]),
            expected_output: "Neutral".to_string(),
        },
    ];

    let client = Arc::new(MockLlmClient);
    let mut optimizer = PromptOptimizer::new(client, test_suite);

    let base_prompt = "Classify the sentiment of: {text}\nSentiment:";
    let (best_prompt, best_score) = optimizer.optimize(base_prompt, 5);

    println!("\n==================================================");
    println!("Optimization Complete!");
    println!("Best Accuracy: {:.2}", best_score);
    println!("Best Prompt:\n{}", best_prompt);

    optimizer.export_results("optimization_results.json");

    // A/B test example
    let (ma, mb, winner, improvement) = optimizer.compare_prompts(
        base_prompt,
        "Classify sentiment. Return only one of: Positive, Negative, Neutral.",
    );
    println!("A/B winner: {}, improvement: {:.2}", winner, improvement);
    println!("A acc: {:.2}, B acc: {:.2}", ma.avg_accuracy, mb.avg_accuracy);
}

fn map_of(items: Vec<(&str, &str)>) -> std::collections::HashMap<String, String> {
    let mut map = std::collections::HashMap::new();
    for (k, v) in items {
        map.insert(k.to_string(), v.to_string());
    }
    map
}
