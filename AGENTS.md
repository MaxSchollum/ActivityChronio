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

## Agent Context And Tooling

Different agent harnesses inject different context. Treat this file as the project-level operating contract, then layer the current tool's system instructions on top.

Common context agents may receive:
- Working directory and current branch.
- Git status at session start.
- Recent commits.
- Current date.
- Project memory files from the user's local agent profile.
- MCP/tool instructions and available skills.
- Deferred tools that can be loaded on demand.

Claude Code note:
- If a `CLAUDE.md` exists, Claude Code injects it as project instructions.
- This repo uses `AGENTS.md` as the shared project contract for Codex and other agents.
- If Claude-specific behavior is needed later, either create a thin `CLAUDE.md` pointing to this file or keep the content duplicated intentionally.

Subagent note:
- Subagents start cold. They do not automatically know the parent conversation.
- Brief each subagent with the issue number, repo path, branch/worktree, exact task, constraints, and expected output.
- Use subagents for bounded search, planning, or review. Do not ask multiple agents to edit the same files in parallel unless ownership is clearly split.

---

## Worktrees And Local State

Claude/Codex implementation sessions often run inside isolated git worktrees under:

`/Users/maxschollum/Library/Application Support/ActivityChronio/.claude/worktrees/`

This means:
- Edits in a worktree do not touch the main checkout until merged.
- Each worktree normally has its own generated branch, such as `claude/dazzling-curran`.
- A clean, unused worktree can be discarded without affecting `master`.
- Worktrees are good for parallel implementation, but final acceptance should verify what is actually merged to `master`.

Known local Claude reference files:
- `.claude/worktrees/dazzling-curran/1 PRD_Addendum.md`
- `.claude/worktrees/dazzling-curran/2 QA_Report.md`
- `.claude/worktrees/dazzling-curran/3 GitHub_Issues_Fix.md`

These were QA/PM artifacts from an earlier V1 session. They documented the stale-bundle deployment problem, a PRD addendum, QA findings, and issue text. They are useful historical references, not current product source of truth. The current source of truth is `docs/PRD.md`, `docs/PM_PROMPT.md`, GitHub issues, and `master`.

Do not commit `.claude/` worktree files unless explicitly asked.

---

## Operating Model

Use three separate Codex threads when possible. Keep the responsibilities clean.

### 1. Feedback / Product Thread

Purpose: convert Max's UX/product feedback into clear GitHub issues and keep product docs current.

What Max gives this thread:
- Raw UX feedback, often dictated or casual.
- Screenshots or descriptions of confusing/broken states.
- Product direction, such as "make this feel more like Timing.app."
- Observations from using the live app.

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

What Max gives this thread:
- One issue number or a batch of issue numbers.
- Optional constraints such as "keep the diff small" or "reuse the existing toast pattern."

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

Concrete implementation workflow:
1. Read each ticket with `gh issue view <number> --repo MaxSchollum/ActivityChronio`.
2. Explore the relevant code before editing, especially `Chronio.vue`.
3. Implement in the assigned branch/worktree only.
4. Run `npm run build` inside `aw-server/aw-webui`.
5. For live local validation, run `make deploy-webui` from the repo root and hard-refresh `localhost:5600`.
6. Browser-check visible UX changes when the app is available.
7. Commit and push the implementation branch.
8. Comment on each implemented issue that it is complete and ready for review.

Handoff output:
- Issue numbers implemented.
- Files changed.
- Verification performed.
- Known risks or follow-up tickets needed.

### 3. Acceptance / Verification / Merge Thread

Purpose: act as the final gate before work becomes `master`.

What Max gives this thread:
- "Review and merge this."
- A branch, worktree, PR, or issue batch.
- Optional concerns, such as "check that drag still works."

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

Acceptance workflow:
1. Identify the implementation branch/worktree and related issue numbers.
2. Read the issue bodies and acceptance criteria.
3. Review the diff against user intent and adjacent flows.
4. Run `npm run build`; run additional tests or browser checks when relevant.
5. Merge to `master` only after verification passes.
6. Push `master`.
7. Update docs if shipped behavior changed.
8. Close GitHub issues with a comment like `Shipped on master in <commit>.`

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

## Local Run And Preview

Useful local ports and launch config:
- `localhost:5600`: Flask AW server / real app.
- `localhost:27180`: Vue dev server.
- `.claude/launch.json`: local launch definitions for Vue, Flask, tray app, and watchers.

Build/deploy behavior:
- `npm run build` in `aw-server/aw-webui` builds the web UI into `aw-server/aw-webui/dist/`.
- `make build-webui` runs the web UI build.
- `make deploy-webui` builds and copies `dist/` into `aw-server/aw_server/static/` so an already-running Flask server can serve the latest bundle.
- After deploy, hard-refresh the browser with `Cmd+Shift+R`.
- Do not commit `aw-server/aw-webui/dist/` or `aw-server/aw_server/static/` unless explicitly requested.

Historical note:
- The V1 stale-bundle issue came from the running server serving an older static bundle. When a UI fix appears missing locally, first confirm the built bundle was deployed and the browser was hard-refreshed.

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
