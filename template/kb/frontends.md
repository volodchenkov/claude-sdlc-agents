# Frontends

> Fill in: each frontend project that ships from this repo, with its
> stack, conventions, and build commands. Agents (vue-developer,
> react-developer, ui-tester, designer) read this to know what they're
> writing for.

## Inventory

| Project | Path | Stack | Purpose |
|---|---|---|---|
| `<name>` | `apps/<dir>` | Vue 3 / Nuxt 3 / Pinia / TS strict | <one-line purpose> |
| `<name>` | `apps/<dir>` | Vue 2 / Nuxt 2 / Vuex / class components | <one-line purpose> |
| `<name>` | `apps/<dir>` | React 18 / Next.js 14 / App Router | <one-line purpose> |
| `<name>` | `apps/<dir>` | Angular X | <one-line purpose> |

## Per-project details

For each frontend, document:

### `<project name>` (`apps/<dir>`)

- **Stack:** Vue 3.X / Nuxt 3.X / Pinia / Vite X / TypeScript strict
- **API style:** Composition API only, `<script setup lang="ts">`
- **State:** Pinia (no Vuex)
- **Data fetching:** `useFetch` / `useAsyncData` (Nuxt 3 conventions)
- **Routing:** file-based (Nuxt 3 `pages/`)
- **Styling:** Tailwind / CSS Modules / styled-components / …
- **UI library:** — / Buefy / Material UI / shadcn / …
- **Component conventions:** see naming in [`conventions.md`](conventions.md)
- **Build commands:**
  ```bash
  cd <repo>/apps/<dir>
  yarn lint
  npx nuxi typecheck
  npx nuxi build
  ```

### `<project name>` (`apps/<dir>`)

- **Stack:** Vue 2.X / Nuxt 2.X / Vuex / vue-property-decorator / TS
- **API style:** Class components only (`@Component`)
- **State:** Vuex (no Pinia)
- **Data fetching:** `this.$axios` (Nuxt 2 module pattern)
- **UI library:** Buefy / …
- **Build commands:**
  ```bash
  cd <repo>/apps/<dir>
  yarn lint
  yarn build
  ```

### `<project name>` (`apps/<dir>`)

- **Stack:** React 18 / Next.js 14 / App Router
- **Components:** Functional + hooks (no class components)
- **State:** Zustand / Redux Toolkit / Context (pick one, document)
- **Server vs Client:** App Router — default Server, `'use client'` only when needed
- **Data fetching:** Server: direct `await`; Client: SWR / React Query
- **Styling:** Tailwind / CSS Modules / …
- **Build commands:**
  ```bash
  cd <repo>/apps/<dir>
  yarn lint
  next typecheck   # if configured
  next build
  ```

## Cross-frontend rules

- Don't mix conventions across frontends — each is consistent within itself
- Match the existing patterns of the target frontend; don't import Vue 3
  patterns into a Vue 2 project (or vice versa)
- Storybook / Compodoc: optional per project; if used, document where stories live

## Skill overrides

The `vue-developer.md` and `react-developer.md` prompts encode generic
best practices. Project-specific divergence (e.g. "we use Options API
in this Vue 3 codebase for legacy reasons") goes here, and the project
wins.
