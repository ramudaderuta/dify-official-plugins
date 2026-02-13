## Style Guide

Applies to EasyWork (Rust backend + React/TS frontend). Use this as a default, but prefer local patterns in the file you are editing.

## General
- Keep functions focused; split only when it improves reuse or testability.
- Prefer early returns; avoid deep nesting.
- Avoid unnecessary destructuring when it hides context (`obj.a` can be clearer than `{ a }` in long flows).
- Prefer `const` in TS/JS; use `let` only when reassignment is required.
- Naming: prefer short, concrete names. Use multi-word names when they add clarity or disambiguate domain meaning.

## TypeScript / React
- Avoid `any`; use `unknown` + narrow, or proper types.
- Error handling: avoid blanket `try/catch`; use typed results and narrow exceptions to boundaries (IO, network, parsing).
- Control flow: avoid `else` blocks when a return can simplify flow.
- Destructure React props when it improves readability; otherwise prefer `props.foo`.
- Prefer built-in Web/Node APIs already used in the repo; do not add Bun-specific APIs.
- Hooks: keep dependencies complete; avoid suppressing lint unless there's a clear reason and a comment.
- State: prefer derived values over duplicating state; lift state only when necessary.
- Effects: avoid mixed concerns in a single `useEffect`; split by responsibility if it grows.
- i18n: use existing translation helpers (`useTranslation`) instead of hard-coded UI strings.
- Logging: use existing UI logger helpers instead of raw `console.log` in app flows.

Example: prefer const + early return
```ts
function resolveMode(flag: boolean) {
  if (flag) return "on"
  return "off"
}
```

Avoid: let + else
```ts
function resolveMode(flag: boolean) {
  let mode = "off"
  if (flag) mode = "on"
  else mode = "off"
  return mode
}
```

## Rust
- Prefer explicit error types (`thiserror` or enums) over `Box<dyn Error>` in app code.
- Use `Result<T, E>` and propagate with `?`; handle errors at boundaries (commands, IO, HTTP).
- Avoid large functions; keep services small and composable.
- Prefer `&str` over `String` for read-only inputs.
- Logging: keep structured, include key context, avoid logging secrets.
- Tauri commands: validate inputs at the boundary and keep command bodies thin; delegate to services.
- HTTP/proxy: always build clients through the proxy service helper; do not bypass proxy rules.
- Data flow: prefer explicit structs for IPC payloads and avoid loose `serde_json::Value` when a schema exists.
- File IO: sanitize paths and enforce size/type checks at the boundary.

## Exceptions
Rules are defaults, not absolutes. When violating a rule:
- Add a brief comment or keep the code obviously clear.
- Match existing file conventions to reduce churn.
