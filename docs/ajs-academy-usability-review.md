# AJ’s Academy: Holistic Usability Review

**Usability findings, potential bugs, and a prioritized improvement backlog**

Review date: October 12, 2026 • Audience: parents and the next implementation team

Reviewed source baseline: e843428 • Streamlit 1.65.0 • Private, single-family Streamlit application

Report inventory: 11 confirmed defects, 10 separately qualified risks/verification gaps, and 22 backlog items. Browser layout observations are recorded separately rather than inflated into a bug count.

## 1. Executive summary

AJ’s Academy has a sound starting structure: nine clearly named interests and learning areas, original illustrations, encouraging language, parent-controlled financial detail, and a points system that rewards participation rather than feelings or performance. Social Skills is especially careful about uncertainty, voluntary participation, and trusted-adult support.

The next iteration should emphasize reliability and reducing effort, not adding more tabs. The most important concerns are silent inaccuracies in the original financial-import path, diary attachment/deletion behavior, a broken news action, and the separately tracked privacy boundaries around unattended parent screens and copied media links.

This is an expert-led usability inspection plus synthetic-data browser and automated checks. It is not a study with AJ, a clinical assessment, a security certification, or a test on a physical iPad. No family records or uploaded family media were read or changed for this audit. No fixes were implemented.

### Recommended order

1. Stop silent financial-import errors: reject malformed activity and non-finite numbers; handle or explicitly block multiple 529 holdings.
2. Complete the existing media-access and unattended-screen privacy work, then verify the merged implementation. A private object bucket and a password page are different access boundaries.
3. Make diary saves and deletions predictable, including duplicate photos, partial storage failures, and clearing deleted content from the editor.
4. Make the daily child experience easier to enter: a short “Today” path, clearer navigation, readable controls, and low-pressure progress.
5. Improve parent setup and content management before expanding feeds, live deals, or new AI functionality.

## 2. Method and evidence

| Method | What was examined | What the result establishes |
|---|---|---|
| Browser interaction review | Unchanged app interface, synthetic family-day and parent/child handoff journey; 1024×768 and 768×1024 Chromium viewports | Layout and interaction behavior in those browser dimensions, not real iPad Safari behavior |
| Existing automated tests | 39 tests: 20 account/performance/import checks, 5 session-safety checks, 11 social-content checks, 3 social-customization checks | All 39 passed against mocked/synthetic state; no live financial or child records involved |
| Additional audit checks | 13 synthetic characterization/safety checks, including diary failure injection, original-import edge cases and the news action | All 13 checks passed; some deliberately confirm an undesirable behavior, so this is not “52 product tests all green” |
| Source inspection | UI routing, role checks, settings, uploads, rewards, content approval, finance parsing and planning, visual theme | Directly supported behavior and implementation risks; does not substitute for production end-to-end verification |
| Historical project evidence | Existing private-release checklist and prior handler-level media finding | A previously documented risk, clearly distinguished from fresh browser evidence |

The browser fixture replaced database access, authentication, object storage, AI, news, and market-data calls with in-memory synthetic substitutes. Real database and AI client entry points were configured to fail if called. The original UI, role gates, navigation, form logic, and local business logic remained in use.

Synthetic authentication allows testing role transitions without reading a real password. It does not validate real password comparison, persistent lockout, or deployment access settings. Synthetic uploads and deletion failures reveal application logic, not cloud-provider reliability. Synthetic headlines and AI responses allow interface checks, not a finding that live content is safe or accurate.

The original shared application remained running and unchanged. This report’s findings apply to the reviewed baseline. Separate task work may finish during the audit; an implementation marked complete elsewhere is not treated as fixed here until merged and verified.

### Evidence key

- B: directly observed browser behavior; exact coverage appears in section 8.
- A: reproduced with isolated Streamlit AppTest or a focused pure-function check.
- C: source inspection or a calculation from explicit source values.
- H: historical project evidence, not freshly reverified in this audit.
- U: untested or blocked; not a pass and not, by itself, a bug.

### Severity and priority

- High: can misstate financial information, compromise a privacy boundary, or cause inconsistent/lost data.
- Medium: materially impedes a core journey, accessibility, or understanding; a workaround usually exists.
- Low: confusing feedback or an avoidable extra step without demonstrated serious harm.
- P0: verify or address before relying on affected sensitive flows. P1: next iteration. P2: after reliability and privacy.
- Effort S/M/L is a rough implementation estimate, not a delivery-date promise. M generally includes UI, behavior, and regression checks; L involves a larger integration or persistence boundary.

---

## 3. Feature-by-feature usability scorecard

Ratings are qualitative: “Keep + improve” means the basic experience is useful but needs refinement; “Reliability first” means the underlying correctness or privacy concern should be addressed before expansion. These are not measurements of AJ’s abilities.

| Area | Strengths to preserve | Main improvement | Assessment |
|---|---|---|---|
| Home and navigation | Illustrated nine-feature grid, descriptive subtitles, friendly greeting, points and practice indicators | Reduce equal-choice overload; make the current daily activity and return path easier to discover; do not imply optional chores are daily obligations | Keep + improve |
| Login and handoff | A parent authorizes child sessions; parent-to-child handoff clears session drafts; the parent portal re-gates access | Simplify role-dependent login fields; separate parent setup from AJ’s sign-in; complete automatic visible parent-screen locking | Privacy work first |
| 1. My Investments | Child view emphasizes percentages and life aspirations; parent details are gated; market change is labeled separately from personal return | Replace technical account labels with short explanations; show freshness; strengthen original CSV validation and time-horizon assumptions | Reliability first |
| 2. My College Dream | School interests, soccer caveat, residency options and full-cost planning; source links and scenario assumptions | Correct fixed enrollment warning; detect multiple fund holdings; show a clearer school comparison and what parents still need to confirm | Reliability first |
| 3. My Diary | Exactly three supportive questions, partial answers accepted, parent visibility disclosed, participation not mood scoring | Prevent duplicate attachments and partial-deletion inconsistency; clear deleted editor text; add optional picture/audio support without forcing disclosure | Reliability first |
| 4. AJ’s Reminders | Large action buttons, visual task cards, once-per-day completion, adjustable future points, carryover | Show one task at a time when helpful; distinguish optional chores from expected routines; show “waiting for parent” reward status | Keep + improve |
| 5. Soccer | Learn/play/follow structure, short practice cues, reviewed-video gate, daily 50-point cap; no technique grading | Replace repeated generic step images with distinct movement cues; offer parent-verified short videos; validate actual iPad media behavior | Keep + improve |
| 6. LEGO | Interests/categories, wishes, parent-priced approval, no in-app purchases; live deals honestly marked unconnected | Visual catalog and parent-reviewed prices remain future work; make pending/approved wishes and redemption status clearer | Keep + improve |
| 7. AI Discoveries | Parent-reviewed stories, simple hands-on challenge, participation-only points, sources retained | Give draft-only feeds an empty state; let parents edit/unpublish/archive saved stories; make the weekly routine predictable | Keep + improve |
| 8. My Arcade | Parent-approved privilege, weekend default, no points charge, clear external-game boundary | Explain access duration with a simple child cue; verify external link/device return behavior without claiming Academy can lock the external site | Keep + improve |
| 9. AJ’s Social Skills | Local help available without AI; custom supports/trusted adults; cautious meanings; optional conversation practice; approved visual stories; skip/stop | Large show-to-adult wording and parent preview are already queued; reduce reading and tab-discovery effort; verify recording consent before capture | Keep + improve |
| Parent portal | Financial privacy, future-point settings, approval before rewards/stories, editable social supports | Add a setup checklist and clearer sections; improve content lifecycle and failure recovery; verify persistence and privacy outside UI mocks | Keep + improve |

### Cross-cutting observations

- The theme sets ordinary buttons to at least 3.4 rem high and tabs to at least 3.2 rem. This is helpful for touch, but smaller native segmented/radio controls and sidebar behavior still need device checks.
- Motion can be reduced through the operating-system preference; the existing reduced-motion rule should be retained.
- The same nine destinations appear as Home cards and sidebar links. This provides recovery, but a collapsed sidebar makes the Home return button particularly important.
- Several screens combine multiple columns, long explanatory captions, tables, and tabs. A child-facing mode should prefer short steps, visible choices, and optional expansion of explanations.
- Many general-purpose SVG illustrations use role="img" without a descriptive title; social scenario illustrations do have descriptive titles. If the art is decorative, mark it appropriately; if instructional, supply a meaningful accessible description.
- News links and shopping links ask for parent participation in captions. That wording is guidance, not an enforced parent gate. External pages can contain ads, recommendations, and material the Academy does not control.
- Parent report tables correctly distinguish statement-backed account evidence from activity exports and market prices. Preserve those distinctions when simplifying the child-facing text.

---

## 4. Confirmed bugs and defects

“Confirmed” means the stated behavior was reproduced with synthetic inputs, or is directly calculable from explicit source values. It does not mean a real family has experienced loss. For each item, the source snapshot and synthetic environment are the same as section 2.

| ID / severity | Feature and evidence | Reproduction and actual outcome | Expected outcome / impact |
|---|---|---|---|
| D01 • Medium | Diary photo save • A/C | Keep one valid PNG selected, enter an answer, then save repeatedly. Seven saves upload seven blobs; only six references remain in the entry | Saving unchanged attachments should not silently duplicate them. When references are replaced or capped, retained/deleted blob ownership must be explicit |
| D02 • Medium | Diary permanent deletion • A | Open a synthetic entry dated today as Parent; confirm and delete. The saved entry disappears, but Today’s story retains its answers. Clicking Save recreates them | After a confirmed deletion, clear the editor copy for that entry or explicitly identify it as a retained draft. Do not silently make “permanent deletion” easy to undo by accidental resave |
| D03 • Medium | 529 enrollment warning • A/C | Render a parent 529 view with a synthetic 2037 enrollment fund. The screen still states that the holding is a 2040–2041 portfolio | Derive warnings from the actual fund and intended enrollment assumptions, or state uncertainty. A false warning can send a parent to investigate a nonexistent mismatch |
| D04 • High, conditional on file | Original 529 import • A | Import a synthetic CSV with two recognized holding rows worth 1,000 and 2,000. The parser returns only the first fund and a balance of 1,000 | Aggregate supported holdings correctly or reject the multi-holding format with a clear explanation. Do not silently understate the starting savings used for planning |
| D05 • Medium | Original activity import • A | Put "nan" in a synthetic trade quantity. The original parser accepts it and the derived net-unit table contains NaN | Validate finite numeric values before saving or calculating. The reviewed-statement parser already does this; the original-export route needs equivalent explicit rejection |
| D06 • Low | AI feed empty state • A | Supply a nonempty stories list containing only an unapproved draft. Child view renders no story and no waiting/empty-state message | Show “Your parent is preparing your next story” whenever there are no approved stories. Do not disclose draft contents |
| D07 • Medium | Primary-button contrast • C | Evaluate CSS cream text #FFF8EC on blue #3E8FB0: contrast is about 3.45:1. Declared button text is 1.1 rem bold, about 17.6 px at a 16 px base | Ordinary text needs 4.5:1 under WCAG AA. This size is below the 18.67 px bold large-text threshold. Verify computed styles and adjust colors or qualified text size; this is a specific contrast finding, not a full accessibility audit |
| D08 • High, fault-injected | Diary deletion recovery • A/C | Delete an entry with two synthetic photos; make removal of the second blob fail. First photo is deleted, but the entry and both references remain saved; a generic section error is shown | Make deletion retry-safe and reconcile metadata with actual blob removal. A single service failure should not leave a saved entry referencing a photo already removed |
| D09 • High, conditional on file | Original activity import • A | Upload a CSV with one well-formed row and a later row missing a column. The original parser silently skips the malformed row and accepts the remaining history | Block or present a row-specific error before saving; do not present a shortened history as complete. The newer broker-statement path already surfaces malformed rows |
| D10 • Medium | Soccer upload guidance • B/C | Open Play soccer. The explanatory caption says “Maximum 40 MB” but the native upload control says “200MB per file.” The save handler rejects files over 40 MB | Configure the actual control and messages to the same per-feature limit, with early actionable feedback. A child should not select a large file based on a contradictory promise |
| D11 • Medium | Soccer/stock news action • B/A/C | Click Get latest headlines with a successful synthetic headline provider. The UI reports news unavailable, then section loading failed. The button key and saved-news key are both "news-" plus suffix | Use separate widget and result keys. Fetch success must show headlines; provider failure must show one clear message without breaking the section. Shared news_reader means the same defect applies to both soccer and company news |

### How to locate and reproduce the defects

- D01/D02/D08: app.py, diary() and photo_upload(). The repeated-save and deletion paths are separate: duplicate upload is not the same as a failed deletion. The synthetic failure test never removed a real object.
- D03: app.py, finance_parent() college branch. The warning string is unconditional and is not derived from the displayed fund.
- D04/D05/D09: finance.py, parse_csv() and positions(). These findings concern “Replace the account export,” not the newer reconciled-statement preparation path.
- D06: app.py, ai(). The empty-state condition checks whether any story exists rather than whether an approved story exists.
- D07: visuals.py, the primary-button CSS. Other text/control combinations were not exhaustively measured.
- D10: app.py, soccer() upload caption and 40 MB save guard. Screenshot qw820z shows both limits; no large file was uploaded.
- D11: app.py, news_reader(). A button widget owns the same session-state key that the handler tries to overwrite with a dictionary. The Streamlit assignment raises, and subsequent result handling treats button state as a news object. A synthetic provider returned successfully in the focused check, so this failure is not evidence of an external news outage.

A related reward usability issue was also reproduced: a pending request is deduplicated correctly in storage, but the request button stays enabled and repeats the “ready for your parent” notice. This is not a duplicate-points bug. It is included as backlog item G19.

---

## 5. Potential bugs, retained risks, and blocked checks

These are not all confirmed application failures. The evidence and next verification step are explicit so the next team does not mistake suspicion or a historical result for a new reproduction.

| ID / priority | Risk and current evidence | What would confirm or resolve it | Tracking |
|---|---|---|---|
| R01 • P0 | Copied media/download URLs may bypass app role checks. H: prior synthetic media-handler test documented anonymous byte access; C: baseline still emits native media and download output | Test the merged authorization implementation with synthetic image/audio/video/download links, anonymous and child sessions, logout, and Range requests. Do not test with family files or infer protection from a private bucket | #8; related follow-ups #18 and #19 appeared during this audit |
| R02 • P0 | A parent screen can remain visible while idle. C: expiry is evaluated at script rerun, not by a visible-screen timer. A: expired sessions do re-gate on the next interaction | Implement and test automatic visible-screen lock with an actual idle interval. Verify parent-to-child handoff, browser back, and restored tabs | #9 |
| R03 • P1 | iPad HEIC/photo-picker conversion, microphone permission, denial recovery, and MOV codecs may differ from Chromium. U: not tested on a physical device in this audit | Test current iPad model/iPadOS/Safari; use synthetic photos and video. Check allowed, denied, interrupted, and unsupported-file paths | New device-validation work; prior user-reported checks are historical only |
| R04 • P1 | Social audio capture is displayed before the speaker-permission checkbox is checked. C: submission rejects nonconsented audio, but the recorder itself is not conditionally gated | Verify on device whether local recording can begin before consent. Gate capture as well as transmission, and re-require permission for each new recording | New; distinguish local capture from the existing server submission check |
| R05 • P1 | Raw soccer/stock headlines can include age-inappropriate material. C: headlines are displayed directly; “read with a parent” is advice, not approval enforcement | Evaluate representative real feeds with a parent; add a parent-reviewed child reading view or a meaningful gate. Synthetic feeds cannot establish real-content suitability | New; distinct from #2’s LEGO deals/weekly routine |
| R06 • P2 | Invalid or older saved settings may fail a page: missing keys, unsupported favorite_school, malformed arcade deadline. C: several direct lookups/index/date parsing paths exist | Use isolated legacy fixtures and malformed settings; check migration/defaulting and safe recovery, without replacing real state | #13 |
| R07 • P2 | Age-21 and college horizons can become stale over time. C: custodial planning uses a fixed 13 years, college defaults to 11; no automatic aging is represented | Define parent-controlled target dates, review reminders, and stale-as-of labels. Confirm scenario calculations after date changes | New |
| R08 • P2 | Parent role lockout is shared household-wide. C: failures are stored by role, so repeated failed parent attempts can temporarily block legitimate parent access | Isolated authentication tests for lockout, recovery, concurrent clients and deployment access boundary; never deliberately lock the real parent account | New verification/design decision, not a request to weaken authentication |
| R09 • P2 | Pending redemptions preserve their requested point price when a wish is later repriced. C: requests snapshot title/points and approval uses that snapshot | Define whether the original price remains valid or requires reconfirmation. Test repricing and insufficient balance in two isolated sessions | New policy decision; not labeled a confirmed pricing bug |
| R10 • P1 verification | A fresh unauthenticated capture of the live proxied preview showed only the Streamlit shell. U: this does not establish whether authenticated pages or ordinary browser loading fail | Confirm startup and WebSocket loading through the actual preview path. The synthetic localhost review cannot prove the live proxy path works. No production failure is asserted | Separate preview-path verification if the symptom is reproducible |

### Important non-bugs and boundaries

- An activity export cannot establish complete holdings or personal investment returns. Withholding unverified personal performance is correct.
- Practice earns one 50-point award per day, not 50 points for each uploaded video. The tested once-per-day behavior is intentional.
- No points are deducted for a reward request; deduction happens only on parent approval. Duplicate approval is idempotent in the isolated check.
- Points carrying over, AI participation starting at zero points, and a locked weekday arcade are intentional parent-controlled defaults.
- The arcade lock controls the Academy’s link, not access to the external Lovable site from a copied URL.
- The diary weekly view measures participation and repeated words, not mental-health or developmental growth. Avoid “happy/sad scores” inferred from text.
- A safe AI prompt is not proof that every live model response will be appropriate. Provider behavior and retention were outside this synthetic audit.

---

## 6. Prioritized feature backlog

This is a report backlog, not authorization to implement every row. Existing project tasks are referenced rather than duplicated. New rows include concrete acceptance criteria so they can become bounded implementation tasks.

| Priority / ID | Feature and user benefit | Acceptance criteria | Effort | Dependencies / tracking |
|---|---|---|---|---|
| P0 • G01 | Trustworthy original financial imports: avoid misleading savings and account history | Reject malformed/non-finite rows with line-specific errors; support or clearly block multiple 529 holdings; failed import preserves prior evidence; fix derived enrollment warnings; regression fixtures cover all four cases | M | Proposed #20; D03/D04/D05/D09; preserve reconciled-statement checks |
| P0 • G02 | Private media stays private after copying a link | Synthetic links enforce role/session authorization, including downloads and range playback; logout/handoff behavior is explicit; avoid treating object location as authorization | L | Existing #8, marked implemented during audit but not validated in this baseline; #18 memory resilience and #19 authorization regression checks |
| P0 • G03 | Hide sensitive parent pages when the iPad is left alone | Visible financial details lock automatically after inactivity; reauthentication needed; timer does not depend on a new click | M | Existing #9; R02 |
| P1 • G04 | Reliable diary save and deletion: protect family memories and privacy | Same selected photo is not duplicated by a text-only resave; attachment removal is explicit; deletion is retry-safe across storage/DB failures; deleting today clears/relabels editor drafts | M | Proposed #21; D01/D02/D08; coordinate media APIs with #8 |
| P1 • G05 | A calmer “Today” home with discoverable navigation | Parent chooses a short daily sequence; AJ sees the next action and a clear Home return; all nine interests remain reachable; portrait controls fit; pending rewards use waiting state; primary text meets contrast requirements | M | Proposed #22; preserve nine features and existing reward rules |
| P1 • G06 | Large, easy-to-show help request for a trusted adult | One action shows selected wording in large, uncluttered type; return/close is clear; no score or recording required | S–M | Existing #15; local scripts already exist |
| P1 • G07 | Guide parent setup without hunting through menus | A private checklist covers routine points, conversion, rewards, video review, finance source dates and social privacy; child sees readiness cues, not parent-only values | M | New; links to existing settings rather than a parallel data model |
| P1 • G08 | Parent-managed AI story lifecycle | Parents edit, archive/unpublish and remove saved stories; child sees only approved items; no-approved-story state explains what is coming next; changes do not accidentally award challenge points twice | M | New; D06; preserve challenge ledger keys |
| P1 • G09 | Parent-reviewed soccer/stock news for child reading | Parent selects suitable stories; child sees a short, dated summary and source; external browsing needs explicit adult involvement; outages show cached/reviewed content freshness, not “latest” claims | M–L | New; R05; depends on G22; distinct from existing #2 |
| P1 • G10 | Make story review regressions visible before release | Draft/add/edit/approve/remove paths and child allowlist covered with synthetic UI tests; skip/stop preserved; legacy data does not crash the child screen | M | Existing #14 |
| P1 • G11 | Private backup and restore | Export/restore includes family state plus media ownership, versioning and confirmation; failed restore does not overwrite valid records | L | Existing #12; coordinate #13 |
| P1 • G12 | Preserve saved data as settings evolve | Missing/legacy settings receive documented safe defaults; upgrades are versioned and idempotent; malformed records explain recovery rather than failing entire pages | M | Existing #13; R06 |
| P1 • G13 | Real-iPad recording and upload validation | Unify uploader limits and messages; document model/OS/browser; test camera/photo picker, HEIC behavior, supported MOV/MP4 playback, microphone grant/deny/interruption, keyboard and orientation; verify speaker permission before local capture | M | New; D10/R03/R04; no family media needed |
| P2 • G14 | Distinct picture steps for soccer drills | Each chosen move has three meaningfully different visual instructions; parent verifies video suitability and short duration; no requirement to grade technique | M | New; current generic/repeated cues are only a starting point |
| P2 • G15 | Flexible routines without pressure to complete every chore | Parent chooses school/weekend/optional tasks and reminder count; daily denominator includes only planned tasks; effort celebrated; points and history carry over unchanged | M | New; preserve optional kindness and existing once/day awards |
| P2 • G16 | Parent preview of customized help choices | Parent sees child layout with long labels and chosen symbols before saving; validation/reorder/removal remain reliable | S | Existing #16 |
| P2 • G17 | Monthly statements without rebuilding the entire history | Stage new-period evidence against saved reviewed history; duplicates/corrections explained; parent confirmation and full reconciliation required | L | Existing #10 |
| P2 • G18 | LEGO choices and a regular discovery routine | Visual parent-reviewed set catalog with dated prices/seller/shipping context; no false best-deal claim; approved wishes connect to points; weekly story preparation remains parent-controlled | L | Existing #2; source permissions and actual retailer access required |
| P2 • G19 | Clear reward-request status | Replace repeated request action with “Waiting for parent”; approval/decline explanation and remaining points visible; no duplicate request or deduction | S | New; storage already deduplicates correctly |
| P2 • G20 | Dated goals and understandable finance explanations | Parent maintains target dates/as-of balances; child gets short explanations of percentages and growth; annual review prompts refresh school costs and residency assumptions | M | New; R07; no financial promises or private dollar amounts in child view |
| P2 • G21 | Optional read-aloud and low-stimulation settings | Parent controls read-aloud/visual density; instructions can be heard without recording; reduced motion and quiet mode respected; text and pictures remain usable without audio | M | New; accessibility supports, not diagnostic features |
| P1 • G22 | Working news controls with useful failure recovery | Widget keys and saved-results keys are distinct; successful synthetic feeds display soccer and company headlines; changing a topic does not show another topic’s results; outages keep the section usable | S | New; D11; not covered by the LEGO/weekly-routine task |

### Suggested first implementation batch

Three new follow-ups were proposed: #20 “Keep savings figures accurate when account files are uploaded” (G01), #21 “Save and delete diary photos without losing track of them” (G04), and #22 “Make AJ’s daily choices easier to find and read” (G05). Keep already queued privacy and social-display work in their existing tasks. These are proposals, not fixes made during the audit or permission to build the entire backlog.

---

## 7. Test coverage and boundaries

| Area | Fresh automated evidence | Browser coverage | Remaining validation |
|---|---|---|---|
| Login / role handoff | 5 existing isolated session checks, including signed-out load prevention, expiry on rerun, handoff, logout and child authorization | See section 8 | Actual persistent authentication/lockout and production access boundary |
| Investment / statement evidence | 20 existing checks; original-import non-finite/malformed cases; planner arithmetic sanity | See section 8 | Broker-supplied real-world formats, external price service; no real CSV analyzed in this audit |
| 529 planning | Two-holding synthetic parser case; zero-return payment; four-year cost sum; enrollment-warning mismatch | See section 8 | Current university budgets/residency and qualified-expense eligibility require parent/provider confirmation |
| Diary | Repeated selected-photo save, today deletion/editor state, partial object deletion outage | See section 8 | Actual storage reliability, HEIC/device formats, microphone and provider transcription |
| Reminders / rewards | Routine completion disabled after one award; duplicate request deduplicated; repeat parent approval does not deduct twice | See section 8 | Real DB concurrent requests and long-term carryover/backup |
| Soccer | Award key/source logic inspected; no quality grading claimed | See section 8 | Real provider videos/embedding/ads, actual upload/codec playback; browser fixture did not grade a drill |
| LEGO | Wishlist/reward forms and link validation inspected | See section 8 | No live prices/deals integration exists; external sites not audited |
| AI | Parent-approval filter and draft-only empty-state case | See section 8 | Live article retrieval, model response safety/quality, future weekly freshness and story lifecycle |
| Social Skills | 11 existing pure/mock content checks; 3 customization UI checks; local help works while AI disabled | See section 8 | Real microphone/camera, speaker consent before capture, live interpretation safety; no child research |
| Arcade | Weekend/override/no-points implementation inspected | See section 8 | External site accessibility and return behavior; no external access control promised |
| Accessibility / layout | Button-color calculation, theme/motion/SVG review | See section 8 | Full screen-reader and keyboard assessment, text zoom, actual iPad keyboard/orientation |

Current automated outcomes: 39 existing regression tests passed; 13 additional audit checks passed. Two audit-harness assumptions were corrected before interpreting findings: an outside-form checkbox needed a rerun before its dependent deletion button existed, and a button’s transient True value resets after the run. These were not application defects and are not listed as such.

## 8. Browser observations and evidence

The single pass completed and ended signed out. Its verdict was failure because of a confirmed upload-guidance defect; the follow-up cheap AppTest check also confirmed the shared news action defect. Core role handoff, routine completion, diary save, parent reward approval, and social-story approval were exercised successfully. Every browser assertion must be read alongside the synthetic-provider limitations in section 2.

| Journey | Observed browser result | Limitations / interpretation |
|---|---|---|
| Parent login and setup | Parent login worked with review-only credentials; all eight Manage destinations were inspected; financial 529 view showed the incorrect fixed fund warning | Fake authentication; no real password, cloud store or real account data |
| Handoff and Home | Switch to AJ’s view opened Home; all nine tiles were exposed; child finance pages had percentages but no dollar figures or parent-import controls | This verifies interface allowlists, not copied-download or live deployment authorization |
| Routines and rewards | Wake up awarded 5 once, from 200 to 205; completion disabled. TV request stayed pending without deduction; parent approval reduced balance to 105 | Browser did not approve a second time; separate isolated check confirms duplicate approval does not deduct again. Repeated request screenshot looked ambiguous, but synthetic state held one pending request |
| Diary | Blank save was rejected. Three synthetic answers saved and appeared in the dated history | Browser did not test same-day editing, photos, voice or deletion; these were covered only where specified by isolated characterization checks |
| Investments and college | Percentages and review-pending messages were visible; technical terms remain in child copy | No market-performance action or external price call; real imports and university facts not independently re-researched |
| Soccer | Chosen drill stayed video-gated until parent review; picture steps were available; upload limit messages conflicted; headline action failed | No media selection/upload, YouTube/source visit, camera or microphone; D11 subsequently isolated from provider behavior |
| LEGO | Added a synthetic moon-robot wish, saw waiting-for-parent-pricing status, and removed it | No product price checks, purchases or external browsing |
| AI and arcade | Approved story shown, draft hidden; challenge disabled after participation without changing zero-configured points. Weekday arcade stayed locked, no points charged | No live AI generation, weekend/time-expiry wait or external game |
| Social help and meaning | Generated/saved words were found in My helpful words; generic synthetic interpretation appeared; forced provider outage gave trusted-adult fallback | Stub output cannot establish live interpretation quality. Screenshot timing did not conclusively prove dismissal of the previous alert |
| Conversation and practice stories | Interest starter appeared; approved scenarios only; response feedback stayed supportive; Skip and Stop worked without points changes | No measurement of real conversational/social improvement |
| Parent social-story lifecycle | Added, edited and approved a synthetic scenario; it appeared for AJ, then was removed. Test-created wish and phrase also removed | Exercised one happy-path lifecycle; comprehensive boundary regression work remains in #14 |
| Sign-out | Returned to login screen | Does not prove previously issued media links are revoked |

### Layout and interaction findings

- At 768×1024 with the sidebar expanded, Home keeps three narrow columns. “AI Discoveries” breaks within the word “Discoveries”; the other cards require multiple lines. Independent sidebar and page scrolling add navigation effort. This is observed wrapping, not proof that every iPad orientation is unusable.
- The Social Skills tab strip horizontally overflows, and the “Help me” label is partly obscured at the captured scroll position, even in the landscape capture. Scroll arrows exist, so this is a discoverability problem rather than proof that the tab cannot be reached.
- Buttons were generally large. Small text and heavy wrapping, especially beside the sidebar, remain a concern for independent child use.
- Reward status is not reflected in the request button. The UI keeps an enabled Ask action while a request is pending, and permits asking again after an approved reward. The first is confusing; repeated use after fulfillment may be valid, so define that policy rather than calling it an extra-deduction bug.
- No browser-console application errors were reported. A chart scale warning and password-field DOM warnings were reported. Visual rerenders sometimes left a capture on the previous view; the tester used subsequent live body/layout checks rather than treating those captures as definitive.

### Screenshot evidence index

The runner provided session screenshot IDs, not downloadable local image exports. This Word report therefore includes observations, reproduction steps and the reference index rather than embedding inaccessible image files. The screenshots were synthetic-only; IDs are session evidence references, not web links.

| Evidence ID | Capture | What it supports |
|---|---|---|
| qw820z | Soccer Play, landscape | Simultaneous “Maximum 40 MB” and “200MB per file” messages; D10 |
| azopvk | Child Home after repeated ask | Ambiguous similar reward-card presentation; not proof of duplicate state or deduction |
| bdeb2f | 1024×768 Home, lower tiles/rewards | Landscape navigation and approved reward status |
| 6limh6 | 768×1024 Home | Narrow three-column cards and midword “AI Discoveries” wrapping |
| 37f6g9 | 1024×768 Social | Paused practice and partly obscured left tab label |
| 5mz3n1 | 768×1024 Social | Saved helpful-word entry |
| 5vp56p | 768×1024 story selector | Approved scenario choices only |
| ljqat5 | Final signed-out login | End-of-journey sign-out |

## 9. Retest checklist for the next iteration

- After G01: synthetic malformed/NaN/multi-fund imports must block or reconcile correctly; old saved evidence must be unchanged on failure.
- After G04: save identical photo selection twice, edit only words, replace/remove attachments, delete today’s entry, inject individual storage and DB failures, and verify consistent retry behavior.
- After privacy tasks: anonymous/child/copied-link/Range/logout cases with synthetic media, then actual idle-screen hiding. Do not use actual financial downloads as fixtures.
- After G05: real iPad portrait/landscape, large-text/zoom, soft keyboard, touch/focus, Home recovery and parent handoff. Confirm next-action navigation does not remove any interest.
- After content work: verify draft withdrawal, empty/approved feeds, safe source labels, external-parent boundaries and explicit AI/provider failure recovery.
- Once reliability is improved, run a short parent-observed session with AJ: find a routine, share a diary thought, ask for help, choose a practice story, and return Home. Observe effort and confusion without scoring his social skills or requiring disclosure.

## 10. Reproducibility and artifact notes

The report’s source is docs/ajs-academy-usability-review.md. The Word builder is scripts/build_academy_review_doc.py. The isolated fixture, characterization checks, logs, source hash manifest, browser evidence and DOCX are under generated-artifacts/usability-review/ or generated-artifacts/. Generated outputs are excluded from Git/deployment by the existing ignore rules.

Relevant implementation: artifacts/ajs-academy/app.py; store.py; content.py; visuals.py; finance.py; finance_views.py; account_performance.py; statement_import.py; statement_import_views.py; schools.py. Existing test files: test_account_performance.py, test_session_safety.py, test_social_skills.py and test_social_customization.py. Historical context: PRIVATE_RELEASE_CHECKLIST.md.

No production database query, account transaction, purchase, live AI request, or deployment change was part of this audit. No claim is made that mock persistence proves PostgreSQL durability or that Word package validation replaces opening the document in Microsoft Word.
