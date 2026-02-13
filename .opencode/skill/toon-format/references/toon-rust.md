# toon-format Rust crate quick reference

## Crate
- Install lib: `cargo add toon-format`
- Install CLI: `cargo install toon-format`
- Docs: https://docs.rs/toon-format

## Core functions
- `encode<T: Serialize>(&value, &EncodeOptions)` → `Result<String, ToonError>`
- `encode_default<T>(&value)` → default opts
- `decode<T: Deserialize>(&input, &DecodeOptions)` → `Result<T, ToonError>`
- `decode_default<T>(&input)` → default opts

## EncodeOptions (builder style)
- `with_delimiter(Comma|Tab|Pipe)` default Comma
- `with_indent(Indent::Spaces(n))` default 2
- `with_spaces(n)` shorthand for indent
- `with_key_folding(KeyFoldingMode::{Off,Safe,Aggressive})` (v1.5 feature)
- `with_flatten_depth(n)` limit folding depth

## DecodeOptions
- `with_strict(bool)` default true
- `with_coerce_types(bool)` default true ("true"→bool etc.)
- `with_expand_paths(PathExpansionMode::{Off,Safe,Aggressive})` (v1.5 feature)

## Common patterns
```rust
use serde::{Serialize, Deserialize};
use toon_format::{encode_default, decode_default};

#[derive(Serialize, Deserialize, PartialEq)]
struct User { name: String, age: u32 }

let toon = encode_default(&User { name: "Alice".into(), age: 30 })?;
let user: User = decode_default(&toon)?;
```

Strict decode with relaxed rules:
```rust
use toon_format::{decode, DecodeOptions};
let opts = DecodeOptions::new().with_strict(false).with_coerce_types(false);
let json: serde_json::Value = decode("active: true", &opts)?;
```

Key folding round-trip:
```rust
use toon_format::{encode, decode, EncodeOptions, DecodeOptions, KeyFoldingMode, PathExpansionMode};
let enc = EncodeOptions::new().with_key_folding(KeyFoldingMode::Safe);
let dec = DecodeOptions::new().with_expand_paths(PathExpansionMode::Safe);
let toon = encode(&serde_json::json!({"a":{"b":{"c":1}}}), &enc)?;
let v: serde_json::Value = decode(&toon, &dec)?;
```

## CLI cheatsheet (`toon`)
- Detect mode by extension: `toon data.json` (encode), `toon data.toon` (decode)
- Force: `toon -e input.txt`, `toon -d input.toon`
- Pipe: `cat data.json | toon --fold-keys --stats`
- Options: `--delimiter tab|pipe`, `--indent 4`, `--fold-keys [--flatten-depth N]`, `--stats`, `--json-indent N`, `--no-strict`, `--no-coerce`, `--expand-paths`
- Interactive TUI: `toon --interactive` (live stats + diff)

## Error handling
`ToonError` variants include ParseError (line/col), LengthMismatch, TypeMismatch, InvalidStructure, SerializationError, DeserializationError.

## Tests
- Run all: `cargo test`
- Spec fixtures: `cargo test --test spec_fixtures`