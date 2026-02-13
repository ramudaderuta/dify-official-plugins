# EasyWork - Collaboration & Context Guide
**Last Updated:** 2026-02-07

Purpose: give contributors a crisp, up-to-date overview of the product, constraints, build/run steps, and where to find deeper docs. Keep this synced with the codebase; do not edit the “Recent Changes” section except to add new dated entries.

---
## Product at a Glance
- Desktop app (Tauri v2) that lets users upload knowledge-base documents and use AI to simplify verification/search workflows.
- Rust backend + React 19 frontend; local extraction with OCR and per-page snapshots, ≤100 MB per file.
- AI layer: Rust Rig agent in `src-tauri/src/services/docs_review_service.rs` and `docs_search_service.rs` with fixed providers (Claude for review, Dify for search).
- AI flows: specs review uses Claude; smart search uses Dify (providers fixed by business). Base URLs are read-only in UI and edited via config.yaml.
- Workspaces: JSON under `~/.easywork/workspaces/*.json`, includes knowledge dataset binding (`knowledge.datasetId`), document list (`knowledge.documents`), product type, and review results.
- Review output: Approved / Pending / Rejected with evidence required in `filename P<page>:` format (≤100 chars).

---
## What Matters Most
- Accuracy & traceability of document verification; human-in-the-loop (default Pending).
- Security: size/type allowlist, path sanitization, no secrets in repo, proxy support.
- Simplicity: single app, no microservices or cloud backends.
- UX consistency: sidebar shell, unified Checklist + Agentic Debug flows.

---
## Working Norms
- Prefer doing, not suggesting: make small, focused patches; keep comments minimal and useful.
- Stay surgical: match existing patterns; no large refactors unless requested.
- Tests: run the smallest meaningful set for behavior changes; skip only for docs/trivial edits (state it).
- Security: respect file size/type limits, path sanitization, and never commit secrets.

---
## Proxy Rules (Implementation)
- Always build HTTP clients via `proxy_service::apply_proxy(...)` to enforce PAC/Off behavior.
- PAC mode: use PAC result only; never fall back to system/environment proxies.
- If PAC returns DIRECT (or parsing fails), force `no_proxy()` direct connection.

---
## Runtime Flags
- (none)

---
## Build & Run

### Windows (Cross-compilation)
```powershell
pnpm install

# Dev (auto-loads xwin env)
pnpm dev

# Build desktop bundles (MSI/NSIS/EXE under src-tauri/target/release/bundle/)
pnpm build

# Cargo with xwin env already loaded
. ./scripts/xwin-env.ps1; cargo check && cargo test

# One-liner cargo with env
pwsh -NoProfile -ExecutionPolicy Bypass -Command "& { . ./scripts/xwin-env.ps1; cargo check; cargo test }"

# Offline NSIS/WiX (bad network)
pwsh -ExecutionPolicy Bypass -File scripts/WiX_nsis.ps1
```

### Linux (Native)
```bash
pnpm install

# Dev (no xwin needed)
pnpm dev:linux

# Build .deb bundle under src-tauri/target/release/bundle/
pnpm build:linux

# Cargo runs natively
cargo check && cargo test
```

### Test Notes
- Full `cargo test` includes vendor OCR tests from `src-ocr/vendor/rust-paddle-ocr`, which can fail due to OCR output diffs or vendor expectations.
- To avoid vendor coupling during review work, run: `cargo test -p easywork -p phase_tests`.

---
## Key Paths
- Backend: `src-tauri/src/commands/` (IPC), `services/docs_review_service.rs`, `services/dify_service.rs`, `services/dify_dataset_service.rs`, `dify/`.
- Frontend: `src-ui/src/views/ChecklistView.tsx`, `AgenticDebugView.tsx`, `ExtractionView.tsx`, `SettingsView.tsx`, `ModelManagementView.tsx`, `KnowledgeView.tsx`, `SearchView.tsx`.

---
## Business Flow & Data Flow
- Specs Review (Checklist/Agentic Debug):
  - UI → `src-tauri/src/commands/analysis_commands.rs`
  - TOON pack/unpack → `src-tauri/src/services/toon_service.rs`
  - Rig pipeline → `src-tauri/src/services/docs_review_service.rs`
  - Provider client → `src-tauri/src/services/ai_service.rs` → `src-tauri/src/services/claude_service.rs`
- Smart Search (Search view):
  - UI → `src-tauri/src/commands/search_commands.rs`
  - Retrieval → `src-tauri/src/services/docs_search_service.rs` → `src-tauri/src/services/dify_dataset_service.rs`
  - Chat response → `src-tauri/src/services/docs_search_service.rs` → `src-tauri/src/services/ai_service.rs` → `src-tauri/src/services/dify_service.rs`

---
## Rig Essentials
- Commands exposed: `generate_review_results_with_agentic_breakdown`, `build_review_results_request_document_text`, `get_review_results_system_prompt`, `validate_review_results_json`, `export_excel_review`, `import_excel_review`.
- Prompt: default in `DEFAULT_REVIEW_RESULTS_CHUNK_INSTRUCTIONS`; UI can override; JSON-only output enforced by tool-call wrapper.
- Validation: evidence prefix + length, confidence in [0,1], item no 1-110; `validate_review_results_json` checks this.
- Metrics: `timing` + `token_usage` returned to UI (rough estimates when provider usage absent).

---
## Delegation
- Use sub-agents only when the task is unclear/large; otherwise act directly.
- If delegating: include What/Why/Where/How and ensure `python ./context_restore.py` is run by the sub-agent before work.

---
## Recent Changes
- **2026-02-07**: Claude Messages migration landed (review path)
  - Review provider path migrated from OpenAI-compatible `chat/completions` to Claude Messages `/v1/messages`.
  - Backend service/config naming migrated: `openai_service` → `claude_service`, `OpenaiChatCompletions` → `ClaudeMessages`, `openai_service.rs` → `claude_service.rs`.
  - Health checks now validate Claude via `/v1/messages` (with Claude headers), while Dify health checks remain unchanged.
  - Frontend settings and i18n now use Claude terminology and `claude_service` keys.
  - Config compatibility retained for one transition cycle via aliases (`openai_service`, `openai_chat_completions`).
- **2026-02-04**: ClaudeCompat streaming compatibility + repair context
  - Streaming client now disables gzip/deflate/brotli and sends `Accept-Encoding: identity` to reduce decode errors.
  - Claude streaming parser accepts JSONL-like chunks without strict SSE `data:` prefix and logs content/tool_calls paths.
  - Retry repair prompt now includes a larger truncated copy of the previous response (head + tail) to repair cut-off JSON.
- **2026-02-04**: Streaming robustness + think filtering
  - Claude stream parsing now accepts non-SSE JSONL `event-stream` payloads.
  - Streaming failures no longer fall back to blocking; surface `stream_error` immediately.
  - `<think>` blocks are stripped by default in Claude responses; behavior is configurable per ProviderRequest (`allow_think`).
- **2026-02-04**: Fixed AI providers per business + config cleanup
  - Docs review (`docs_review_service`) now uses Claude only; docs search (`docs_search_service`) uses Dify only.
  - Removed provider selection from config/UI; health checks run for both providers.
  - Claude base URL/model/key are built-in; Dify uses a single built-in key; temperature removed from config.
- **2026-02-04**: Workspace JSON v2 refactor
  - Knowledge documents + dataset binding moved to top-level `knowledge`.
  - Only `schemaVersion: 2` is read; v1 is replaced with empty v2.
- **2026-02-03**: OCR submodule integration + settings cleanup
  - Backend: replaced in-tree OCR with `src-ocr` wrapper + `rust-paddle-ocr` submodule; removed `mnn-sys` build-dep.
  - Config/UI: removed `efficient_cropping`; added OCR backend (CPU/OpenCL), precision, and with-rects controls.
  - Logging: OCR detail logs now gated by log level (DEBUG detailed, INFO summary); env toggles removed.
- **2026-02-02**: Unified OCR render DPI + image DPI scaling
  - Config: `ocr.render_dpi` replaces `pdf_render_dpi` (alias kept); defaults to 300 DPI.
  - Backend: PDF render scale uses `render_dpi`; image OCR scales by metadata DPI (clamped 0.5x–4x).
  - Tests: OCR sample expectations updated for new DPI behavior.
c- **2026-01-30**: OCR models bundled + model management removed
  - Backend/UI: removed Model Management view, commands, and download logic.
  - Packaging: OCR models now bundled under `src-tauri/resources/models` and resolved at runtime.
  - Config: OCR settings live under `ocr` (no `conversion` alias).
  - Tests: real OCR tests use bundled models and `res/` samples.
- **2026-01-28**: Local/remote knowledge split
  - Local workspaces keep local extraction + keyword search; remote workspaces use Dify datasets for upload/retrieve.
  - Semantic RAG/FFI removed; keyword search retained for local.
- **2026-01-27**: Dify knowledge base migration
  - Backend: added Dify dataset commands/service, removed RAG/search services and related FFI/test scaffolding.
  - Frontend: Search/Knowledge views now use Dify dataset retrieval and workspace `specView.datasetId`.
  - Docs/skills: added Dify dataset testing guide/script and migration notes.
- **2026-01-20**: Docs search/review refactor + chat pipeline + Dify key split
  - Backend: renamed services (`rig_agent` -> `docs_review_service`, `search_service` -> `docs_search_service`, `chunking` -> `ai_service`); shared chunking + provider helpers in `ai_service`.
  - Backend: docs search chat supports direct answer for single chunk, chunk-extraction+aggregation for multi-chunk, and respects configured response mode.
  - Backend: Dify keys split by usage (search vs review) with unified resolver; health check uses same resolver.
  - Frontend: Search chat stream listener only enabled in streaming mode; API key input disabled for Dify providers.
- **2026-01-20**: RAG status + search UX + model validation speedups
  - Backend: RAG enable flag in config; warmup on startup/update; status check command; global embedder singleton; semantic results sorted by score; model validation switched to XXH3 with size metadata backfill.
  - Frontend: RAG status badge + check button in Settings; SearchView notice behavior + relevance percentage; AI/RAG controls use sliders; semantic-only search with keyword fallback when RAG disabled.
- **2026-01-19**: RAG config + lightweight fused ranking
  - Backend: removed reranker pipeline; added RRF fusion, per-doc cap, adjacent chunk penalty; RAG parameters configurable via AppConfig and cache strategy fingerprint.
  - Frontend: SettingsView adds RAG configuration card (Dev Mode) for chunking and ranking parameters.
- **2026-01-19**: Semantic search Phase 2 + inline highlights
  - Backend: added reranker integration (mandatory when models available), Unicode/CJK tokenization, query+rerank LRU caches, and improved snippet/highlight selection.
  - Frontend: snippet/excerpt now render keyword highlights with `<mark>` and prioritize full-query matches.
- **2026-01-18**: Model download robustness + validation UX
  - Backend: added parallel chunked downloads (max 8), sequential resume, redirect-aware Range handling, and in-memory validation caching to avoid repeat SHA checks per run.
  - Frontend: Model Management now shows “验证中” during auto-validation and disables action buttons until validation completes.
  - Config: RAG model download sources switched to ModelScope (MNN) with updated checksums.
- **2026-01-16**: Model management + RAG download plumbing
  - Backend: added model commands, RAG service, and a unified model manager; refactored OCR manager usage and related service wiring.
  - Frontend: expanded Model Management view; added RAG model specs, model types, and i18n strings for download/management.
  - Tooling: added Codex skills for CDN download and git worktrees; refreshed code-architect skill guidance.
- **2026-01-15**: Smart Search backend wiring + semantic plan
  - SearchView now shares one UI with a Semantic/Keyword toggle; falls back to keyword when semantic models are unavailable; Chat mode currently shows “not implemented”.
  - Backend adds `semantic_search_workspace_documents` (fallback to keyword) and extends SearchResult models.
- **2026-01-15**: Unified provider pipeline + service split
  - Added shared provider trait and ReAct tool-call pipeline for Claude Messages + Dify Chat.
  - Removed Claude Response + Dify Workflow provider options in Settings/backend.
  - Moved Claude and Dify client implementations into `services/claude_service.rs` and `services/dify_service.rs`.
- **2026-01-09**: Smart Search UI prototype
  - Added Search view with chat + retrieval modes, inline result detail expansion, and auto-growing input.
  - Workspace Hub now includes a Search entry; navigation wiring added for the new view.
  - Added PandaWiki-style send icon and i18n strings for Search/检索/検索.
  - Documented UI + integration TODOs in `docs/memories/ui-design.md`.
- **2026-01-08**: Workspace hub + navigation refactor
  - Sidebar now has fixed actions, persistent workspace list, and a new Workspace Hub entry flow (Extraction/Spec).
  - Extraction/Checklist require preselected workspace; hub handles selection and entry paths.
  - Extraction header aligned with Checklist, adds Export JSON + Rename workspace; document modal supports per-page editing.
  - UI cleanup: removed unused CSS/i18n keys, simplified workspace hub list behavior.
- **2025-12-24**: Chunked analysis default pipeline
  - Default review flow now runs chunked analysis + aggregation to avoid timeouts.
  - Added chunking configuration defaults/validation and prompt modes for chunk + aggregation.
- **2025-12-23**: Dify/Claude provider UX + health checks
  - Settings now disables the Model selector when a Dify provider is chosen.    
  - Health check uses Dify `/parameters` for Dify providers and `/models` for Claude providers.
- **2025-12-23**: Dify provider integration
  - Added Dify official API adapter (`src-tauri/src/dify/` + `services/dify_service.rs`) with blocking + streaming support.
  - Analysis provider switch exposed in Settings (Claude chat/response, Dify chat/workflow).
  - Dify requests now honor proxy configuration and keep stable conversation IDs per session.
- **2025-12-21**: Frontend structured logging coverage
  - Added `uiLogger` helper for `[ui.<scope>] <event>` structured console messages and unified formatting before bridging to backend.
  - Lifecycle (main/App), Settings, Model Management, Checklist views now log via scoped logger; console→backend bridge formats arguments consistently.
- **2025-12-20**: Logging overhaul (tracing + frontend bridge)
  - Backend switched from env_logger to `tracing` with stdout + `~/.easywork/easywork.log` tee, runtime level reload, and size cap (Settings: System → 日志级别/大小；default 3 MB, format `[MM-DDT HH:MM:SS.mmm]`).
  - Added spans/debug/trace across document conversion, Rig agent, OCR model management, workspace normalization, health checks; third-party `log` bridged via `LogTracer`.
  - Frontend `console` is bridged to the same Tauri logging channel; key UI flows emit structured tags (e.g., `[ui.lifecycle]`, `[ui.settings]`).
- **2025-12-20**: Text-based paging + extractor refactor
  - TXT/MD/CSV/JSON now paginate by weight (CJK=1, ASCII=0.25) with newline-preferred breaks (≈1000 CJK per page); Excel paged per sheet; PPTX paged per slide.
  - DOCX extractor now outputs low-fidelity tables (tab-separated) and `[Image]` placeholders; Word pagination uses embedded Noto Sans CJK font via temp PDF + pdfium.
  - Moved pdf processor and shared utils under `extractor/`; added shared mm/pt conversion and CJK font loader; added bundled `resources/fonts/NotoSansCJKsc-Regular.otf`.
- **2025-12-20**: Word pagination via DOCX→PDF→pdfium
  - Word uploads now convert parsed DOCX text into a temporary text-only PDF (Helvetica, wrapped) and reuse pdfium per-page extraction for accurate page splits.
  - Uses lopdf for PDF generation; cleans up temp files after extraction.
- **2025-12-19**: AgenticDebugView Enhancements - Performance Metrics and TOON Editing
  - **NEW FEATURE**: Token usage tracking and cost estimation display
    - Backend: Added `TimingBreakdown` (total_ms, http_request_ms, parsing_ms, prompt_build_ms) and `TokenUsage` (prompt_tokens, completion_tokens, total_tokens) structs to `ReviewResultsResponse`
    - Frontend: Added metrics panel with timing breakdown, token usage, and cost estimation cards
    - Token estimation uses text length / 4 for both prompt and completion
  - **NEW FEATURE**: Prompt quality metrics panel
    - Calculates average confidence, status distribution (Approved/Pending/Rejected counts/percentages)
    - Color-coded display: green (success), yellow (warning), red (destructive)
  - **NEW FEATURE**: Editable TOON request support
    - Added "Edit TOON" button (Edit3 icon) to toolbar
    - Modal dialog for editing the TOON request text before sending to AI
    - Added "Reset" button (RotateCcw icon) to clear edited text and return to auto-build mode
    - Modified `runAgentic()` to use edited TOON text if available, otherwise auto-build from workspace
    - Backend already supported custom `document_text` parameter - no backend changes needed
  - **NEW FEATURE**: JSON Schema validation for AI output
    - Backend: Added `validate_review_results_json` Tauri command with comprehensive validation
    - Validates against `ReviewResultsDocument` schema using serde deserialization
    - Additional checks: confidence ∈ [0,1], evidence ≤50 chars, evidence format "filename p<page>:", item no ∈ [1-110]
    - Frontend: Added "Validate" button in output panel with visual feedback
    - Validation banner shows success (green) or errors (red) with detailed error paths
    - Spin animation during validation, monospace highlighting for error paths
  - UI improvements:
    - Added icons: Clock, Zap, DollarSign, BarChart3, Edit3, Save, X, CheckCircle2, XCircle
    - Responsive grid layout for metrics cards
    - Modal overlay with animations (fadeIn, slideInUp)
    - Character count display in TOON editor
    - Validation banner with error list and highlighted paths

- **2025-12-19**: Workspace documents now paged (no merged `text`)
  - Workspace schema uses `totalPages` + `pages[]` for all formats; Rig prompt tightened: evidence ≤50 chars and must include filename+page; frontend/viewers adjusted accordingly.
  - TODO: add Word pagination by DOCX→PDF conversion then pdfium per-page extraction.
- **2025-12-17**: Rig Migration (Rust)
  - Replaced the TypeScript `src-agentic/` layer with a native Rig (`rig-core`) agent in Rust.
  - Added `src-tauri/src/services/rig_agent.rs` with structured JSON output and system prompt override support.
  - Updated Tauri command `generate_review_results_with_agentic_breakdown` to call the Rig agent directly (no Node.js subprocess).
  - Settings now surface Rig parameters: `base_url`, `model`, `api_key`, `timeout_ms`, `temperature`, `max_tokens`.
  - Added environment variable proxy fallback support for Rig HTTP client. Priority: UI proxy config > env vars (`HTTP[S]_PROXY`) > direct connection. Added diagnostic logging for proxy configuration.

- **2025-12-17**: TOON + Workspace Normalization Backend Migration
  - Added Rust TOON support via `toon-format = "0.4.0"`; backend now owns TOON encode/decode for agent requests.
  - Added backend command `build_review_results_request_document_text` to build the exact `documentText` (TOON v2) sent to the Rig agent, including productType + requirement-matrix filtering.
  - Consolidated TOON resource access under `get_toon_resource_json(name)` (e.g. `checklist-template`, `requirement-matrix`) to remove TS-side TOON decoding.
  - Moved workspace JSON normalization to backend commands: `normalize_workspace_json_text` (in-memory) and `read_and_normalize_workspace_json` (from file path). (Implementation now lives in `services/workspace_service.rs`.)
  - Removed frontend dependency on `@toon-format/toon`; Agentic Debug/Checklist now call backend commands for request construction and workspace normalization.
