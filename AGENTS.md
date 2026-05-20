# AGENTS.md

## Project Overview

ActivityChronio is a Chronio product built on top of ActivityWatch. It is a local-first macOS activity tracker focused on daily review: open a day, see what happened, categorize activity, and understand productivity.

Core promise:
- "Sit down on Monday and see exactly what you did at 3 PM last Wednesday."
- Category-first, Timing.app-inspired UX.
- Local-first data; no cloud dependency.

Primary stack:
- Frontend: Vue 2, Pug templates, TypeScript, Pinia
- Main UI: `aw-server/aw-webui/src/views/activity/Chronio.vue`
- Stores: `aw-server/aw-webui/src/stores/`
- Category logic: `aw-server/aw-webui/src/util/classes.ts`
- Server: Flask in `aw-server`
- Build/deploy: `npm run build` in `aw-server/aw-webui`, or `make deploy-webui`
- Product docs: `docs/PRD.md`, `docs/PM_PROMPT.md`
- GitHub repo: `MaxSchollum/ActivityChronio`

V1 is the daily review product. V2 is the power-user layer: multi-day views, trends, screenshots, settings, search, export/reporting, rules management, goals, shortcuts, and packaging.

---

## Operating Model

Use three separate Codex threads when possible. Keep the responsibilities clean.

### 1. Feedback / Product Thread

Purpose: convert Max's UX/product feedback into clear GitHub issues and keep product docs current.

Allowed:
- Inspect relevant files for context.
- Check existing GitHub issues before creating new ones.
- Create, update, label, and prioritize GitHub issues.
- Update `docs/PRD.md`, `docs/PM_PROMPT.md`, and QA docs.
- Commit documentation or issue-tracking changes.

Not allowed:
- Do not implement product/code changes.
- Do not opportunistically fix bugs found while writing tickets.
- Do not combine unrelated feedback into one ticket unless implementation clearly overlaps.

Issue format:
- Title under 70 characters.
- Context: what the user is trying to do.
- Problem: what currently breaks, confuses, or feels wrong.
- Expected behavior.
- Proposed implementation notes, including likely files.
- Acceptance criteria as checkboxes.
- Labels: `bug` or `enhancement`, plus `v1` or `v2`.
- Effort estimate: XS/S/M/L/XL.

When feedback is dictated or messy, infer intent, state assumptions, and create implementation-ready tickets.

### 2. Implementation Thread

Purpose: implement scoped GitHub issues.

Before coding:
- Read the issue, related comments, and relevant product docs.
- Inspect existing code before proposing changes.
- Identify the smallest surface area needed.
- Prefer local patterns over new abstractions.
- Confirm whether the issue is V1 polish, V2 product work, or a bugfix.

During coding:
- Keep diffs focused on the ticket.
- Preserve existing behavior unless the issue explicitly changes it.
- Avoid broad refactors while implementing narrow UX fixes.
- Reuse existing stores, utilities, styles, and route patterns.
- Do not commit generated build artifacts such as `aw_server/static/`.
- Run an appropriate verification command before handing off.

Default verification:
- Frontend build: `cd aw-server/aw-webui && npm run build`
- For deployed local testing: `make deploy-webui`
- Use browser verification for visible UX changes when a local server is available.

Handoff output:
- Issue numbers implemented.
- Files changed.
- Verification performed.
- Known risks or follow-up tickets needed.

### 3. Acceptance / Verification / Merge Thread

Purpose: act as the final gate before work becomes `master`.

Responsibilities:
- Review the implementation against the GitHub issue acceptance criteria.
- Check that the product behavior matches the user intent, not only the literal ticket text.
- Run build/tests and browser checks when relevant.
- Look for regressions in adjacent flows.
- Confirm docs and issue state are current.
- Merge or push only after verification passes.
- Close GitHub issues only after the fix is on `master`.

Verification checklist:
- The issue acceptance criteria are met.
- The changed UX has loading, empty, hover, error, and disabled states where relevant.
- The app still builds.
- No unrelated files are staged or committed.
- Product docs are updated if shipped behavior changed.
- GitHub issues are closed with a short shipped comment.

If verification fails:
- Do not merge.
- Leave a concise failure summary with reproduction steps.
- Either fix the issue directly if it is small and clearly in scope, or return it to the implementation thread.

---

## General Engineering Rules

- Do not make large architectural changes unless explicitly requested.
- Prefer modifying existing patterns over introducing new abstractions.
- Keep changes small, readable, and easy to review.
- Avoid unnecessary dependencies.
- Avoid premature optimization.
- Do not rewrite ActivityWatch internals unless the ticket requires it.
- Do not remove user data, settings, or migration paths without explicit instruction.
- Treat untracked or modified files as user-owned unless you created them.

---

## UI / UX Standards

Chronio should feel:
- fast
- calm
- intentional
- dense but readable
- local and private
- modern without decorative excess

Prioritize:
- clear visual hierarchy
- predictable interactions
- compact information density
- good empty states
- hover and selected states
- keyboard and mouse ergonomics
- no jarring refreshes or layout jumps

Avoid:
- marketing-page patterns inside the product
- oversized UI
- excessive modals
- visual noise
- decorative gradients/orbs
- hidden state changes without feedback

For operational UI, use restrained styling. Chronio is a work tool, not a landing page.

---

## Code Standards

- Use TypeScript where the surrounding code uses TypeScript.
- Avoid `any` unless matching existing local patterns makes it impractical to avoid.
- Prefer explicit names over clever names.
- Keep functions focused.
- Avoid deeply nested logic.
- Reuse existing utilities before creating new ones.
- Keep comments rare and useful.
- Do not format massive unrelated sections just to satisfy prettier warnings.

Key files:
- `aw-server/aw-webui/src/views/activity/Chronio.vue`: main product UI.
- `aw-server/aw-webui/src/stores/categories.ts`: category CRUD and persistence.
- `aw-server/aw-webui/src/stores/settings.ts`: settings persistence.
- `aw-server/aw-webui/src/util/classes.ts`: default categories and matching logic.
- `aw-server/aw-webui/src/App.vue`: shell/no-shell routing behavior.
- `aw-server/aw-webui/src/route.js`: Chronio routes and redirects.
- `Makefile`: build/deploy helpers.

---

## Git And GitHub Rules

- Default branch is `master`.
- Use branches for implementation work.
- Keep PM/doc-only changes separate from implementation changes when practical.
- Before creating an issue, search existing open and closed issues.
- Before closing an issue, confirm the fix is merged or pushed to `master`.
- When closing issues, include the shipping commit or PR.
- Do not commit ignored deployment artifacts.
- Do not force-push or rewrite shared history unless explicitly requested.

Useful commands:
- `gh issue list --repo MaxSchollum/ActivityChronio --state open`
- `gh issue view <number> --repo MaxSchollum/ActivityChronio`
- `gh issue close <number> --repo MaxSchollum/ActivityChronio --comment "Shipped on master in <commit>."`
- `git status --short --branch`
- `git log --oneline --decorate -n 10`

---

## Documentation Rules

- `docs/PRD.md` is the product source of truth.
- `docs/PM_PROMPT.md` is the product-manager thread bootstrap.
- Update docs when shipped behavior changes materially.
- Keep V1/V2 status accurate.
- Do not let GitHub issue state and docs drift apart.

Because `docs/` is ignored by `.gitignore`, use `git add -f docs/PRD.md docs/PM_PROMPT.md` when intentionally committing doc changes.

---

## Output Style

- Be concise.
- Be concrete.
- Lead with status and next action.
- Use file paths and issue numbers.
- Do not provide generic explanations unless requested.
- When work is incomplete, say exactly what remains and why.
