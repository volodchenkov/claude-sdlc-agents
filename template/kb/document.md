# Documentation discipline

> Fill in: how this project documents code — docstring style, generation
> tool, where module-level docs live.

## Docstring style (Python)

- Tool: Sphinx + napoleon / MkDocs + mkdocstrings / pdoc / …
- Style: Google / NumPy / reStructuredText / free-prose
- Where docs are generated: `docs/source/` (Sphinx) / `docs/` (MkDocs) / inline only
- How to build: `cd docs && make html` / `mkdocs build` / …

If using Sphinx + napoleon, default style is **Google**:

```python
def calculate_delivery_estimate(order, region):
    """Estimate delivery date for `order` to `region`.

    Combines carrier SLA, warehouse processing time, and the region's
    holiday calendar.

    Args:
        order: Order instance to estimate delivery for.
        region: Region instance (destination).

    Returns:
        datetime.date — the expected delivery date.

    Raises:
        ValueError: if region has no carrier configured.
    """
```

## Module-level documentation

- Every Django app gets an RST file in `docs/source/<app>.rst` (Sphinx) / a section in `docs/<app>.md` (MkDocs)
- Update or create when adding a new app or significantly changing one

## Frontend documentation

- Style: TSDoc / JSDoc inline
- Tool: TypeDoc (optional) / Compodoc (Angular) / inline only
- Per-directory `README.md` in significant directories (`composables/`, `stores/`, `pages/`, `hooks/`)
- Example signatures: see `documentation-discipline` skill

## What to document

- New public functions / classes / modules — always docstring
- Inline comments — only when "why" isn't obvious from "what"
- README updates — when change affects how others interact (new env var, new CLI command, new public API)
- Migration files — always intent docstring
- ADR status updates in SPEC sub-issues — when implementing

## What NOT to document

- Auto-generated code
- Trivial getters / setters
- Internal helpers used in one place (better: rename for clarity)
- Outdated information — better no docs than wrong docs

## Definition of Done — documentation slice

A coder's CHANGES is incomplete unless:
- All new public surface has docstrings (in this project's style)
- Inline comments justify any non-obvious "why"
- README / `.env.example` / docs index updated for new public surface
- Migration files have intent docstring
- ADR status posted as comment on SPEC sub-issue (if implementing one)
- Test names are descriptive (read like documentation)

See the `documentation-discipline` skill for examples and full discipline.
