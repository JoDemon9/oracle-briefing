# Product decisions and reasons

[DEC-020 — Luna, sports and collapsible findings](https://github.com/JoDemon9/Claude-Briefing/blob/codex/luna-sports-collapsible-findings/decisions/DEC-020-luna-sports-and-collapsible-findings.md): requested recovery preserves all findings behind native disclosures, visible dated favourite headlines, full source/image/coverage gates and the separate Wire. The portal browser check now opens findings before checking full article text, verifies exact text and keyboard toggling with/without JavaScript, and retains compatibility with older saved snapshots. Source code, local/CI checks, main/Pages, actual prompts and actual model selection remain distinct. The source implementation is reviewed in Claude-Briefing PR #23; this portal snapshot is prepared separately and is not live until approved publication and exact verification.

The canonical decision history is maintained in [Claude-Briefing/DECISIONS.md](https://github.com/JoDemon9/Claude-Briefing/blob/main/DECISIONS.md), alongside the shared renderer and editorial specification. Read it before changing this portal. Do not maintain a second independently edited copy.

Current records:

- [DEC-004 — Whole-day overview](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-004-whole-day-overview.md): the user approved recommendation 1; reviewed points retain important stories from every participating slot.
- [DEC-005 — Reading value](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-005-reading-value.md): the user approved recommendation 2; 30-second findings, useful optional expansion and further reading when justified supersede word-count floors and mandatory counterarguments.

- [DEC-001 — Preserve the reasons behind fixes](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-001-decision-history.md): the user wants GitHub to retain what was fixed, why it was done and what future work must preserve.
- [DEC-002 — Compact market evidence](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-002-compact-market-evidence.md): reduce repeated mobile documentation rows while keeping evidence and timestamps accessible. Implementation is staged, not live.
- [DEC-003 — Market interpretation](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-003-market-interpretation.md): provide useful interpretation and Cyprus implications beyond a list of prices. Implementation is staged, not live.

For a meaningful fix, record the user need, reason, affected behavior, tradeoffs, preservation requirements, actual checks and publication state in the canonical history. Reference decision IDs in commits/PRs. A later explicit user request can supersede a record; retain its old rationale and link the new record. Do not reverse an accepted choice during an unrelated fix or treat an unapproved recommendation as a requirement.

[The newspaper review](https://github.com/JoDemon9/Claude-Briefing/blob/main/NEWSPAPER_REVIEW.md) is a proposed improvement backlog. Existing rules in AGENTS.md and OPERATIONS.md remain active, including historical URLs, complete daily snapshots, source times, privacy, accessibility and the independent Wire workflow.

Latest: [DEC-008 compact sports](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-008-compact-sports.md), [DEC-009 curated day](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-009-curated-daily-newspaper.md), [DEC-010 morning balance](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-010-morning-news-balance.md). Follow the canonical records for implementation and publication status.

[DEC-012 reading UI and explicit follow-ups](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-012-reading-ui-and-followups.md) records the latest approved UI changes; since-last-visit tracking remains deferred.

[DEC-013 backend reliability](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-013-backend-publication-reliability.md) records the six approved backend fixes. Follow the canonical BACKEND_OPERATIONS.md; implementation remains on review branches until merged and live verified.

[DEC-014 efficient editorial production](https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-014-efficient-editorial-production.md) consolidates runtime inputs, research/due-check/photo reuse and separates routine checks from maintenance. Keep real scheduled runs, Pro observations, code and live deployment status distinct.

DEC-015 deploys the reviewed publication safeguards and compact instructions alongside the 16 October recovery, retains current Wire data, and carries the repaired complete day. Canonical record: https://github.com/JoDemon9/Claude-Briefing/blob/main/decisions/DEC-015-production-recovery-and-editorial-quality.md . Publication/task verification is reported separately.

DEC-015 completion (16 October): the user explicitly approved deployment. Both repaired sites are on main and exact-byte verified; the recovered evening is included, all three daily tasks are enabled at their existing times, and the historical fourth task is unchanged. Canonical final evidence: https://github.com/JoDemon9/Claude-Briefing/blob/main/REPAIR_REPORT_2026-10-16.md . Wire data/cache/health files remain unchanged.

DEC-016 decoupled LLM content generation and CI testing (16 October): the user approved decoupling heavy deterministic testing from the ChatGPT action. ChatGPT focuses on research, source validation, and delivering schema-compliant content JSONs. Site compilation (build.py), schema validation, image preparation, and Playwright browser checks are executed by GitHub Actions CI on push. This eliminates container timeouts, reduces token usage by ~50%, and keeps strict quality gates intact in CI.

