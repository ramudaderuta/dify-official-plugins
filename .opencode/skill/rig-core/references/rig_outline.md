# Rig Docs Outline (https://docs.rig.rs/docs)

- **Overview**: landing page linking to all sections.
- **Quickstart**: `quickstart/getting_started`, `quickstart/embeddings`, `quickstart/tools`.
- **Why Rig?**: benefits, comparison to direct SDK use.
- **Architecture**: design principles, agent pipeline, abstractions.
- **Concepts**: agents, prompts, providers, memory, tools/function-calling.
- **Integrations**:
  - LLM providers (OpenAI + others listed on site).
  - Vector stores (Postgres/pgvector, Supabase, SQLite, Redis, Pinecone, Chroma, Qdrant, Milvus, Neo4j, SurrealDB).
  - Third-party plugins under `integrations/plugins/` (Discord, Twitter, etc.).
- **Extensions**: CLI chatbot and other utilities.
- **How to Contribute**: contribution flow and issue links.
- **API Reference**: points to `https://docs.rs/rig-core` for rustdoc.

Use these links when a deeper page is needed; keep only the relevant reference file in context to manage tokens. Each page on docs has a "Edit on GitHub" link (`0xPlaygrounds/rig-docs`) if the latest source is required.
