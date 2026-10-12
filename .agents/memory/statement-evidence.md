---
name: Statement evidence boundaries
description: Why account performance uses a separately reviewed statement ledger rather than treating broker activity as holdings.
---
Treat custody activity exports as incomplete evidence, never as current holdings. A parent-reviewed normalized ledger plus opening tax lots and dated statement positions/balances is the supported source for personal performance.

**Why:** The supplied custody records describe transactions, not a holdings statement. Missing opening positions and corporate actions can make plausible-looking net quantities and returns wrong.

**How to apply:** Preserve the distinction between exported activity, parent-entered planning assumptions, and reconciled statement performance. Reject unsupported actions or mismatched checkpoints rather than estimating missing values. Describe reconciliation as consistency with parent-supplied statements, not independent broker verification.

Import failures should leave previously saved, reconciled evidence intact, rather than replacing it with a draft that hides existing results.

**Why:** Parents need to investigate incomplete broker exports without losing their last reviewed statement history. Preview validation is a safer boundary than saving first and suppressing metrics later.

**How to apply:** Keep preparation separate from persistence; require successful reconciliation and confirmation tied to the current preview before replacing saved evidence.
