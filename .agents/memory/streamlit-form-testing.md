---
name: Streamlit form testing
description: A Streamlit AppTest behavior to account for when testing form submissions.
---
In Streamlit AppTest, form field edits are buffered. Do not call `.run()` between changing a field inside a form and clicking its submit button; an intermediate rerun restores the previous value. Set the field and submit before the next run.

**Why:** AppTest models the form's submit boundary; an intermediate script rerun does not commit the staged values.

**How to apply:** For AppTest coverage of parent forms, stage widget values and submit the form in the same test interaction batch, then inspect saved state after the resulting rerun.

For page-level `MagicMock` tests with multiple buttons, use a sequential `side_effect` instead of making every button return `True`; otherwise later actions such as removal can also fire after a save.

**Why:** A mocked Streamlit page evaluates subsequent controls in the same run, so a blanket truthy button mock can trigger unrelated destructive actions and obscure whether the intended save worked.

**How to apply:** When testing save flows that continue rendering after save, set button responses in render order and let persistence mocks apply the callback to a test state.

AppTest Markdown element `repr` does not include its rendered text; assert against each Markdown element's `value` instead.

**Why:** A test that searched the full app representation falsely reported visible text as missing.

**How to apply:** For rendered-text assertions, join `app.markdown` widget values rather than inspecting `repr(app.main)`.

`AppTest` renders tab contents into its widget tree but its `Tab` elements do not support selecting a tab. Interact with a widget by label or key without calling a tab-selection method.

**Why:** AppTest's tab API differs from browser-driven interaction APIs; assuming tabs are selectable causes tests to fail before exercising the underlying flow.

**How to apply:** Use the app's visible widget keys/labels for tab-contained controls, and assert the resulting state and rendered elements directly.
