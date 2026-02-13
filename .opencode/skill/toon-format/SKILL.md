---
name: toon-format
description: use when encoding or decoding JSON/serde types with the official Rust crate or CLI, converting data to/from TOON, or answering questions about TOON syntax, headers, arrays, key folding/path expansion, strict mode, and spec compliance.
---

Use this skill whenever you need to convert data to/from TOON, wire the `toon-format` Rust crate into a project, or reference TOON specification rules.

## Quick workflow
- Choose path: Rust library (`toon-format`), CLI (`toon`), or spec-only guidance.
- Library: `cargo add toon-format`; start with `encode_default` / `decode_default`; toggle options via builders.
- CLI: `cargo install toon-format`; run `toon data.json` (encode) or `toon data.toon` (decode); add flags for folding, path expansion, stats.
- Spec checks: see `references/SPEC.md` (v3.0 working draft, 2025-11-24) for syntax and validation.

## Library usage (succinct)
- Default round-trip: `encode_default<T>(&value)` and `decode_default<T>(&str)` for any `Serialize`/`Deserialize`.
- Encoding options: `EncodeOptions::new().with_delimiter(Comma|Tab|Pipe).with_indent(Indent::Spaces(n)).with_key_folding(KeyFoldingMode::Safe).with_flatten_depth(n)`.
- Decoding options: `DecodeOptions::new().with_strict(false).with_coerce_types(false).with_expand_paths(PathExpansionMode::Safe)`.
- Errors surface `ToonError` (parse line/col, length/type mismatch, invalid structure, serialization/deserialization).
- Tests: `cargo test` or `cargo test --test spec_fixtures` for spec fixtures.

## CLI usage (succinct)
- Auto mode by extension: `toon file.json` -> TOON, `toon file.toon` -> JSON.
- Force mode: `toon -e input.txt` or `toon -d output.toon`.
- Common flags: `--delimiter tab|pipe`, `--indent 4`, `--fold-keys [--flatten-depth N]`, `--stats`, `--json-indent N`, `--no-strict`, `--no-coerce`, `--expand-paths`.
- Interactive: `toon --interactive` for live conversions plus stats and diff.

## Spec and validation
- Spec head is v3.0 (working draft, 2025-11-24); crate markets v2.1 compliance. Confirm target version before asserting conformance.
- Strict mode expectations: array length must match header, delimiters consistent per scope, indentation is spaces-only, quote keys when non-identifiers, diagnostics listed in section 14 of the spec.
- Use `references/SPEC.md` table of contents to jump to relevant sections (headers section 6, arrays section 9, strict errors section 14, core profile section 19).

## References (load on demand)
- `references/toon-rust.md` - crate/CLI cheat sheet, options, error types, tests, version notes.
- `references/SPEC.md` - full TOON specification v3.0 working draft (2025-11-24).

## Tips
- Prefer strict defaults; relax with `with_strict(false)` only when ingesting non-conformant input.
- For token savings, enable key folding on the encoder and path expansion on the decoder to preserve structure.
- When bridging UI/LLM prompts, keep evidence strings under 50 characters and include filename plus page if required by the caller schema.
