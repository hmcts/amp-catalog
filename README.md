# HMCTS API Catalog

A central index of published HMCTS API documentation. The catalog is a single
static page that lists every participating API and links to its rendered
Swagger UI documentation and source repository.

**Live catalog:** https://hmcts.github.io/amp-catalog/

This is the central-index half of the GitHub Pages stop-gap described in
[Migrating from API Hub](https://tools.hmcts.net/confluence/spaces/AMP/pages/1973306073/Migrating+from+API+Hub).
Each API hosts its **own** documentation site at `https://hmcts.github.io/<repo>/`;
this repo just lists them. See [docs/CATALOG-PLAN.md](docs/CATALOG-PLAN.md) for
the design and rationale.

---

## How to list your API in the catalog

There is **one step** for an API team, plus the listing happens automatically.

### Fast path — the Claude Code skill (recommended)

If you use Claude Code, the `publish-api-to-catalog` skill does the whole thing
for you: it finds your spec, runs a public-exposure eligibility check, adds the
caller workflow, opens the PR, and verifies the live site and catalog listing.

1. **Install the skill once** (makes it available in any repo):
   ```bash
   mkdir -p ~/.claude/skills
   # from a checkout of this repo:
   cp -r amp-catalog/.claude/skills/publish-api-to-catalog ~/.claude/skills/
   # or copy it straight from GitHub:
   #   gh repo clone hmcts/amp-catalog -- --depth 1 \
   #     && cp -r amp-catalog/.claude/skills/publish-api-to-catalog ~/.claude/skills/
   ```
2. **Run Claude Code from inside your API repo** and invoke it:
   ```
   /publish-api-to-catalog
   ```
   or just ask: *"publish this API to the catalog"*.
3. Answer the eligibility prompt (the skill will not publish an internal-only
   API), then let it open the PR and verify the result.

> The skill is the optional fast path. The manual steps below are the source of
> truth and work without Claude Code.

### Add one workflow to your API repo

Drop this single file into your repo. That's the entire footprint — no viewer
HTML, no Pages setup, no edits to your existing CI:

```yaml
# .github/workflows/publish-api-docs.yml
name: Publish API docs
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
      openapi_path: src/main/resources/openapi/openapi-spec.yml
```

The shared workflow enables GitHub Pages, generates the Swagger UI viewer
(Try-It disabled), and deploys your spec to `https://hmcts.github.io/<repo>/`.
Cut a release (or run it via *workflow_dispatch*) to publish.

> Pin to a released tag (`@v1`), not `@main`, so a change to the shared
> workflow can't break your repo unexpectedly.

### Listing is automatic

A daily job in this repo
([`discover-apis.yml`](.github/workflows/discover-apis.yml)) scans the org for
repos using the workflow above, reads each live spec's `info.title` /
`info.description`, derives the team from your `CODEOWNERS`, and opens a PR
updating [`docs/apis.json`](docs/apis.json). Once that merges your API appears
in the catalog. You don't have to register anything by hand.

> **Want it listed immediately, or need to override the auto-derived
> title/description/team?** Edit [`docs/apis.json`](docs/apis.json) directly and
> open a PR. The **Validate API catalog** workflow checks it (valid JSON,
> required fields, no duplicate names). Manual entries use the same fields:
> `name` (repo name — required), `title`, `description`, `team`, and optional
> `docs` / `repo` URL overrides.
