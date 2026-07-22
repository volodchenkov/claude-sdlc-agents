# Journal — dated append-only log

One file per day: `YYYY-MM-DD.md`. See `agent-base` skill §9.1.

**Write** anything the code / `kb/*.md` / SPEC / ADR / git log does NOT already contain: credentials, undocumented endpoints, «why Y was configured this way», gotchas, incident root causes, verbal instructions from the initiator.

**Format** (one entry):

```markdown
## HH:MM — Заголовок #tag1 #tag2

1–3 lines of body. Facts, not narrative. Cite source.
```

**Retrieval:**

```bash
grep -riE '<keyword>' kb/journal/ kb/gotchas.md | tail -30
```

Existing tags:

```bash
grep -h '^##' kb/journal/*.md | grep -oE '#[a-z0-9-]+' | sort -u
```

Never rewrite past entries. Corrections = new entry with `#correction`.
