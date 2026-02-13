# TOON Specification Cheat Sheet (condensed)

Version notes: v3.0 working draft (2025-11-24). 

## Data model
- Mirrors JSON types: null, bool, number (IEEE 754 JSON number), string, array, object.
- Root may be object or array.

## Core syntax
- Line-oriented, indentation defines structure (spaces only).
- Objects: `key: value` or `key:` then indented children.
- Arrays: header declares length (and optional field list). Items follow on new lines.
- Strings unquoted unless needed (spaces, delimiters, colon, quotes, tabs, control chars, leading zeros, etc.). Quote with double quotes; escape `\"` and `\\`.
- Keys unquoted if identifier `[A-Za-z0-9_]+`; otherwise quote.

## Arrays
- Header: `name[len]: item1,item2` (scalar array) or `name[len]{fields}:` (tabular objects).
- Active delimiter scoped per array: comma default, may switch to tab (`[len\t]`) or pipe (`[len|]`).
- Row per line; object rows follow field order.
- Length is authoritative in strict mode; mismatch is error.
- Nested objects inside rows allowed: `name[len]{id,meta}: 1,{a:1}` or new indented block after header.

## Objects inside arrays (tabular)
- `rows[len]{f1,f2,f3}:` then rows with delimiter.
- Missing field → empty value; extra field → error (strict).

## Delimiters
- Only comma, tab, pipe. Scoped to current array header.
- No mixed delimiters within the same array.

## Indentation
- Spaces only; count significant. Commonly 2 spaces but not mandated.
- Sibling keys align; deeper levels increase indent.

## Numbers
- Canonical JSON number format: optional minus, integer part (no leading zeros unless zero), optional fractional, optional exponent.

## Booleans / null
- Literals: `true`, `false`, `null`.

## Options (v1.5+)
- Key folding (encoder): collapse single-key chains into dotted path when safe.
- Path expansion (decoder): expand dotted keys back into nested objects.
- Strict mode toggle; type coercion toggle.

## Strict mode diagnostics (common)
- Length mismatch for arrays.
- Invalid delimiter or mixed delimiters.
- Bad indentation (tabs, inconsistent indent).
- Non-identifier key left unquoted.
- Trailing delimiter or missing values in a row.
- Duplicate keys in same object.
- Type mismatch against inferred structure (e.g., row field count).
- Unescaped control characters or bad escapes.
- Invalid number format or leading zeros.

## Core profile (minimal, for constrained agents)
- Objects, arrays, strings, numbers, bool, null.
- Comma delimiter only.
- No key folding/path expansion.
- Spaces for indentation; strict length matching.

## Header grammar (simplified)
- `name[len]:` scalar array
- `name[len]{fields}:` tabular objects
- `name:` object
- Optional delimiter marker: `[len\t]` or `[len|]`

## Quick examples

Object:
```
user:
  name: Alice
  active: true
```

Scalar array:
```
tags[3]: red,green,blue
```

Tabular array:
```
users[2]{id,name}:
  1,Alice
  2,Bob
```

Nested with folding (encoder option):
```
data.meta.count: 5
```
Expanded (decoder option):
```
data:
  meta:
    count: 5
```

## Validation tips
- Prefer strict mode for ingestion; relax only when caller demands.
- Check length vs rows; forbid mixed delimiters; enforce quoted non-identifier keys.
- Keep indentation consistent; reject tabs for indent.

## Interop notes
- Round-tripping: enable key folding on encode + path expansion on decode to preserve structure.
- When embedding in prompts, keep rows short; prefer tabular arrays for LLM token efficiency.

## References
- Full spec: https://github.com/toon-format/spec (SPEC.md, v3.0 draft)
- Rust crate docs: https://docs.rs/toon-format
