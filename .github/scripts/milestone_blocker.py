#!/usr/bin/env python3
"""
Milestone Blocker for Production Readiness v1.1

Checks if a milestone has any open blocking issues and fails the workflow if so.
This prevents merges to main when critical issues remain unresolved.

Blocking criteria:
1. Open issues in the milestone with specified labels (e.g., "blocking")
2. Open issues in the milestone with title prefixes (e.g., "FTS-", "PAGE-", "PERF-")
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional

import requests


def gha_error(msg: str) -> None:
    print(f"::error::{msg}")


def gha_warning(msg: str) -> None:
    print(f"::warning::{msg}")


def gha_notice(msg: str) -> None:
    print(f"::notice::{msg}")


def die(msg: str, code: int = 1) -> None:
    gha_error(msg)
    raise SystemExit(code)


def gh_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "milestone-blocker-v1.1",
    }


def gh_get(url: str, token: str, params: Optional[Dict[str, Any]] = None) -> Any:
    r = requests.get(url, headers=gh_headers(token), params=params, timeout=30)
    if r.status_code >= 400:
        die(f"GitHub API GET failed {r.status_code}: {url} :: {r.text[:500]}")
    return r.json()


def fetch_milestones(repo: str, token: str) -> List[Dict[str, Any]]:
    """Fetch all open milestones for the repo."""
    milestones: List[Dict[str, Any]] = []
    page = 1
    while True:
        data = gh_get(
            f"https://api.github.com/repos/{repo}/milestones",
            token,
            params={"state": "open", "per_page": 100, "page": page},
        )
        if not data:
            break
        milestones.extend(data)
        if len(data) < 100:
            break
        page += 1
    return milestones


def find_milestone_number(
    milestones: List[Dict[str, Any]], milestone_name: str
) -> Optional[int]:
    """Find milestone number by name."""
    for m in milestones:
        if m.get("title", "").strip().lower() == milestone_name.strip().lower():
            return m.get("number")
    return None


def fetch_milestone_issues(
    repo: str, milestone_number: int, token: str
) -> List[Dict[str, Any]]:
    """Fetch all open issues for a milestone."""
    issues: List[Dict[str, Any]] = []
    page = 1
    while True:
        data = gh_get(
            f"https://api.github.com/repos/{repo}/issues",
            token,
            params={
                "milestone": milestone_number,
                "state": "open",
                "per_page": 100,
                "page": page,
            },
        )
        if not data:
            break
        # Filter out pull requests (they have a "pull_request" key)
        for item in data:
            if "pull_request" not in item:
                issues.append(item)
        if len(data) < 100:
            break
        page += 1
    return issues


def check_blocking_labels(
    issues: List[Dict[str, Any]], blocking_labels: List[str]
) -> List[Dict[str, Any]]:
    """Find issues with any of the blocking labels."""
    blocking_labels_lower = {lbl.lower().strip() for lbl in blocking_labels}
    blockers = []
    for issue in issues:
        issue_labels = {
            lbl.get("name", "").lower() for lbl in issue.get("labels", [])
        }
        if issue_labels & blocking_labels_lower:
            blockers.append(issue)
    return blockers


def check_blocking_prefixes(
    issues: List[Dict[str, Any]], blocking_prefixes: List[str]
) -> List[Dict[str, Any]]:
    """Find issues with titles starting with any blocking prefix."""
    blockers = []
    for issue in issues:
        title = issue.get("title", "")
        for prefix in blocking_prefixes:
            if title.startswith(prefix.strip()):
                blockers.append(issue)
                break
    return blockers


def format_issue(issue: Dict[str, Any]) -> str:
    """Format issue for output."""
    number = issue.get("number", "?")
    title = issue.get("title", "Untitled")
    url = issue.get("html_url", "")
    labels = ", ".join(lbl.get("name", "") for lbl in issue.get("labels", []))
    return f"#{number}: {title} [{labels}] - {url}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Check for blocking issues in a milestone"
    )
    ap.add_argument("--repo", required=True, help="owner/repo")
    ap.add_argument("--milestone", required=True, help="Milestone name")
    ap.add_argument(
        "--blocking-labels",
        default="blocking",
        help="Comma-separated list of blocking labels",
    )
    ap.add_argument(
        "--blocking-prefixes",
        default="",
        help="Comma-separated list of blocking title prefixes",
    )
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        die("GITHUB_TOKEN not set")

    # Parse labels and prefixes
    blocking_labels = [
        lbl.strip() for lbl in args.blocking_labels.split(",") if lbl.strip()
    ]
    blocking_prefixes = [
        pfx.strip() for pfx in args.blocking_prefixes.split(",") if pfx.strip()
    ]

    print(f"Checking milestone: {args.milestone}")
    print(f"Blocking labels: {blocking_labels}")
    print(f"Blocking prefixes: {blocking_prefixes}")
    print()

    # Fetch milestones
    milestones = fetch_milestones(args.repo, token)
    milestone_number = find_milestone_number(milestones, args.milestone)

    if milestone_number is None:
        gha_notice(
            f"Milestone '{args.milestone}' not found or has no open issues. "
            "Passing check."
        )
        print("Milestone Blocker: PASSED (milestone not found)")
        return 0

    print(f"Found milestone #{milestone_number}")

    # Fetch issues
    issues = fetch_milestone_issues(args.repo, milestone_number, token)
    print(f"Open issues in milestone: {len(issues)}")

    if not issues:
        print("Milestone Blocker: PASSED (no open issues)")
        return 0

    # Check for blockers
    all_blockers: List[Dict[str, Any]] = []

    if blocking_labels:
        label_blockers = check_blocking_labels(issues, blocking_labels)
        all_blockers.extend(label_blockers)
        if label_blockers:
            print(f"\nBlocking issues (by label):")
            for issue in label_blockers:
                print(f"  - {format_issue(issue)}")

    if blocking_prefixes:
        prefix_blockers = check_blocking_prefixes(issues, blocking_prefixes)
        # Avoid duplicates
        existing_numbers = {b.get("number") for b in all_blockers}
        for b in prefix_blockers:
            if b.get("number") not in existing_numbers:
                all_blockers.append(b)
        if prefix_blockers:
            print(f"\nBlocking issues (by prefix):")
            for issue in prefix_blockers:
                print(f"  - {format_issue(issue)}")

    # Deduplicate
    seen = set()
    unique_blockers = []
    for b in all_blockers:
        n = b.get("number")
        if n not in seen:
            seen.add(n)
            unique_blockers.append(b)

    if unique_blockers:
        print(f"\n{'='*60}")
        print(f"BLOCKED: {len(unique_blockers)} blocking issue(s) remain open")
        print(f"{'='*60}\n")

        for issue in unique_blockers:
            gha_error(f"Blocking issue: {format_issue(issue)}")

        print("\nMilestone Blocker: FAILED")
        print("Resolve all blocking issues before merging to main.")
        return 1

    print("\nMilestone Blocker: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
