# Product decisions and reasons

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
