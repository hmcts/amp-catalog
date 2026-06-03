---
name: publish-api-to-catalog
description: >-
  Publish an HMCTS API's OpenAPI documentation to the API Catalog (Swagger UI on
  GitHub Pages) and get it listed. Use when working inside an API repo and the
  user wants to publish/expose their API docs, "add my API to the catalog", set
  up the publish-api-docs workflow, or get a hmcts.github.io docs site. Performs
  an eligibility (public-exposure) safety check, adds the one caller workflow,
  opens a PR, then verifies the live site and catalog listing.
---

# Publish an API to the HMCTS API Catalog

This skill onboards the **current repository** (an API repo) to the API Catalog
stop-gap: a public Swagger UI site at `https://hmcts.github.io/<repo>/`, plus an
automatic listing in [amp-catalog](https://github.com/hmcts/amp-catalog).

The per-repo footprint is a single workflow file — most of this skill is
**checking** the API is safe to expose and **verifying** the result.

Run these phases in order. Do not skip Phase 2.

---

## Phase 1 — Locate and validate the OpenAPI spec

1. Confirm you are in an API repo (it has an OpenAPI spec). Find it:
   ```bash
   find . -path ./.git -prune -o -name "openapi-spec.y*ml" -print 2>/dev/null
   ```
   The HMCTS convention is `src/main/resources/openapi/openapi-spec.yml`. If
   there are several, ask the user which is the published spec.
2. Sanity-check it parses and read its `info` block (used later for the catalog
   entry):
   ```bash
   ruby -ryaml -e 'i=YAML.load_file(ARGV[0])["info"]; puts i["title"]; puts i["description"]' <SPEC_PATH>
   ```
   If it does not parse, stop and report — fix the spec first.
3. Record the path relative to the repo root as `OPENAPI_PATH`.

## Phase 2 — Eligibility check (REQUIRED — do not skip)

GitHub Pages on a **public** repo is **world-readable**. Only external APIs may
be published this way:

- **2c — external, documentation-only:** ✅ eligible
- **2b — external, mock execution:** ✅ eligible (docs-only here; Try-It is off)
- **2a — internal (developers only):** ❌ **NOT eligible** — it must not be
  exposed publicly. These stay on API Hub until the Developer Portal lands.

Do this:
1. Check repo visibility:
   ```bash
   gh repo view --json visibility,nameWithOwner -q '.visibility + "  " + .nameWithOwner'
   ```
2. **Ask the user to confirm the API is external (bucket 2b or 2c) and safe to
   expose to the public internet.** State plainly that this publishes the spec
   to a world-readable URL.
3. If the API is internal-only (2a), or the user is unsure, or the repo is
   `private`/`internal` and they cannot confirm it should be public: **STOP.**
   Do not add the workflow. Explain that internal APIs are out of scope for this
   stop-gap and should wait for the APIM Developer Portal.

Only continue past here once the user has explicitly confirmed public exposure
is intended.

## Phase 3 — Add the caller workflow

Create `.github/workflows/publish-api-docs.yml` with `openapi_path` set to the
`OPENAPI_PATH` from Phase 1. Pin to the released tag `@v1`:

```yaml
name: Publish API docs

# Publishes this API's Swagger UI to https://hmcts.github.io/<repo>/ on release.
# All the work lives in the shared catalog workflow; this repo only declares
# where its OpenAPI spec is. See https://github.com/hmcts/amp-catalog.
on:
  release:
    types: [ published ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  docs:
    uses: hmcts/amp-catalog/.github/workflows/publish-swagger-ui.yml@v1
    with:
      openapi_path: <OPENAPI_PATH>
```

Do **not** add `docs/index.html`, a per-repo `publish-swagger-ui.yml`, or any
edit to `ci-released.yml` — the shared workflow handles all of that (enabling
Pages, generating the viewer, deploying).

## Phase 4 — Open a PR

Branch, commit just this file, push, and open a PR. Never commit on the default
branch directly.

```bash
git checkout -b chore/publish-api-docs
git add .github/workflows/publish-api-docs.yml
git commit -m "ci: publish API docs to GitHub Pages via amp-catalog"
git push -u origin chore/publish-api-docs
gh pr create --fill
```

Tell the user the PR URL and that merging it, then cutting a release, publishes
the docs.

## Phase 5 — Publish and verify

After the PR is merged (ask the user to merge, or merge if they direct you):

1. Trigger a publish without waiting for a real release:
   ```bash
   gh workflow run publish-api-docs.yml
   ```
2. Watch it to completion:
   ```bash
   gh run list --workflow publish-api-docs.yml --limit 1
   gh run watch <RUN_ID>
   ```
3. **Allow release (tag) deploys.** The auto-created `github-pages` environment
   permits deployments only from `main` by default. A `release`-triggered run
   uses the **tag** ref, so it is rejected at the environment gate — the deploy
   job fails instantly with no logs and the site stays 404. Add a tag policy
   once (after the first run has created the environment; requires repo admin):
   ```bash
   repo=$(gh repo view --json name -q .name)
   gh api -X POST "repos/hmcts/$repo/environments/github-pages/deployment-branch-policies" \
     -f name='*' -f type='tag'
   ```
4. Confirm the live site (expect HTTP 200):
   ```bash
   repo=$(gh repo view --json name -q .name)
   curl -sS -o /dev/null -w "%{http_code}\n" "https://hmcts.github.io/$repo/"
   curl -sS -o /dev/null -w "%{http_code}\n" "https://hmcts.github.io/$repo/openapi-spec.yml"
   ```
5. **Catalog listing** is automatic — the daily `discover-apis.yml` job in
   amp-catalog picks the repo up and opens a PR adding it to `docs/apis.json`.
   Tell the user it will appear within ~24h.

## Optional — list immediately / override metadata

If the user wants it in the catalog now, or the auto-derived title / description
/ team will be wrong, add the entry by hand in **amp-catalog** instead of
waiting for discovery:

1. In a clone of `hmcts/amp-catalog`, add to `docs/apis.json`:
   ```json
   {
     "name": "<repo-name>",
     "title": "<from spec info.title>",
     "description": "<one-liner>",
     "team": "<owning team>"
   }
   ```
   (`docs` / `repo` URLs are derived from `name`; override only if non-standard.)
2. Open a PR to amp-catalog. The `validate-catalog.yml` check must pass.

## Guardrails

- The Phase 2 eligibility check is mandatory. When in doubt, do not publish.
- Always pin the caller to `@v1`, never `@main`.
- This is a temporary bridge; when the APIM Developer Portal lands these sites
  are retired. Do not build anything on top of the Pages URLs.
