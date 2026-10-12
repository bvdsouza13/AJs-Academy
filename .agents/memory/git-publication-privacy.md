---
name: Git publication privacy
description: Privacy boundary for the initial GitHub publication and subsequent code updates.
---

The user chose a new private GitHub repository named `ajs-academy`, starting from a clean code-only snapshot rather than publishing the existing Replit Git history.

**Why:** Historical commits contain family account CSV uploads even though the current tracked tree excludes them. Ignore rules do not remove files from old commits. A normal push of the existing history could disclose those uploads.

**How to apply:** Preserve Replit's existing history and internal remotes. Publish and update through an isolated, reviewed code-only history that excludes family uploads, recordings, saved application data, secrets, conversation archives, and agent memory. Do not later push the original workspace branch into the external repository.
