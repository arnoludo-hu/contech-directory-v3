# ConTech Conversational Search API — implementation baseline

## What is implemented
- FastAPI `/api/v1/search` and `/health`.
- Pydantic validated query plans: AND across groups, OR inside groups, NOT via negative operators.
- SQLAlchemy parameterised PostgreSQL queries against the supplied ConTech v2 schema.
- Verified PSG, reseller, support and local entity filtering; unknown does not qualify.
- Deterministic full-set filtering and distinct-company counts, with pagination.
- Sentence-transformers semantic ranking over eligible results, using 384-dimensional MiniLM.
- Session context, add/remove/replace filter operations, result-position comparison.
- Source URLs limited to verified, public claim evidence.
- LLM extraction via OpenAI when enabled, otherwise conservative local parser for demonstration.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
# Set DATABASE_URL and optionally OPENAI_API_KEY / ENABLE_LLM=true
# export variables from .env using your preferred environment manager
docker compose up -d
psql postgresql://contech:contech@localhost:5432/contech -f sql/001_schema.sql
uvicorn app.main:app --reload
pytest -q
```
Example request:
```bash
curl -X POST http://localhost:8000/api/v1/search -H 'Content-Type: application/json' -d '{"message":"Find computer vision solutions for construction progress monitoring","page":1,"page_size":10}'
```
Reuse the returned `session_id` for follow-up messages.

## Required data loading
The database starts empty. Import approved records from the previous architecture package into `contech.*` tables, respecting foreign keys. **Do not import synthetic examples into public production.** Only `published` companies and solutions with verified material AI eligibility are searchable.

## Critical caveats before production
1. In-memory sessions are single-process and have no expiry. Replace with Redis/DB persistence, TTL, optimistic locking, and retention controls.
2. LLM JSON extraction uses schema validation but no adjudication of ambiguous filter semantics; human-labelled regression testing is required. Fallback parser is intentionally limited and may require confirmation.
3. Affordability is **not** in the v2 database; pricing preferences are explicitly marked unsupported, not invented. Add verified pricing bands and evidence before claiming affordability rankings.
4. Semantic ranking encodes all eligible rows at query time; for scale, store and query pgvector embeddings with filtered candidate retrieval, plus exhaustive-recall tests. `solution_search_documents.embedding` is available for that migration.
5. Current no-match response explains that constraints are strict but does not yet compute per-filter exclusion counts or generate a separately labelled relaxed-alternative list. Implement filter diagnostics and user-approved relaxation before public release.
6. Public API needs rate limiting, authentication for administration, observability, prompt-injection tests, privacy controls, and a security review.
7. `compare` uses previously returned ranking positions; stable snapshots should be persisted for distributed deployment.
8. PSG verification relies on the underlying v2 view. Operational policy should require current authoritative listing evidence and a freshness SLA; a historical verification alone is insufficient.
9. Verified company-level reseller relationships are assumed applicable to all company solutions unless `solution_id` is specified. Tighten to solution-scoped coverage where partner agreements are product-specific.
10. Source evidence is returned only for verified solution-level claims. Expand to verified company/PSG/presence claims with explicit provenance joins.

## API contract
POST `/api/v1/search`: `{message:string, session_id?:string, page?:integer, page_size?:integer}`.
Returns `session_id`, `intent`, `applied_filters`, `preferences`, `total_solutions`, `total_companies`, `page`, `page_size`, `matches`, `clarification`, `message`. `matches` contain solution/company IDs, names, score, reasons, limitations, source URLs.

## Architecture
`interpreter.py` -> `models.py` -> `state.py` -> `repository.py` -> `ranking.py` -> `main.py`.

This is an executable **engineering starter**, not a security-hardened public production deployment.
