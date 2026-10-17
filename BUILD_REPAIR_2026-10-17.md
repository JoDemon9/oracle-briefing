# Morning publication recovery — 17 October 2026

The user requested repair and retry after a failed build cleanup. The source
repository now stages outside the synchronised workspace on the same filesystem;
its full CI and exact 475-file Pages verification passed before portal sync.

Portal CI exposed two stale test assumptions: every day already has a substantive
update and the first Cyprus card always has analysis. DEC-005/014 explicitly allow
a first morning with provenance only and a factual card without useful extra
analysis. The reviewed source correctly renders the empty chronology and omits
that analysis. No news or analysis should be fabricated to satisfy a test.

The central browser test now requires exact source chronology/card preservation,
checks the nonempty message when no update exists, and checks analysis presence
against the source. Both empty/populated chronology fixtures run on every browser
test, including a negative missing-chronology case. Existing keyboard, source,
photo, snapshot fallback, no-JS, market and responsive checks remain. No renderer,
factual content, source/quote times, schedules or Wire files are changed.

All gates remain blocking. CI, main and exact live verification status are
reported separately in the publication records.
