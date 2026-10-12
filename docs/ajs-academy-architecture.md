# AJ’s Academy
## Architecture and Component Guide

Companion to the system architecture diagram

Prepared October 12, 2026

### Purpose and scope

This document explains the architecture of AJ’s Academy for a parent, product owner, or developer taking over the project. It describes each major component in the canvas diagram, the information it handles, and how the components work together.

It is based on the repository inspected for this document. It is not a new security audit, a live deployment verification, or a claim that every proposed integration is finished. Other agents may be developing features in separate branches.

The diagram combines existing components with architectural safeguards. In particular, “authorize each media fetch” is a required safeguard, not a completed guarantee. The unattended-screen lock and copied-media-link protections remain separate work.

### Reading guide

1. System overview and diagram key
2. People, access, and sessions
3. Streamlit application and parent controls
4. The nine product features
5. Persistent data and private media
6. Temporary inputs and AI processing
7. Public sources and external websites
8. End-to-end data flows
9. Security boundaries and limitations
10. Operations, testing, and future development

## 1. System overview and diagram key

AJ’s Academy is a private, single-family learning and routine-management app. AJ mainly uses an iPad. A parent configures content, controls rewards and AI permissions, and manages private financial reports.

The current application is a Python Streamlit application, not a React frontend backed by a separate Academy REST API. Streamlit renders controls in the browser and runs page logic on the server. Browser interactions trigger reruns of the Python script, while session state keeps temporary values between those reruns.

The main connections are:

- Family browser → Streamlit application: sign-in, navigation, forms, uploads, and results.
- Streamlit application ↔ PostgreSQL: persistent family settings and records.
- Streamlit application ↔ private object storage: uploaded diary pictures and soccer-practice videos.
- Streamlit application ↔ AI service: explicitly requested transcription, story preparation, and social-context interpretation.
- Streamlit application → public sources: selected market data, news, and newsletter retrieval.
- Family browser → external websites: reviewed sources, retailer searches, school pages, and AJ’s arcade.

The diagram uses blue and violet for people and application components, green for stored family data, orange for external processing, and yellow/red for temporary information and privacy requirements. Arrows summarize logical flows; they are not separate network APIs or microservices.

## 2. People, access, and sessions

### 2.1 AJ’s iPad and child view

The child view provides large visual choices, simple instructions, and a small number of actions at a time. It includes the nine feature areas and a shared points display.

AJ can complete routines, write a diary, select drills, upload practice, build a wishlist, read approved stories, and use supportive social tools. Financial screens emphasize percentage progress and understandable goals rather than parent-only dollar amounts.

The browser does not directly query PostgreSQL or receive database credentials. It displays the interface and sends interactions to the Streamlit server. Microphone and camera use also depend on browser/device permissions.

### 2.2 Parent view

The parent uses the same application with a different role, rather than a separate administration product. Parent-only areas include account reports, planning assumptions, point values, reward decisions, video approvals, AI/privacy settings, and social-interest cards.

The parent can review every diary entry. The app states this to AJ so the diary is not presented as a secret space. Saved social phrases are also parent-visible.

### 2.3 Authentication and role checks

The current access model is a single-family prototype gate. It is not individual multi-user identity management, enterprise SSO, or a multi-family tenancy system.

A new child session requires parent authorization as well as the child login. Parent access is separately checked. Authentication attempts are tracked in PostgreSQL, with a temporary lockout after repeated failures. Credentials and provider configuration are read on the server; their values do not belong in documentation or browser code.

Switching from parent to child clears the session before establishing the child view. Sign-out clears session state. Parent-only report functions also check the role before presenting their contents.

### 2.4 Session expiry and its limit

The app records a last-active time and checks a 30-minute inactivity threshold when Streamlit executes again. An expired session must sign in again.

This is not an automatic screen blanker. A parent report already visible on an untouched iPad can remain visible until a new interaction/rerun. An automatic parent-screen lock is separate planned work. Session clearing also does not establish that previously emitted media/download URLs have been revoked.

## 3. Streamlit application and parent controls

### 3.1 Application shell

The main entrypoint is artifacts/ajs-academy/app.py. It establishes the theme, login gate, role, navigation, loaded family state, and page dispatch.

Home is the landing/navigation page, not an additional tenth feature. The feature suite contains Investments, College, Diary, Reminders, Soccer, LEGO, AI Discoveries, Arcade, and Social Skills.

The repository also contains an API-server artifact and residual frontend scaffolding. Those should not be mistaken for the active Academy request path: the Academy artifact’s configured service runs Streamlit directly.

### 3.2 Shared business logic

The application calls focused Python modules for persistence, financial calculations, source retrieval, and visual elements. These are modules within one application process, not independently deployed services.

- store.py: database access, mutations, authentication checks, points, and object-storage access.
- finance.py and account_performance.py: export parsing, planning calculations, statement reconciliation, and supported performance calculations.
- finance_views.py: parent statement interface and child-safe performance presentation.
- content.py: public source retrieval, curated drills, transcription, AI story preparation, and social helper functions.
- schools.py: school-cost baseline information used by the planner.
- visuals.py: shared illustrations, theme, and presentation helpers.

### 3.3 Parent control layer

Parent controls are the policy layer for the child experience. Settings decide which videos can play, whether transcription/social AI is enabled, how chores earn points, which rewards are available, and when the arcade link is unlocked.

These decisions are stored in the family state and read by the appropriate feature. They are not a universal filter over the rest of the internet: external websites retain their own advertisements, tracking, content, and access controls.

## 4. The nine product features

### 4.1 Investments: custodial account

The investment area separates financial evidence from education and projections. Parents upload supported activity exports and provide statement evidence or confirmed balances. AJ sees simple goals such as a first home, a yearly vacation, or a car.

An activity export is not automatically a complete holdings ledger. Opening positions, transfers, splits, exchanges, cancelled trades, and missing history can change the interpretation. A list of symbols from the export does not prove those securities are still owned.

The financial engine supports a normalized statement-evidence route and reconciliation checks. Account performance must remain conditional on adequate evidence; it is not broker verification or tax advice. Broker-specific import improvements may exist in separately implemented work and should be verified in the destination checkout before being described as deployed.

Market history retrieved through yfinance is presented as adjusted market-price change, not the family’s personal account return. Personal return must account for the timing of cash flows and reliable account valuations.

The age-21 planner uses a parent-confirmed balance, an inflation-adjusted target, and illustrative return assumptions. The inspected implementation uses a 13-year horizon and month-end contributions. It does not model taxes or fees, and returns are not guaranteed.

### 4.2 College: 529 savings

The college feature combines an uploaded 529 snapshot with a selected school, a residency scenario, and editable full-cost assumptions. AJ explores schools and sees progress; parents see the detailed numbers.

The model projects each of four attendance years separately using a college-cost inflation assumption. It then estimates monthly contributions needed to fund the projected cost by enrollment. Return scenarios are assumptions, not predictions.

The current planner assumes the full four-year amount is available at enrollment and does not add further investment growth during college. It separates contributions from growth and does not treat internal fund conversions as new savings.

School budgets are source-linked baselines and parent-edited assumptions, not a guaranteed live university-pricing API. Tuition, fees, housing, meals, books, travel, and other costs should be checked for the intended year. Residency eligibility and whether an expense qualifies for 529 treatment are separate questions.

### 4.3 Diary

The diary asks three questions: the best part of the day, what felt sad or unhappy, and what AJ looks forward to tomorrow. Typed answers remain editable. Parent-enabled transcription turns a deliberately submitted audio clip into text that AJ can review before saving.

Saved answers go to PostgreSQL. Uploaded photos are processed and stored separately in object storage; the diary record holds their references. Original transcription audio is not deliberately saved as a diary attachment.

The weekly view reports participation and displays AJ’s own words. It is not a mental-health assessment or a measure of emotional development. In the inspected app, parents can delete diary entries and their referenced photos.

### 4.4 Reminders, points, and rewards

Visual routines cover morning preparation, after-school tidying, evening care, and extra household help. Parents choose point values. The system stores completion records and a points ledger rather than only a mutable points total.

Award keys prevent the same routine/day event from being awarded twice. The balance is the sum of ledger entries. Points carry over instead of resetting at the end of each week.

A reward request is not an immediate purchase or deduction. The parent approves it, the system rechecks the balance, and an approved redemption creates a negative ledger entry. A declined request does not deduct points.

### 4.5 Soccer

Learn offers a small curated drill selection, visual cues, and videos that require parent approval. Play accepts an uploaded practice recording. Follow retrieves source-linked soccer headlines.

Practice capture currently means recording in the iPad Camera app and uploading the result, not an embedded practice recorder. Files are stored in object storage with a practice record in PostgreSQL. Saving practice can award 50 points once per day, regardless of additional uploads that day. The app rewards participation and does not grade technique.

The upload limit is 40 MB. Accepted extensions do not guarantee that every video codec will play on every iPad. YouTube may show advertisements or recommendations even for an approved video.

### 4.6 LEGO

LEGO connects interests to a wishlist and parent-approved rewards. A parent can set point prices using the family’s conversion settings and approve redemption.

The inspected app provides retailer/search links and wishlist handling. Live price tracking and “best deal” comparisons are not connected. The diagram’s reference to deals describes a product direction, not a completed price-comparison service. No purchase happens automatically.

### 4.7 AI Discoveries

The parent story studio can retrieve public Batch article links, extract supported article text, and ask AI for a child-friendly story and hands-on challenge. The parent reviews and edits the draft before approving it for AJ.

Gen Academy material can be supplied as a public source link and excerpt. LinkedIn is not automatically monitored. A parent should not paste private information into the drafting service.

Approved stories are persistent records. Drafts remain temporary until approved. The requested weekly routine is parent-driven in the inspected implementation; an autonomous weekly publishing scheduler is not implied.

### 4.8 Arcade

The arcade is an external Lovable-hosted game. The Academy app stores unlock settings and controls whether its own link is available. Access is primarily a parent-approved weekend privilege, with an explicit weekday exception available.

It never costs points. Locking the Academy link does not prevent direct access to the external game URL, and it does not control that site’s session or data handling.

### 4.9 Social Skills

Help me uses selected feelings, a short situation, and a requested support to generate editable language for a child or an adult. This basic phrasing uses local templates and works without AI. Optional voice input uses transcription.

What might they mean accepts typed words, an image of written context, or an optional audio clip. Parent settings govern AI/audio use. For another person’s audio, the UI asks AJ to confirm the speaker was told and agreed; submission checks that confirmation. This is a self-attested permission control, not technical proof that consent existed.

The AI provides a literal reading, a possible interpretation, a question to ask, and a trusted-adult next step. It must not claim certainty about intent, diagnose people, infer feelings from faces, or normalize threatening content.

Conversation practice uses “ask, listen, share” cues and parent-managed interest cards. AJ can explicitly save useful phrases. Those saved phrases persist and can be reviewed/deleted by parent and child. Raw social interpretation captures are not deliberately saved to the database or object storage.

## 5. Persistent data and private media

### 5.1 PostgreSQL family state

The current persistence model keeps the family’s application state in a JSONB document in academy_state. A separate academy_auth_attempts table tracks authentication failures and lockouts.

State includes settings, point events, completions, diary entries, finance records, practice metadata, wishes, rewards, requests, approved stories, and social cards/phrases. Media bytes live elsewhere.

Mutations read the family row with a database lock, apply a change, and write it back within a transaction. This serializes simultaneous updates and helps avoid lost points or duplicate redemption effects.

This is practical for one family but is not a multi-tenant architecture. As records grow, rewriting a shared state document can become a bottleneck. A future multi-family system would need explicit family membership, record ownership, authorization, and a migration plan; adding more passwords would not be enough.

### 5.2 Private object storage

Object storage holds larger binary assets such as photos and videos. The database stores an object reference and display metadata rather than embedding the bytes in every state update.

Uploads use generated object paths. Diary photos are decoded, resized, and re-encoded as JPEG, which removes original EXIF location metadata. This does not remove names or other private details visibly present in the picture.

Database writes and object uploads are separate operations, not one atomic transaction. An upload that succeeds before a later database failure can leave an unreferenced object. Cleanup and retention policies should account for this.

### 5.3 Storage privacy is not delivery authorization

The app downloads private object bytes server-side and gives them to Streamlit media controls. Streamlit may then serve those bytes through its own generated media URLs. Financial download buttons can use the same delivery mechanism.

The project’s release checklist records a handler-level finding: such URLs can bypass the app’s role/session gate. A private deployment access gate is an additional boundary, but does not establish parent-versus-child authorization for an already issued link.

Therefore, the diagram’s “authorize each media fetch” label is a requirement still needing hardening. Private bucket paths, long random URLs, and sign-out are not substitutes for per-request authorization.

## 6. Temporary inputs and AI processing

### 6.1 Streamlit session state

Temporary state holds navigation, draft answers, selected drills, unapproved AI stories, and social interpretation inputs/results. It survives a normal Streamlit rerun but is not the app’s durable database.

“Not saved” means not deliberately persisted by the application. It does not mean data never exists in browser/server memory, never travels over the network, or cannot be retained by an external provider under its own policies.

### 6.2 Replit AI Integrations and OpenAI

The inspected client sends OpenAI-compatible requests through the configured Replit AI integration endpoint. It uses transcription for speech and language/image-capable requests for story drafting and social interpretation.

These are external processing calls. The consent boundary concerns the content sent, not merely whether a microphone permission dialog appeared. A parent enabling a feature and AJ choosing to submit are distinct steps.

Social images are resized and re-encoded before transmission. Social responses use a structured schema and required-field checks. Source material is treated as untrusted input. These measures improve predictability but cannot guarantee that every AI answer is correct or safe.

If AI is unavailable, the app should show a clear error rather than fabricate an interpretation. Typing, local help phrases, conversation cues, and asking a trusted adult remain useful alternatives. Provider retention and contractual terms must be reviewed separately; this document makes no zero-retention claim.

## 7. Public sources and external websites

### 7.1 Market data and news

yfinance supplies historical market prices. Google News RSS supplies searched headlines for stocks and soccer. These providers are not custodians of the family’s account and do not verify account balances or personal returns.

Public headlines may contain adult topics. A source link and a parent-reading prompt are not equivalent to a fully moderated news feed. Retrieval failures should remain visible, and unavailable data should not be silently replaced with invented facts.

### 7.2 Educational and curated sources

The Batch is a supported public source for story preparation. School websites support parent cost research. YouTube drills and LEGO retailer searches are curated links or embeds, not owned content services.

Parents should review suitability and source dates. External content, prices, availability, advertisements, and recommendations can change after approval. Opening a link takes the browser into another operator’s privacy and security environment.

## 8. End-to-end data flows

### 8.1 Completing a routine

AJ checks a task → the server verifies that day/task has not already been completed → a transaction records completion and the configured point award → the next render shows the updated ledger-derived balance.

### 8.2 Saving a diary day

AJ types or requests transcription → AJ reviews the text → selected pictures are validated, resized, and uploaded → the diary text and object references are saved in PostgreSQL → history loads text from the database and media through the storage/delivery path.

### 8.3 Understanding a confusing phrase

AJ supplies words or permitted media → the app checks parent settings and the required audio confirmation → audio is transcribed if present → relevant text/image content is sent for interpretation → a structured response is checked and displayed as possibilities → the app clears capture widgets and retains the answer temporarily, not as a durable social history.

### 8.4 Producing a financial report

The parent uploads a supported export/evidence file → parsing validates the expected format → statement reconciliation checks consistency → parent reports distinguish evidence, contributions, and returns → child views receive an intentionally reduced presentation. Public market data remains a separate contextual comparison.

### 8.5 Approving a story or reward

For a story, a parent reviews an AI draft before saving an approved record. For a reward, a parent reviews the request and the database transaction checks affordability before recording a deduction. Neither AI generation nor a child’s request is itself approval.

## 9. Security boundaries and limitations

### 9.1 Current controls

- Parent authorization for a new child session and parent-role checks for management/reporting.
- Server-side credentials, authentication-attempt tracking, and session clearing on sign-out/handoff.
- Separate persistent state and private binary storage.
- Parent controls for transcription, social AI, content, rewards, and arcade access.
- Deliberate social phrase saving rather than automatic retention of every interpretation.

### 9.2 Open or conditional safeguards

- Copied media and financial-download links need role/session-aware authorization independent of the Streamlit page gate.
- Idle parent screens do not automatically blank merely because 30 minutes have elapsed.
- Session-only processing is not a guarantee about external AI retention.
- Speaker consent is asserted by the user; the app cannot prove it.
- HEIC photos and universal video codec compatibility are not established.
- Parent-approved embeds and public headlines are not fully controlled or fully moderated content.
- Sanitizing known export fields does not prove every free-text value is free of personal information.

The release checklist records previous deployment and device-check evidence. This guide does not re-verify that evidence or assert the current deployment has changed. Keep those historical results separate from a fresh production security review.

## 10. Operations, testing, and future development

### 10.1 Runtime and configuration

The Academy artifact runs the Streamlit service configured in artifacts/ajs-academy/.replit-artifact/artifact.toml. Its development command runs the existing workspace package; the build command checks Python compilation.

Schema definitions live in schema.sql. The app should not create or alter its schema opportunistically at startup. Treat environment selection, schema changes, and production data handling as deliberate operations, not as side effects of viewing a page.

Changes to this guide do not restart, test, or deploy the application. Secrets must be managed outside the document, and production publishing needs explicit approval.

### 10.2 Verification strategy

Existing focused tests cover financial calculations/reconciliation, social-helper logic, and session safety. Streamlit AppTest can exercise child and parent flows with synthetic state. Such tests do not prove real iPad capture behavior, provider accuracy, or media-URL authorization.

Before releasing a relevant change, verify the corresponding layer: calculations with deterministic tests; role controls with child/parent tests; uploads with denied-permission and invalid-file cases; private delivery with signed-out, child, parent, expired-session, and copied-link requests; AI with safe failures and inappropriate-content scenarios.

Use synthetic data for tests and redact logs. Never obtain “test evidence” by publishing family records or copying secret values into reports.

### 10.3 Extension points

Near-term work already identified includes copied-media-link protection, unattended parent-screen protection, easier monthly statement additions, visual social scenarios, personalized calming choices, and live LEGO/news routines. These are extensions or hardening work, not additional layers already implemented in the diagram.

Preserve the current child/parent split and low-pressure experience when extending the app. Prefer deterministic calculations for finance and points; use AI for optional language assistance where uncertainty can be made clear. Do not move account reconciliation, reward authorization, or access decisions into an LLM.

### Repository reference

The source files used for this guide are app.py, store.py, finance.py, account_performance.py, content.py, schema.sql, and PRIVATE_RELEASE_CHECKLIST.md within artifacts/ajs-academy. The artifact configuration identifies the active Streamlit runtime. Related presentation modules are listed in section 3.

### Glossary

- Authentication: checking who is signing in.
- Authorization: checking whether that person may perform a specific action or read a resource.
- Session: temporary state associated with a browser’s active use of the app.
- JSONB: PostgreSQL’s structured JSON storage format.
- Ledger: a sequence of events, such as point awards and deductions, from which a balance can be calculated.
- Reconciliation: checking that financial records agree with balances and supporting evidence.
- Object storage: storage designed for binary files such as photos and videos.
- Trust boundary: a point where data or control passes to a component with different permissions or an external operator.
