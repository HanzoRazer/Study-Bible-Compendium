#!/usr/bin/env python3
"""
PR Gates runner for Production Readiness v1.1

Reads a JSON policy (pr_checklist_v1_1.json) and enforces:
- Required PR labels (any-of)
- Required PR template checkboxes
- Gate rules based on labels + changed paths:
  - files_exist_any
  - tests_match_any (glob)
  - docs_contains
  - artifact_or_link_present (bench evidence)
- Emits GitHub Actions annotations and fails if any required checks fail.

Notes:
- This script intentionally does NOT implement the "milestone" rule that checks
  open issues in a milestone. GitHub PR objects don't have milestones; milestones
  are attached to issues. You can enforce that via a separate workflow or by
  parsing linked issues (future enhancement).
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


def gha_error(msg: str) -> None:
    print(f"::error::{msg}")


def gha_notice(msg: str) -> None:
    print(f"::notice::{msg}")


def die(msg: str, code: int = 1) -> None:
    gha_error(msg)
    raise SystemExit(code)


def load_json(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        die(f"Policy file not found: {path}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        die(f"Failed to parse policy JSON: {path} ({e})")
    return {}  # unreachable


def gh_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pr-gates-v1.1",
    }


def gh_get(url: str, token: str, params: Optional[Dict[str, Any]] = None) -> Any:
    r = requests.get(url, headers=gh_headers(token), params=params, timeout=30)
    if r.status_code >= 400:
        die(f"GitHub API GET failed {r.status_code}: {url} :: {r.text[:500]}")
    return r.json()


def fetch_pr(repo: str, pr_number: int, token: str) -> Dict[str, Any]:
    return gh_get(f"https://api.github.com/repos/{repo}/pulls/{pr_number}", token)


def fetch_pr_files(repo: str, pr_number: int, token: str) -> List[str]:
    files: List[str] = []
    page = 1
    while True:
        data = gh_get(
            f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files",
            token,
            params={"per_page": 100, "page": page},
        )
        if not data:
            break
        for item in data:
            # filename includes full path in repo
            files.append(item.get("filename", ""))
        if len(data) < 100:
            break
        page += 1
    return files


def file_exists_any(paths: List[str]) -> bool:
    return any(Path(p).exists() for p in paths)


def match_any_glob(patterns: List[str], candidates: List[str]) -> bool:
    for pat in patterns:
        for c in candidates:
            if fnmatch.fnmatch(c, pat):
                return True
    return False


def read_text_file(path: str) -> Optional[str]:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def pr_has_required_labels_any(pr_labels: List[str], required_any: List[str]) -> bool:
    pr_set = {x.lower() for x in pr_labels}
    return any(lbl.lower() in pr_set for lbl in required_any)


def extract_checked_checkboxes(pr_body: str) -> List[str]:
    """
    Return list of checkbox line text that are checked, e.g.
    "- [x] Acceptance criteria..." -> "Acceptance criteria..."
    """
    checked = []
    for line in pr_body.splitlines():
        m = re.match(r"^\s*-\s*\[x\]\s+(.*)\s*$", line, flags=re.IGNORECASE)
        if m:
            checked.append(m.group(1).strip())
    return checked


def checkbox_checked(pr_body: str, checkbox_text: str) -> bool:
    checked = extract_checked_checkboxes(pr_body)
    # allow "starts with" match to tolerate minor punctuation differences
    want = checkbox_text.strip().lower()
    for got in checked:
        g = got.strip().lower()
        if g == want or g.startswith(want) or want.startswith(g):
            return True
    return False


def changed_paths_any(changed_files: List[str], paths: List[str]) -> bool:
    """
    paths may contain globs like schema/** or sbc/search.py
    We'll treat any entry with glob chars as fnmatch.
    """
    for p in paths:
        if any(ch in p for ch in ["*", "?", "[", "]"]):
            for f in changed_files:
                if fnmatch.fnmatch(f, p):
                    return True
        else:
            if p in changed_files:
                return True
            # allow prefix style like "schema/**" handled above; if user gives "schema/"
            if p.endswith("/") and any(f.startswith(p) for f in changed_files):
                return True
    return False


def labels_any(pr_labels: List[str], required: List[str]) -> bool:
    pr_set = {x.lower() for x in pr_labels}
    return any(x.lower() in pr_set for x in required)


def ensure_requirements(
    require: Dict[str, Any], pr_body: str, repo_files_list: List[str]
) -> Tuple[bool, List[str]]:
    """
    Evaluate the "require" block. Return (ok, errors).
    repo_files_list should be full repo file paths (from git index scan) for glob matches
    """
    errors: List[str] = []

    # files_exist_any
    fea = require.get("files_exist_any")
    if isinstance(fea, list) and fea:
        if not file_exists_any(fea):
            errors.append(f"Required file(s) missing (any-of): {fea}")

    # tests_match_any
    tma = require.get("tests_match_any")
    if isinstance(tma, list) and tma:
        if not match_any_glob(tma, repo_files_list):
            errors.append(f"Required test file(s) missing (any match): {tma}")

    # docs_contains
    dc = require.get("docs_contains")
    if isinstance(dc, list) and dc:
        for rule in dc:
            fp = rule.get("file")
            must = rule.get("must_include")
            if not fp or not must:
                continue
            txt = read_text_file(fp)
            if txt is None:
                errors.append(f"Documentation file missing: {fp}")
            else:
                if must not in txt:
                    errors.append(
                        f"Documentation missing required text '{must}' in {fp}"
                    )

    # pr_template_checkboxes_checked
    cb = require.get("pr_template_checkboxes_checked")
    if isinstance(cb, list) and cb:
        for item in cb:
            if not checkbox_checked(pr_body, item):
                errors.append(f"Required PR checkbox not checked: {item}")

    # artifact_or_link_present
    aolp = require.get("artifact_or_link_present")
    if isinstance(aolp, dict):
        one_of = aolp.get("one_of", [])
        ok_any = False
        reasons = []
        for opt in one_of:
            if opt.get("type") == "file":
                prefix = opt.get("path_prefix", "")
                if prefix and Path(prefix).exists():
                    # must contain at least one file
                    p = Path(prefix)
                    if any(x.is_file() for x in p.rglob("*")):
                        ok_any = True
                        break
                reasons.append(f"missing files under {prefix}")
            elif opt.get("type") == "text_in_pr_body":
                pat = opt.get("pattern", "")
                if pat and re.search(pat, pr_body, flags=re.IGNORECASE):
                    ok_any = True
                    break
                reasons.append(f"missing PR body text pattern: {pat}")
        if not ok_any:
            errors.append(
                f"Bench evidence missing (need one-of): {one_of}. "
                f"Details: {', '.join(reasons)}"
            )

    return (len(errors) == 0), errors


def list_repo_files() -> List[str]:
    """
    Return repo file list from the working tree (tracked or not).
    For gate checks we only need existence by glob; keep it simple.
    """
    out: List[str] = []
    for p in Path(".").rglob("*"):
        if p.is_file():
            out.append(str(p).replace("\\", "/"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--pr", required=True, type=int)
    ap.add_argument("--base", required=True)
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        die("GITHUB_TOKEN not set")

    policy = load_json(args.policy)

    # Quick applicability checks
    applies = policy.get("applies_to", {})
    branches = applies.get("branches", [])
    if branches and args.base not in branches:
        gha_notice(
            f"Base branch '{args.base}' not in policy branches {branches}; "
            "skipping gates."
        )
        return 0

    pr = fetch_pr(args.repo, args.pr, token)
    pr_body = pr.get("body") or ""
    pr_labels = [lbl["name"] for lbl in (pr.get("labels") or [])]
    changed_files = fetch_pr_files(args.repo, args.pr, token)

    # Build repo file list for test glob checks
    repo_files_list = list_repo_files()

    failures: List[str] = []

    # Enforce required PR labels any-of
    required_any = policy.get("required_pr_labels_any_of", [])
    if required_any:
        if not pr_has_required_labels_any(pr_labels, required_any):
            failures.append(
                f"PR must have at least one of these labels: {required_any}. "
                f"Found: {pr_labels}"
            )

    # Map checkbox ids -> text
    checkbox_defs = policy.get("required_pr_template_checkboxes", [])
    id_to_text = {}
    for c in checkbox_defs:
        cid = c.get("id")
        txt = c.get("text")
        if cid and txt:
            id_to_text[cid] = txt

    # Enforce required PR template checkboxes (global)
    for c in checkbox_defs:
        if c.get("required") is True:
            txt = c.get("text", "")
            if txt and not checkbox_checked(pr_body, txt):
                failures.append(f"Required PR checkbox not checked: {txt}")

    # Gate rules
    gate_rules = policy.get("gate_rules", [])
    for rule in gate_rules:
        rid = rule.get("id", "<unknown>")
        when = rule.get("when", {})
        req = rule.get("require", {})

        # Skip milestone gate for now (explained in header)
        if "milestone" in when:
            gha_notice(
                f"Skipping rule '{rid}' (milestone-based enforcement "
                "not implemented in this runner)."
            )
            continue

        # Evaluate when clauses
        ok_when = True

        if "labels_any" in when:
            if not labels_any(pr_labels, when["labels_any"]):
                ok_when = False

        if ok_when and "changed_paths_any" in when:
            if not changed_paths_any(changed_files, when["changed_paths_any"]):
                ok_when = False

        if not ok_when:
            continue

        # Expand checkbox ids to their text so checks work
        if "pr_template_checkboxes_checked" in req:
            expanded = []
            for item in req["pr_template_checkboxes_checked"]:
                # if it's an id, expand; else treat as literal text
                expanded.append(id_to_text.get(item, item))
            req = dict(req)
            req["pr_template_checkboxes_checked"] = expanded

        ok_req, errs = ensure_requirements(req, pr_body, repo_files_list)
        if not ok_req:
            for e in errs:
                failures.append(f"[{rid}] {e}")

    if failures:
        for f in failures:
            gha_error(f)
        print("\nPR Gates: FAILED\n")
        return 1

    print("PR Gates: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
