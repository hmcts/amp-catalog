#!/usr/bin/env python3
"""Reconcile docs/apis.json by discovering APIs that publish via the catalog's
reusable Swagger UI workflow.

Discovery strategy:
  1. GitHub code search for repos in the org whose workflows reference
     `<ORG>/amp-catalog/.github/workflows/publish-swagger-ui.yml`.
  2. For each repo, fetch its live spec from
     `https://<ORG>.github.io/<repo>/openapi-spec.yml` and read info.title /
     info.description. Repos with no live site yet are skipped.
  3. Derive the owning team from the repo's CODEOWNERS (first @org/team).

Environment:
  GH_TOKEN  - token with org repo read + code search (required)
  ORG       - GitHub org (default: hmcts)
  OUTPUT    - path to write (default: docs/apis.json)
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import yaml

ORG = os.environ.get("ORG", "hmcts")
TOKEN = os.environ.get("GH_TOKEN", "")
OUTPUT = os.environ.get("OUTPUT", "docs/apis.json")
WORKFLOW_REF = f"{ORG}/amp-catalog/.github/workflows/publish-swagger-ui.yml"

API = "https://api.github.com"


def gh(url, accept="application/vnd.github+json"):
    req = urllib.request.Request(url)
    req.add_header("Accept", accept)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def find_repos():
    """Repos whose code references the reusable workflow."""
    query = f'"{WORKFLOW_REF}" org:{ORG}'
    url = f"{API}/search/code?q={urllib.parse.quote(query)}&per_page=100"
    try:
        data = json.loads(gh(url))
    except urllib.error.HTTPError as e:
        print(f"::error::code search failed: {e}", file=sys.stderr)
        raise
    repos = {item["repository"]["name"] for item in data.get("items", [])}
    return sorted(repos)


def fetch_spec_info(repo):
    """(title, description) from the repo's live Pages spec, or None."""
    url = f"https://{ORG}.github.io/{repo}/openapi-spec.yml"
    try:
        raw = urllib.request.urlopen(url, timeout=30).read()
    except (urllib.error.HTTPError, urllib.error.URLError):
        return None
    try:
        info = (yaml.safe_load(raw) or {}).get("info", {})
    except yaml.YAMLError:
        return None
    return info.get("title", repo), info.get("description", "")


def fetch_team(repo):
    """First @org/team in the repo's CODEOWNERS, else 'TBD'."""
    for path in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        url = f"{API}/repos/{ORG}/{repo}/contents/{path}"
        try:
            text = gh(url, accept="application/vnd.github.raw").decode()
        except urllib.error.HTTPError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            for tok in line.split()[1:]:
                if tok.startswith(f"@{ORG}/"):
                    return tok.split("/", 1)[1]
        break
    return "TBD"


def main():
    repos = find_repos()
    print(f"Discovered {len(repos)} repo(s) referencing the workflow.")
    apis = []
    for repo in repos:
        info = fetch_spec_info(repo)
        if info is None:
            print(f"  skip {repo}: no live spec at Pages site")
            continue
        title, description = info
        apis.append(
            {
                "name": repo,
                "title": title,
                "description": description,
                "team": fetch_team(repo),
            }
        )
        print(f"  list {repo}: {title}")

    apis.sort(key=lambda a: a["name"])
    with open(OUTPUT, "w") as fh:
        json.dump({"apis": apis}, fh, indent=2)
        fh.write("\n")
    print(f"Wrote {len(apis)} API(s) to {OUTPUT}")


if __name__ == "__main__":
    main()
