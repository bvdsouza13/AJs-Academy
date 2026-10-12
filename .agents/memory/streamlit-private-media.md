---
name: Streamlit private-media boundary
description: Why private object storage plus a Streamlit password form is not sufficient authorization for served media.
---
Treat Streamlit media and download URLs as a separate authorization boundary
from the Academy's script-level role checks.

**Why:** An isolated test of the installed Streamlit media route returned
synthetic private bytes without auth cookies. Script-level login gates prevent
rendering new content but do not authorize each request to an already-issued
media URL. Platform-private access also does not distinguish parent from child.

**How to apply:** Before approving private publishing, verify anonymous and child
requests to copied media and financial download URLs, including Range requests
and post-logout access. Do not infer safety from private object storage, a login
screen, or a hard-to-guess URL. Never use real family files as audit fixtures.
