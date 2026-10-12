# Private release verification

## Status: private deployment verified; iPad checks reported passed

Checked 2026-10-12. The user changed publishing visibility; platform metadata
now reports a successful private deployment. An unauthenticated request to the
production root received a 307 redirect to Replit's access gate. No credentials
or family data were accessed.

### Verified

- `schema.sql` defines `academy_state` and `academy_auth_attempts`.
  Read-only information-schema queries in development and production confirmed
  the expected columns, types, and nullability. This is not a data reconciliation
  or a complete constraint comparison. No DDL was necessary.
- No startup DDL was found in the Academy persistence or entrypoint.
- Five isolated Streamlit AppTest checks pass:
  signed-out sessions do not load family state; sessions older than 30 minutes
  require login on rerun; parent-to-child handoff clears parent drafts; the child
  must reauthenticate to access parent management; sign-out clears session data;
  child login first requires parent approval.
  Run: `python -m unittest discover -s artifacts/ajs-academy -p test_session_safety.py -v`.
  These tests mock state loading and use no real passwords or family data.
- The development workflow starts cleanly.
- The user reports that all iPad checks requested in chat passed: Safari
  microphone/transcription, photo and practice-video upload/playback, both
  orientations, parent-to-child handoff, and the 31-minute idle check. This is
  user-reported device testing, not independently captured device evidence.

### Remaining privacy limitation

1. **Media URLs bypass the app's role/session gate.** The installed
   Streamlit 1.65.0 media route was exercised in isolation with synthetic bytes:
   an HTTP request with no auth cookies returned 200 and the bytes. Its response
   had no Cache-Control header. The route also serves `st.download_button`
   content, including financial exports. This is a confirmed handler-level
   finding, not evidence that any real family URL has leaked. Actual production
   private media was not fetched. The Replit private access gate blocks
   unauthenticated outside requests, but does not establish role-specific access
   to a copied media link for someone admitted to the deployment.
   Guess-resistant URLs are not authorization. Do not claim app sign-out or
   handoff revokes previously emitted media links.
2. **Camera-format support is limited.** Photos accept PNG/JPEG/WebP, not HEIC;
   conversion behavior from an iPad's photo picker is unverified. Practice
   accepts MP4/MOV/WebM by extension, without codec conversion. A successful MOV
   upload does not prove playback across other iPad models/codecs. The user
   reports their iPad upload/playback check passed. Practice recording means
   recording in the iPad Camera app and then uploading, not an in-app recorder.
3. An active Academy page checks for idle expiry every five seconds and returns
   to the authorization screen when the 30-minute timeout is reached. The
   timeout is also checked at the start of each full app run.
4. Automated signed-out screenshot captured only the Streamlit shell; it is not
   authenticated visual evidence. The user reports checking both iPad
   orientations directly.

## Safe publishing procedure

1. Keep the existing private deployment access restriction in place; do not
   change it to public. Reference:
   https://docs.replit.com/features/publishing/private-deployments
2. For Replit-managed PostgreSQL, review and approve the schema diff in Publish.
   Do not add startup DDL, build-time migrations, or a direct production migration
   script. If changing to an external database, first explicitly confirm that
   target and its migration procedure.
3. Review production secret configuration through the workspace's secrets UI,
   without copying values into chat or documentation.
4. Do not assume development financial imports were copied. Verify the intended
   statement evidence in the production parent portal and reimport explicitly
   if necessary. Do not select a whole-database overwrite as a shortcut.
5. Address role/session authorization for copied media and download URLs
   (including Range requests) before claiming that app-level access controls
   protect private media.
6. Verify automatic idle locking on the deployed iPad after app or Streamlit
   runtime upgrades.

## Required real-device evidence

The user reports all requested iPad checks passed on 2026-10-12. Device model
and iPadOS/Safari versions were not provided. No family data was requested.

| Check | Acceptance evidence |
|---|---|
| Microphone permission and transcription | User reported passed; details of denied-permission recovery not separately provided. |
| Photo upload | User reported passed; HEIC-specific behavior remains unverified. |
| Practice capture/upload and playback | User reported passed on their iPad. Recording is via Camera app, followed by upload. |
| Portrait/landscape | User reported passed in both orientations. |
| Handoff and idle timeout | User reported passed for parent-to-child handoff and the requested 31-minute check. |
| Copied media/download URL authorization | Not verified on production. Isolated handler test shows no app-level auth; private deployment gate blocks outside unauthenticated requests. |

The iPad behavior and private deployment checks are complete by user report and
platform verification. Keep the media authorization finding visible as a
separate security limitation; AppTest and the platform access gate do not
provide role-specific authorization for already-issued media links.
