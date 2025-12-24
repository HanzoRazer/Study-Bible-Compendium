Below is a **ready-to-copy GitHub Issue List**, grouped by **FTS**, **Pagination**, and **Performance Metrics**, written in a style suitable for immediate repo ingestion.

Each issue includes:

* **Title**
* **Labels**
* **Scope**
* **Acceptance Criteria**
* **Notes / Dependencies**

You can paste these directly into GitHub Issues or convert them into a project board.

---

# 📌 Milestone: Production Readiness v1.1

---

## 🔎 FTS5 (Full-Text Search) Issues

---

### **FTS-1: Detect and Validate SQLite FTS5 Support**

**Labels:** `fts`, `core`, `blocking`
**Scope:** Startup / DB initialization

**Description:**
Detect whether the SQLite build supports FTS5 and fail gracefully if not.

**Acceptance Criteria:**

* On startup or `status`, system reports FTS5 availability
* Clear error message if FTS5 is missing
* No stack traces exposed to user

**Notes:**
Required before any FTS work proceeds.

---

### **FTS-2: Define FTS Index Schema**

**Labels:** `fts`, `schema`
**Scope:** Database schema

**Description:**
Define which fields are indexed (e.g., `verses.text`, later `notes.body`) and create FTS5 virtual table(s).

**Acceptance Criteria:**

* FTS schema documented
* Schema version tracked
* FTS tables created idempotently

---

### **FTS-3: Implement init-fts Command**

**Labels:** `fts`, `cli`
**Scope:** CLI

**Description:**
Add `init-fts` command to build FTS index from existing data.

**Acceptance Criteria:**

* Command builds index without modifying verse data
* Progress output for large DBs
* Safe to re-run

---

### **FTS-4: Automatic FTS Updates on Import**

**Labels:** `fts`, `import`, `performance`
**Scope:** Import pipeline

**Description:**
Ensure imports keep FTS index in sync (trigger or post-import rebuild).

**Acceptance Criteria:**

* FTS index updated after import
* No partial or stale FTS state
* Behavior documented

**Notes:**
Batch rebuild acceptable for v1.1.

---

### **FTS-5: Implement rebuild-fts Command**

**Labels:** `fts`, `maintenance`
**Scope:** CLI maintenance

**Description:**
Allow safe rebuilding of FTS index.

**Acceptance Criteria:**

* Warns about runtime cost
* Logs rebuild start/end
* Clears and rebuilds index deterministically

---

### **FTS-6: FTS Query Syntax Handling**

**Labels:** `fts`, `ux`
**Scope:** Search UX

**Description:**
Gracefully handle invalid FTS syntax and document supported query patterns.

**Acceptance Criteria:**

* Invalid syntax produces friendly error
* Phrase search supported
* AND/OR behavior documented

---

### **FTS-7: Relevance Ordering Verification**

**Labels:** `fts`, `quality`
**Scope:** Search results

**Description:**
Verify deterministic relevance ordering (BM25 or equivalent).

**Acceptance Criteria:**

* Same query yields same ordering
* Ordering documented
* Stable sort fallback applied

---

## 📄 Pagination Issues

---

### **PAGE-1: Define Global Pagination Contract**

**Labels:** `pagination`, `design`
**Scope:** CLI API contract

**Description:**
Standardize pagination flags across commands.

**Acceptance Criteria:**

* Decide on `--limit` / `--offset` OR `--page` / `--page-size`
* Defaults defined
* Contract documented

---

### **PAGE-2: Add Pagination to search Command**

**Labels:** `pagination`, `fts`, `blocking`
**Scope:** Search CLI

**Description:**
Implement pagination for search results.

**Acceptance Criteria:**

* Paginated results with stable ordering
* Total hit count reported when feasible
* Page metadata printed or returned in JSON

---

### **PAGE-3: Stable Sorting for Paginated Queries**

**Labels:** `pagination`, `bug-risk`
**Scope:** Query logic

**Description:**
Ensure paginated results do not skip or duplicate rows.

**Acceptance Criteria:**

* Explicit ORDER BY clause applied
* Deterministic tie-breakers used
* Verified across multiple pages

---

### **PAGE-4: Pagination for List Commands**

**Labels:** `pagination`, `ux`
**Scope:** Non-search listings

**Description:**
Paginate commands like `list-translations`, `list-notes` (if present).

**Acceptance Criteria:**

* Same pagination flags work everywhere
* Consistent output format

---

### **PAGE-5: Batch Handling for compare**

**Labels:** `pagination`, `performance`
**Scope:** Parallel comparison

**Description:**
Support batching when comparing many translations or verses.

**Acceptance Criteria:**

* Large compares do not exhaust memory
* Optional batching flags documented

---

## ⏱️ Performance & Metrics Issues

---

### **PERF-1: Add Timing Instrumentation**

**Labels:** `performance`, `observability`, `blocking`
**Scope:** Core command execution

**Description:**
Measure execution time for major CLI commands.

**Acceptance Criteria:**

* Start/end timestamps recorded
* Duration logged
* Optional `--timing` flag prints breakdown

---

### **PERF-2: Implement bench Command**

**Labels:** `performance`, `cli`
**Scope:** Benchmarking

**Description:**
Add `bench` command to run standardized performance tests.

**Acceptance Criteria:**

* Cold vs warm timing
* Outputs median / p95 / max
* Reports DB size and verse counts

---

### **PERF-3: Define Performance Budgets**

**Labels:** `performance`, `docs`
**Scope:** Documentation

**Description:**
Document expected performance targets for key operations.

**Acceptance Criteria:**

* Budgets defined per operation
* Measured values recorded
* Deviations documented

---

### **PERF-4: Slow Query Detection**

**Labels:** `performance`, `logging`
**Scope:** Query execution

**Description:**
Warn when queries exceed a threshold.

**Acceptance Criteria:**

* Threshold configurable
* Slow queries logged with context
* No performance regression introduced

---

### **PERF-5: Query Plan Inspection Support**

**Labels:** `performance`, `dev-only`
**Scope:** Developer tooling

**Description:**
Provide `--explain` option for performance debugging.

**Acceptance Criteria:**

* Outputs SQLite query plan
* Clearly marked dev-only
* Does not affect normal execution

---

### **PERF-6: DB Optimization & Integrity Tools**

**Labels:** `maintenance`, `performance`
**Scope:** DB health

**Description:**
Add `db-optimize` and `db-check` commands.

**Acceptance Criteria:**

* Runs ANALYZE / integrity checks
* FTS integrity verified if possible
* Outputs clear pass/fail results

---

## 🎯 Milestone Completion Rule

**Production Readiness v1.1 is complete when:**

* All **FTS-1 → FTS-7** are closed
* All **PAGE-1 → PAGE-5** are closed
* All **PERF-1 → PERF-6** are closed
* Bench results are committed to `/docs/performance.md`

---

### Next Options

If you want, I can:

* Convert this into **GitHub Issue JSON** (importable)
* Create a **GitHub Project board layout**
* Generate a **PR checklist** that enforces v1.1 gates automatically

Just tell me which artifact you want next.
