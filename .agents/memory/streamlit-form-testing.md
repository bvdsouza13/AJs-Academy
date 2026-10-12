---
name: Streamlit form testing
description: A Streamlit AppTest behavior to account for when testing form submissions.
---
In Streamlit AppTest, form field edits are buffered. Do not call `.run()` between changing a field inside a form and clicking its submit button; an intermediate rerun restores the previous value. Set the field and submit before the next run.

**Why:** AppTest models the form's submit boundary; an intermediate script rerun does not commit the staged values.

**How to apply:** For AppTest coverage of parent forms, stage widget values and submit the form in the same test interaction batch, then inspect saved state after the resulting rerun.
