# Local documentation reader

Implemented on 2026-10-16; documentation rechecked against merged main on 2026-10-22 (Asia/Calcutta). The reader is reproducible from Git; actual VM/public-service acceptance is not established by this review.

## Start the reader

From the repository root, with Python 3.12 and uv installed:

```bash
uv run --frozen --group site python -m scripts.build_docs_site --serve
```

Open **http://127.0.0.1:8000/** in your browser. This command works in PowerShell and Bash; it builds first and runs until Ctrl+C. For another port, add `--port 8001`. It needs neither PostgreSQL nor Ollama. The Python HTTP server is a local preview server, not the planned production web server.

Build without serving:

```bash
uv run --frozen --group site python -m scripts.build_docs_site
```

The deployable static directory is `.site-work/site/`; staging content and browser evidence are also under the ignored `.site-work/` directory. Run the build command after source/template changes; this preview does not provide live reload.

## Reader features

- Home, package catalog, LangChain/LangGraph landing pages, exact-version overview and individual articles.
- Five approved LangChain 1.4.6 articles, with review banners and unchanged source quotations/links.
- Search for article text, symbols and website inventory entries. Try `create_agent`.
- Filter the 30-package / 89-release catalog by package name or exact version, with an explicit empty state.
- Generated compatibility table using tracked runtime JSON, including dependency and invocation failures.
- Review/provenance policy and downloadable audit manifests.
- Four learning placeholders backed by the human-review queue; draft explanations and model output are not rendered as approved prose.
- Responsive layout with a keyboard-operable mobile menu and Escape-to-close behavior.

The wider reference is inventoried but not published as article pages. Other packages link to upstream PyPI context; their inventory entries do not claim final approval or complete runtime validation. There is no chatbot, generation form or database/model API behind the reader.

## Publication inputs and approval boundary

`website/publication.json` explicitly selects the existing approved export and pins hashes for its six Markdown files, export manifest and approval record. The builder checks file containment, all eight hashes, the approval's export identity, catalog identity, unique page reviews, final decisions and matching page identities/review metadata. A changed source or mismatched approval stops the build. New articles require a reviewed publication selection; no directory-wide scan publishes drafts.

The builder stages checked source bytes and inserts a website-only review banner after the heading. It does not rewrite approved Markdown in `docs/generated/`. The version overview is labelled “Approved collection” and “Generated navigation,” rather than falsely attributing a model draft to the navigation page. Hashes/records establish consistency with the checked-in selection; they are not signed reviewer attestations.

Approved export files use LF checkout rules in `.gitattributes` so Windows line-ending conversion does not invalidate their byte-level hashes.

The catalog and compatibility view are assembled from tracked reports. No local `data/` snapshot, archive, database backup, browser installation or cloud account is needed to build or serve the site. MkDocs and its transitive dependencies are in the `site` dependency group and frozen lockfile; existing application dependencies are retained.

## Verification

- Strict MkDocs build passed, including Markdown link/anchor checks, both in a tracked-files-only clean checkout and a checkout with `core.autocrlf=true`.
- Rendered HTML check validated all local link/asset references; each run prints its actual count.
- Chromium desktop at 1440 px: home, package/version filters, no-match state, article navigation, approval banners and search-result navigation passed.
- Chromium mobile at 390 px: keyboard-operated menu, package filter and horizontal-overflow checks passed.
- No uncaught JavaScript errors were recorded in the checked browser flow.
- Eight reader regression tests cover fresh-input assembly, exclusion of unapproved files, changed approved text, approval consistency, path escape, rendered links/anchors and the placeholder/publication boundary. The current full offline baseline is 183 passing tests (225 collected), with 42 database/model tests deselected locally.

Browser checks are repeatable:

```bash
uv run --frozen playwright install chromium
uv run --frozen python -m scripts.check_docs_site_browser
```

On Linux, missing browser system dependencies may require Playwright's `install --with-deps chromium` setup. CI uses that setup. The check starts its own ephemeral localhost server and shuts it down afterwards. Optional `--url http://127.0.0.1:8000` checks an existing preview. Screenshots and `browser-report.json` are saved under `.site-work/qa/`. External source availability and complete accessibility conformance are not established by these checks.

CI builds the site, runs browser/link/placeholder and four pinned learning-recipe checks and uploads the built reader and browser evidence. Public hosting, HTTPS, cloud sizing, VM recovery and database/model deployment remain the next milestone in [the closure tracker](closure-tracker.md).

For VM serving, use the [interactive first-run setup and deployment runbook](deployment/supplied-vm.md), not the local preview server. The [documentation index](README.md) distinguishes current guidance from historical reports.
