# Journal — dated append-only log

One file per day: `YYYY-MM-DD.md`. See `agent-base` skill §9.1.

**Write** anything the code / `kb/*.md` / SPEC / ADR / git log does NOT already contain: **pointers to credentials** (secret manager path / 1Password item / env-var name — never the value), undocumented endpoints, «why Y was configured this way», gotchas, incident root causes, verbal instructions from the initiator.

**NEVER** write plaintext credentials, tokens, passwords, private keys, API keys, or any raw secret. The journal usually lives in a git-tracked directory — once committed, a secret is compromised even if later «removed» (git history retains it). Log the reference (`1Password: item "alfa-sandbox"` / `Yandex Lockbox: coinex/alfa-sandbox/#password` / `env: ALFA_SANDBOX_PASSWORD`), not the value.

**Format** (one entry):

```markdown
## HH:MM — Заголовок #tag1 #tag2

1–3 lines of body. Facts, not narrative. Cite source.
```

**Retrieval:**

```bash
grep -riE '<keyword>' "$KB_DIR/kb/journal/" "$KB_DIR/kb/gotchas.md" 2>/dev/null | tail -30
```

Existing tags:

```bash
grep -h '^##' "$KB_DIR"/kb/journal/*.md 2>/dev/null | grep -oE '#[a-z0-9-]+' | sort -u
```

Never rewrite past entries. Corrections = new entry with `#correction`.
