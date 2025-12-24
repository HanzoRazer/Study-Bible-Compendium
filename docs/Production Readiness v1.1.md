## Production Readiness v1.1

**Scope:** Everything in **PRC v1.0** plus **FTS5 search**, **pagination**, and **measured performance**.
**Target:** “Large library” readiness (multiple translations + notes/commentary scale) with predictable latency.

---

# 1) Full-Text Search (FTS5) Readiness

### 1.1 FTS5 Availability & Setup

* [ ] Startup check confirms SQLite has **FTS5 enabled**
* [ ] `init-fts` command builds FTS indexes (idempotent)
* [ ] Rebuild command exists: `rebuild-fts` (safe + logged)
* [ ] FTS schema version tracked (so future changes don’t break old DBs)

### 1.2 Indexed Content Definition (Contract)

* [ ] Document what is indexed (e.g., `verses.text`, optional `notes.body`)
* [ ] Document tokenization strategy (unicode, diacritics behavior)
* [ ] Document what is **not** indexed (e.g., metadata-only fields)

### 1.3 Query Semantics

* [ ] Support phrase search (`"in the beginning"`)
* [ ] Support AND/OR/NOT (or clearly document what’s supported)
* [ ] Graceful handling of invalid FTS syntax (no stack traces)
* [ ] Relevance ordering is deterministic and documented (BM25 default OK)

### 1.4 Consistency & Freshness

* [ ] Imports update FTS index automatically (trigger or post-import step)
* [ ] If triggers are used: confirmed safe under bulk import (no runaway time)
* [ ] If batch rebuild used: DB records “FTS is stale” until rebuilt

---

# 2) Pagination Readiness (Search & Listing)

### 2.1 Pagination Contract (Uniform Across Commands)

* [ ] All list-like outputs support:

  * `--limit` (default set)
  * `--offset` (or `--page` + `--page-size`)
  * `--sort` where applicable
* [ ] Responses include metadata:

  * total hits (when feasible)
  * current offset/page
  * returned count

### 2.2 Pagination Coverage

* [ ] `search` paginated
* [ ] `list-translations` paginated (optional but consistent)
* [ ] `notes` / midrash listing paginated (if implemented)
* [ ] `compare` supports batching when comparing many translations

### 2.3 Stable Ordering Guarantee

* [ ] Paginated results have stable ordering (no duplicates across pages)
* [ ] Sorting keys are explicit (e.g., `(rank, book, chapter, verse, verse_id)`)

---

# 3) Performance Metrics & SLAs (Measured, Not Assumed)

### 3.1 Built-In Benchmark Harness

* [ ] `bench` command exists to run standardized tests:

  * cold start
  * warm start
  * FTS search
  * passage retrieval
  * context window retrieval
  * parallel compare (N translations)
* [ ] Bench outputs:

  * median / p95 / max times
  * DB size
  * verse counts / translation counts
  * machine info summary (CPU/RAM, OS)

### 3.2 Performance Budgets (Targets)

Define targets for two profiles:

**Profile A (Typical Desktop):** midrange Windows laptop, SSD
**Profile B (Low-End):** older laptop / slower SSD

Minimum acceptable budgets (adjustable, but must exist):

* [ ] `status` < 250ms warm
* [ ] `passage "John 3:16-18"` < 150ms warm
* [ ] `context "John 3:16" --window 4` < 200ms warm
* [ ] FTS search (common term) < 300ms warm
* [ ] FTS search (rare term) < 300ms warm
* [ ] Compare 3 translations single verse < 250ms warm
* [ ] Search pagination page fetch < 150ms warm (after first page)

*(If you can’t hit these on low-end, you still ship—just document the real numbers and set realistic budgets.)*

### 3.3 Instrumentation

* [ ] Each command logs:

  * start/end timestamps
  * duration
  * key parameters (query length, limit, translation set)
* [ ] Optional `--timing` flag prints per-step timings (parse, query, render)

### 3.4 Query Plan Verification

* [ ] For performance-critical queries, provide `--explain` option (dev-only)
* [ ] Ensure indexes exist for non-FTS lookups (spine joins, verse_id joins)
* [ ] Slow query threshold logged (e.g., warn if > 500ms)

---

# 4) Search Result Quality & UX (Practical)

### 4.1 Snippets / Highlights

* [ ] Search results show snippet with matched term highlighted (optional)
* [ ] Snippet generation is bounded (max chars) and fast

### 4.2 Result Navigation

* [ ] Search results include canonical reference (Book Chapter:Verse)
* [ ] `search` result IDs can be piped to `passage` or `context`
* [ ] `--open` or `--format json` supported for automation

### 4.3 Output Formats

* [ ] `--format text|json|csv` supported for key commands (at least search)
* [ ] JSON output schema documented and stable

---

# 5) Database Growth & Maintenance

### 5.1 Vacuum / Optimize

* [ ] `db-optimize` command runs:

  * `VACUUM` (optional, warned)
  * `ANALYZE`
  * FTS optimize (if used)
* [ ] Commands explain expected runtime and disk implications

### 5.2 Integrity Checks

* [ ] `db-check` runs:

  * PRAGMA integrity_check
  * spine integrity checks
  * FTS integrity checks (if supported)

---

# 6) Release Gates for v1.1

**v1.1 may be tagged only when:**

* [ ] PRC v1.0 gates remain satisfied
* [ ] FTS5 is implemented, documented, and validated on a “large-ish” DB
* [ ] Pagination is uniform and stable across all relevant commands
* [ ] Bench suite exists and produces repeatable metrics
* [ ] Performance budgets are either met OR explicitly updated with measured reality
* [ ] “Slow query” warnings do not appear in normal workloads

---

# 7) Suggested v1.1 Acceptance Test Pack (Quick, Repeatable)

Run these in order on a DB containing multiple translations:

* [ ] `status`
* [ ] `init-fts` (or confirm already built)
* [ ] `search "faith" --limit 25 --offset 0`
* [ ] `search "faith" --limit 25 --offset 25`
* [ ] `search "\"in the beginning\"" --limit 10`
* [ ] `passage "Genesis 1:1-5"`
* [ ] `context "John 3:16" --window 4`
* [ ] `compare "John 3:16" KJV BSB ASV`
* [ ] `bench --profile typical`
* [ ] `db-check`

---

If you want, I can turn this into:

1. a **docs file** +
2. a **GitHub issue list** (FTS tasks, pagination tasks, metrics tasks) +
3. a **PR template** that enforces “measured performance proof” for search-related changes.
