# Gotchas — curated one-liners for repeated mistakes

Rule: add a line only when the **same mistake was made twice**. One is bad luck, two is a pattern that costs future runs. See `agent-base` skill §9.2.

Format: one bullet per gotcha, ≤2 lines, prefixed with a `#tag`.

```markdown
- `#tag` One-line description of the failure mode + the correct action.
```

Examples (delete after seeding real ones):

- `#kubectl` После restart pod uid меняется — всегда `get pods -o name` перед `cp`/`exec`, не хранить имя из предыдущей сессии.
- `#git` Никогда `git add -A` / `git add <dir>` — стейджит чужие незакоммиченные файлы.
- `#pytest` Перед первым запуском после чужой миграции — `--create-db`, иначе тесты падают на несуществующей колонке.
