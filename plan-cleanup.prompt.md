## Plan: Cleanup Unused Definitions and Document Directory Structure

TL;DR - Scan the repository for unused definitions, verify candidates, remove only those safe to delete, and create a directory structure document.

**Steps**
1. Verify the repository structure and scan all Python source files under `AutoDocsGenAI/` for definitions and references.
2. Confirm safe removal candidates:
   - `AutoDocsGenAI/discovery/providers/manual.py` — `ManualDiscoveryProvider` appears unused by any package code.
   - `AutoDocsGenAI/planner/selectors.py` — `select_pages` appears unused by any package code.
3. Confirm that these removals will not affect runtime references:
   - `HTTPClient` in `AutoDocsGenAI/utils/http_client.py` is not directly referenced by name but is required to construct the shared `http_client` instance.
   - `main()` in `AutoDocsGenAI/main.py` is the script entrypoint and should remain.
   - Config model classes in `AutoDocsGenAI/models/config.py` are referenced indirectly through `Config` usage and should remain.
4. Remove the unused class and function from their files and keep the rest of the file structure intact.
5. Create `dir_structure.md` at the repository root listing every directory and file used in the workspace, with a 1-2 sentence justification for why each item must exist and why it cannot be merged or deleted.

**Directory structure documentation notes**
- Focus on unique purpose and production-grade organization.
- Flag any placeholder or redundant file/folder for possible merge/removal.
- Keep the final structure concise yet complete for future maintainers.

**Relevant files**
- `/workspaces/auto_doc_gen/AutoDocsGenAI/discovery/providers/manual.py`
- `/workspaces/auto_doc_gen/AutoDocsGenAI/planner/selectors.py`
- `/workspaces/auto_doc_gen/AutoDocsGenAI/utils/http_client.py`
- `/workspaces/auto_doc_gen/AutoDocsGenAI/main.py`
- `/workspaces/auto_doc_gen/AutoDocsGenAI/models/config.py`

**Verification**
1. Run a package-wide grep or static analysis to confirm no references after removal.
2. Execute any existing test suite or at least `python -m pytest AutoDocsGenAI/tests` if available.
3. Optionally run `python AutoDocsGenAI/main.py` in a dry path to ensure import-time behavior still succeeds.

**Decisions**
- Remove only clearly unused definitions; do not remove entrypoints or shared utility classes used indirectly.
- No broad refactor is planned; focus is on cleanup of dead symbols only.

**Further Considerations**
1. If you want, I can also audit for dead modules or unused imports next.
