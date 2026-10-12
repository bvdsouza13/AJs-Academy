# AJ’s Academy: Code and Data Storage Reference

**Code layout, important functions, and where information is stored**  
Repository review: October 12, 2026

## At a glance

AJ’s Academy is currently run as one Python **Streamlit** application. The configured entry point is `app.py`; it renders the family-facing screens and calls Python modules for finance, persistence, imports, content, and illustrations.

The Academy does **not** have a separate SQL table for every feature. Its PostgreSQL schema has two real tables. Most feature records are fields inside one JSONB document in `academy_state`; larger uploaded media files are held in private object storage. This distinction matters when reading the tables below.

```text
Browser / iPad
     │ Streamlit controls and uploads
     ▼
app.py ─── finance/import/content/visual modules
     │
     ├── PostgreSQL: academy_state JSONB + academy_auth_attempts
     ├── Object storage: photos/videos (referenced from JSONB)
     └── External services: AI, market/news sources, linked websites
```

The React/Vite files in `src/` are auxiliary starter scaffolding in this artifact. The artifact’s configured run command launches Streamlit with `app.py`, not that React frontend.

## 1. Code-file layout

| File or path | What it contains | Runtime role |
|---|---|---|
| `app.py` | Streamlit setup, login gate, navigation, child feature screens, and parent portal. | **Active application entry point.** |
| `store.py` | PostgreSQL reads/writes, default family state, role authentication, points ledger, redemption, and object-storage operations. | Active persistence and shared business logic. |
| `schema.sql` | Definitions of `academy_state` and `academy_auth_attempts`. | Actual PostgreSQL schema; apply deliberately, not at app startup. |
| `finance.py` | Broker export parsing, college projections, contribution summaries, activity-based position summaries, and market-history lookup. | Active finance calculations and import helpers. |
| `account_performance.py` | Normalized statement CSV format, validation, FIFO reconciliation, dated account history, allocation, gains, and money-weighted return. | Active evidence-based account performance engine. |
| `finance_views.py` | Parent statement-evidence interface and child-safe account-performance display. | Active finance UI/report layer. |
| `statement_import.py` | Fidelity/Schwab activity normalization, row-by-row issues, duplicate checks, statement review, and evidence parsing. | Active broker import logic; unsupported activity is not silently inferred. |
| `statement_import_views.py` | Streamlit upload, broker-column mapping, review preview, supporting evidence, and readiness checks. | Active parent-only import preparation UI; does not itself save. |
| `content.py` | AI client, transcription, social-help text, cautious social interpretation, news retrieval, The Batch parsing, story simplification, and drill definitions. | Active content and external-service helpers. |
| `schools.py` | Dated school-budget baselines and notes for planning scenarios. | Active source-linked planning defaults, not live prices. |
| `visuals.py` | Theme, SVG illustrations, hero blocks, and welcome visuals. | Active shared Streamlit presentation helpers. |
| `test_account_performance.py` | Finance reconciliation, broker-import, and child-display tests. | Tests; not part of request handling. |
| `test_session_safety.py` | Isolated AppTest coverage for sign-in, expiry-on-rerun, handoff, and sign-out behavior. | Tests; uses mocked family state. |
| `test_social_skills.py` | Local phrasing and social-AI input/response validation tests. | Tests; provider calls are mocked where appropriate. |
| `PRIVATE_RELEASE_CHECKLIST.md` | Recorded private-release checks, reported device checks, and identified media/session limitations. | Operational documentation; review its date/status before relying on it. |
| `package.json` | Workspace scripts for Streamlit development/serve and Python compilation, plus scaffold frontend dependencies. | Active workflow launcher; frontend dependencies are not the Academy request path. |
| `.replit-artifact/artifact.toml` | Artifact metadata, preview route, service port, and configured build/run commands. | **Confirms Streamlit is configured as the active runtime.** |
| `src/App.tsx` | Starter React shell and placeholder home screen. | Auxiliary Vite/React scaffold; not the current Academy UI. |
| `src/main.tsx` | React frontend bootstrap. | Auxiliary Vite/React scaffold. |
| `src/index.css` | Tailwind and starter frontend theme styles. | Auxiliary Vite/React scaffold. |
| `vite.config.ts` | Vite frontend build/dev configuration. | Auxiliary Vite/React scaffold. |
| `tsconfig.json` | TypeScript compiler settings for the auxiliary frontend. | Auxiliary frontend configuration. |
| `components.json` | UI generator/component conventions for the auxiliary frontend. | Auxiliary frontend configuration. |
| `index.html` | HTML shell for the auxiliary Vite frontend. | Not the Streamlit page template. |
| `public/favicon.svg`, `public/robots.txt` | Static icon and crawler instruction for the auxiliary web scaffold. | Static assets; not Academy data storage. |

### Run path in plain language

The Academy artifact configuration starts `python -m streamlit run app.py`. `app.py` imports the other Python modules directly. Its calls to `store.load()` and `store.change(...)` use PostgreSQL; media helpers call object storage; selected features call external services. The Vite React starter files are present in the same directory but are not what the configured Academy web service runs.

## 2. Most important functions

The functions below are selected because they connect the main UI to persisted data, financial calculations, imports, and external services. This is a maintainer’s orientation table, not an exhaustive API listing.

| Module | Function | In brief | Main inputs and result |
|---|---|---|---|
| `app.py` | `login(parent=False)` | Presents the parent or child sign-in flow and establishes the session role after authentication checks. | Form input → Streamlit session role/page. |
| `app.py` | `diary()` | Collects the three daily answers, optional transcription and photos; displays history and a participation/word summary. | User answers and media → saved diary record and media references. |
| `app.py` | `reminders()` | Shows visual tasks by time of day and records a daily completion. | Task selection → completion and points update through `store`. |
| `app.py` | `investments()` / `college()` | Renders child views for custodial savings and 529/school planning. | Sanitized account evidence and planning settings → visual reports. |
| `app.py` | `finance_parent(kind)` | Handles parent CSV import and account assumptions, and displays parent financial detail. | CSV/parent assumptions → finance state and parent report. |
| `app.py` | `parent_portal()` | Presents parent controls for points, redemptions, content, privacy and other parent-managed settings. | Parent choices → validated state updates. |
| `app.py` | `request_reward(item)` | Adds a pending reward request for a parent-approved item. | Reward/wishlist item → pending request; no immediate deduction. |
| `app.py` | `photo_upload(file)` | Validates, resizes and re-encodes a diary image as JPEG before upload. | Uploaded image → object-storage metadata reference. |
| `store.py` | `load()` | Reads the family’s single persisted state document, or a copy of defaults if it does not exist. | PostgreSQL row → Python state dictionary. |
| `store.py` | `change(fn)` | Applies a mutation while locking the state row and writing the result in one database transaction. | State-changing callback → updated JSONB state. |
| `store.py` | `authenticate(role, supplied)` | Checks the configured password for a role and updates role-level failure/temporary-block fields. | Role/password → success or a safe error result. |
| `store.py` | `balance(s)` / `award(s, key, points, label)` | Calculates points from ledger events and prevents duplicate awards with the same event key. | State and ledger event → balance / whether award was added. |
| `store.py` | `complete_task(task_id)` | Records a task once per day and applies its configured point award. | Task ID → serialized completion/ledger mutation. |
| `store.py` | `upload(data, mime, name)` / `download(meta)` | Stores or retrieves binary files using object-storage metadata. | Bytes/metadata → private object or downloaded bytes. |
| `store.py` | `approve_redemption(request_id)` | Approves a pending request only if it is still pending and the point balance covers it. | Request ID → approval plus ledger deduction. |
| `finance.py` | `parse_csv(raw, kind)` | Parses a supported broker export and removes selected account/security identifiers. | CSV bytes and account type → dated records and summary fields. |
| `finance.py` | `payment(balance, target, years, rate)` | Estimates the regular monthly contribution needed under an assumed return. | Current balance, target, duration, assumed rate → monthly contribution. |
| `finance.py` | `future_cost(annual, years, inflation)` | Projects the cost for each year of a four-year degree. | Annual budget and inflation assumption → projected four-year total. |
| `finance.py` | `positions(data)` | Summarizes net unit changes and recorded trade/distribution amounts within an activity export. | Export data → pandas summary; not proof of current holdings or profit. |
| `finance.py` | `market_history(symbol, start)` | Retrieves cached adjusted historical prices for a ticker. | Ticker/date → price series; not personal account return. |
| `account_performance.py` | `parse_statement_csv(raw)` | Validates rows in the normalized dated-statement evidence format. | CSV bytes → typed/validated ledger rows or an error. |
| `account_performance.py` | `reconcile(rows)` | Checks every supplied statement checkpoint and withholds performance results on mismatch. | Normalized ledger → status, issues, and (only if reconciled) metrics/history. |
| `account_performance.py` | `money_weighted(flows)` | Computes a conservative annualized money-weighted return when cash flows support a unique result. | Dated cash flows → percentage or no result. |
| `statement_import.py` | `normalize_broker(raw, broker, mapping)` | Maps supported broker activity rows into the normalized format while retaining row-level preview/errors. | CSV bytes, broker, column mapping → normalized rows and blocking issues. |
| `statement_import.py` | `review_statement(rows, sources=None)` | Checks duplicate evidence and full reconciliation before evidence can be saved. | Normalized rows/source labels → ready status and issues. |
| `statement_import_views.py` | `prepare_import(kind)` | Presents the parent import/mapping/review workflow. | Account kind and Streamlit upload → reviewed rows, ready flag, revision token. |
| `finance_views.py` | `saved_performance(state, kind)` | Recalculates performance only from parent-confirmed statement evidence. | State/account kind → reconciled report or no report. |
| `finance_views.py` | `child_performance(state, kind)` | Renders a child-facing allowlist of allocation percentages and an eligible annualized rate. | Reconciled report → reduced detail; no account dollar amounts. |
| `content.py` | `transcribe(raw, filename=...)` | Sends explicitly submitted audio to the configured transcription service. | Audio bytes → recognized text. |
| `content.py` | `interpret_social(text, image_bytes=None)` | Requests a cautious, structured possible interpretation of words or written context. | Text/image → four short fields; inputs/output are not saved by this function. |
| `content.py` | `news(topic)` / `batch_articles()` | Retrieves searched public headlines or The Batch article links. | Search topic/source → source-linked items. |
| `content.py` | `simplify(text)` | Drafts a child-friendly AI story, activity, and reflection question from supplied text. | Source text → structured draft for parent review. |
| `schools.py` | `baseline(name, residency)` | Returns the stored annual school budget baseline and its caveat/source note. | School/residency → planning input. |
| `visuals.py` | `apply_theme()` / `illustration(...)` / `hero(...)` | Applies shared visual styling and renders shared illustration/heading components. | Theme or visual key/title → Streamlit UI. |

## 3. Actual PostgreSQL tables

These are the only SQL tables defined in `schema.sql`. The schema definition is deliberately applied to the selected database; the application does not create tables automatically when it starts.

| SQL table | Columns | What is stored | Important note |
|---|---|---|---|
| `academy_state` | `id` integer primary key; `data` JSONB, required | The family’s application state: settings, points, routine completions, diary text/media references, finance exports/evidence, practice records, wishes/rewards, stories, and social items. | The code uses the single row `id = 1`. Feature names inside `data` are JSON keys/collections, **not separate SQL tables**. |
| `academy_auth_attempts` | `key` text primary key; `failures` integer; `blocked_until` timestamp with time zone | Role-keyed failed sign-in count and temporary lockout time. | The `key` is the role (parent/child), not a user account record. Passwords are not stored in this table. |

## 4. JSONB collections inside `academy_state.data`

The default state in `store.py` shows the principal top-level keys. Additional optional keys may be added by later feature code. These are application-level collections in the one JSONB row, not SQL tables with independent indexes or foreign-key constraints.

| JSON key | Example information it groups | Privacy / handling |
|---|---|---|
| `settings` | Point values, enabled features, school-cost assumptions, account goal/balance supplied by parent, privacy switches, selected school, arcade unlock time, help phrase. | Includes parent financial assumptions and access/privacy settings; parent controls must remain role-gated. |
| `ledger` | Dated point awards and deductions with event keys and labels. | Drives the displayed balance; duplicate event keys help prevent double awards. |
| `completions` | Task/day completion keys and dates. | Child routine history. |
| `diary` | Date, three answers, and photo metadata references. | Sensitive personal writing; visible to the parent as described in the UI. |
| `practice` | Date, selected drill, optional note, and video metadata reference. | Child-uploaded practice record and media reference. |
| `finance` | Imported custodial/529 export records and, when separately confirmed, normalized dated statement evidence. | Sensitive family financial data; parent reports are role-restricted. |
| `wishes` | Child’s LEGO wishlist title/category/link and parent-set approval/point information. | A user-supplied external link is stored as text; the app limits accepted links to HTTPS. |
| `rewards` | Parent-configured rewards and their approval/point cost. | Redemption requests are separate records. |
| `requests` | Pending/approved/declined reward request and any approved point deduction event. | Parent approval is required before redemption. |
| `stories` | Parent-approved simplified AI story, challenge, reflection prompt, source/date. | Draft is temporary until parent-approved story is saved. |
| `approved_videos` | IDs of drill videos approved by a parent. | Controls which curated embeds are shown. |
| `social_interests` | Parent-managed conversation-interest cards. | Saved cards can contain family-entered child interest details. |
| `social_phrases` | Phrases AJ explicitly chooses to save for later. | Parent-visible saved content; raw unsaved social-interpretation inputs are not a JSONB collection. |

The default state also defines what a brand-new family state looks like. A key in `DEFAULT` may have no saved data yet; parsing an uploaded CSV, adding a settings value or uploading media creates/updates state only when the relevant flow saves it.

## 5. Object storage and information that is not persisted

| Location | Information | How it relates to PostgreSQL |
|---|---|---|
| Private object storage | Binary diary-photo and practice-video contents. | `academy_state.data` records bucket/path/MIME/name metadata so the UI can find the object. The image-upload path re-encodes photos as JPEG; the video path stores the uploaded bytes. |
| Streamlit session state | Current page, form drafts, unapproved story draft, temporary social inputs/results, and other interaction state. | Lives for the active app session/reruns; it is not the durable family JSONB record. Sign-out/handoff clears session state. |
| External AI service request | User-selected transcription audio; social text or written-context image when enabled and submitted; article/source text for story drafting. | The app uses provider responses in the current flow. Those contents are not automatically a family-state row merely because they were sent for processing. Provider retention is subject to provider terms and is not established by app-level “not saved” behavior. |
| Public/external source response | Headlines, market-history data, and article links/text. | Some calls use Streamlit caching; source data is not a live brokerage holdings feed. Approved story text can be saved in `stories` after parent review. |

**Important distinction:** object storage being private does not, on its own, prove that each already-issued Streamlit media/download URL enforces the current app role and session. The release checklist records this as a remaining authorization limitation. Do not describe the table’s storage references as a complete per-request media access-control solution.

Passwords and service credentials are configuration/secrets, not part of the documented SQL schema or JSONB collection list. This reference deliberately contains no secret values, actual account data, or attached CSV records.

## 6. Tests and how to read their coverage

| Test file | What it exercises | What it does not establish by itself |
|---|---|---|
| `test_account_performance.py` | Evidence parsing, reconciliation checkpoints, FIFO basis, dated returns, broker normalization, import review, and a child-view allowlist. | Broker verification, tax correctness, production account data, or market forecasts. |
| `test_session_safety.py` | Signed-out data gate, expiry on rerun, parent-to-child handoff, reauthentication, sign-out, and parent approval before child session. | Automatic screen blanking while idle or authorization on previously emitted media URLs. |
| `test_social_skills.py` | Local phrase generation and handling/validation of social helper input and AI response structure. | Every provider response being correct or suitable in every real situation. |

Tests use synthetic or mocked inputs where described. A passing test does not prove provider availability, device/codec behavior, or production security properties not directly exercised by that test.

## 7. Practical maintainer notes

- Follow the configured Streamlit service path when changing the live Academy UI; do not assume the React/Vite starter is the running interface.
- Treat `academy_state.data` as one application document with real growth and migration implications, not as a set of already-normalized tables.
- Keep financial imports evidence-backed. Activity-only CSV summaries cannot independently prove current holdings or personal return.
- Keep parent-only numbers behind role checks and keep child financial displays intentionally reduced.
- For any change to uploads/downloads, check both page-level authorization and media delivery authorization.
- Check the release checklist’s date and scope before repeating a deployment or device-verification claim.

## Source files reviewed

`app.py`, `store.py`, `schema.sql`, `finance.py`, `account_performance.py`, `finance_views.py`, `statement_import.py`, `statement_import_views.py`, `content.py`, `schools.py`, `visuals.py`, the three Academy test files, `package.json`, and `.replit-artifact/artifact.toml`. File roles were also checked against the contents of the Vite starter files.
