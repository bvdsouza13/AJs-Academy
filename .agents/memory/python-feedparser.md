---
name: Python feed parsing in this runtime
description: Avoid fatal path probing when parsing downloaded RSS bytes.
---
Pass downloaded RSS bytes to feedparser through `io.BytesIO`, not as the bare argument.

**Why:** Bare response bytes caused the runtime to terminate with `get_target_path: path exceeds MAX_PATH` during feed parsing. A direct request returned HTTP 200 first, proving this was parsing rather than network access. The parser appears to probe the content as a filename.

**How to apply:** Use an explicit stream for downloaded feed content. Do not interpret this process-level failure as a remote service outage or disable TLS verification.
