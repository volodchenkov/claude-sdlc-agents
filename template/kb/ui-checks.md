# UI checks learned from escaped defects

> Fill in: one generic check per confirmed escape — a defect the initiator
> found after a UX report said «no bugs». Replace the sample entry below.

A checklist the ui-tester applies to every screen it tests (`agents/ui-tester.md` «Escapes»). Add one line when the initiator finds a defect after a UX report said «no bugs» — one escape is enough. Write the class, not the instance, and name the issue.

```markdown
- <class of defect and how to check it>. — <ISSUE-ID>
```

Example (delete after seeding real ones):

- Money is exact: no float tails, one format per value type on a screen. — PROJ-1
