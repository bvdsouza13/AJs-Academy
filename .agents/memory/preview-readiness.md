---
name: Streamlit preview readiness
description: Avoid mistaking the initial blank Streamlit shell for a failed application.
---
The first preview capture after an Academy restart can show a blank Streamlit shell even when the server is healthy; the rendered page may appear only after startup settles.

**Why:** Both the entry-flow browser check and subsequent visual checks observed this delay, with the actual welcome rendering successfully afterward.

**How to apply:** Distinguish readiness from failure before changing code or restarting again. Use a visible heading as the browser readiness signal. If a settled preview shows an older design, check actual file contents and the working diff before assuming browser caching.
