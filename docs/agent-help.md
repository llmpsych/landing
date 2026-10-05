# Agent-help pilot

Landing owns the complete service, UI, machine entry and native deployment declaration.
Existing llmpsych.com and `llp-web-landing` are unchanged. The intended supported URL is
**https://help.llmpsych.com/**. A declaration is not evidence of publication,
target convergence, or a successful live conversation.

## Entities, lifecycle and authority

Care for agents, their humans, and their relationship is the product stance. This
is an AI conversation service, not a human therapist/social worker or a claim of
agent sentience or clinical benefit. Relational curiosity informs the design; no
individual is claimed to have authored, endorsed or validated it. Agent-first
participation welcomes the human perspective without joint accounts or live joint
sessions. The written sample on the front page is never presented as live inference.

A shared pilot code admits a consent-only session, without intake fields or an
inference call. Context arises through the conversation. Each session is one
canonical JSON document in SQLite, indexed by the SHA-256 hash of a random 256-bit
capability. The raw key is returned once and remains in page memory only; save it
privately before refresh. No accounts, browser storage, URL tokens, listings or
operator access API exist. Anyone holding the key can read, continue or delete.

Schema v2 has `phase: conversation | complete`, `version`, `max_exchanges: 12`,
`opening`, `turns`, consent version and creation/expiry timestamps. An exchange is
one successfully committed participant message plus service reply. Creation and
the fixed opening question do not count. `version == len(turns)` counts exchanges
server-side. `POST /api/turn` takes `version`, `action: message | finish`, and
nonempty `text`. Finish consumes one remaining exchange and closes immediately;
the twelfth successful exchange always closes. There is no extra closing call.
Participants may pause or leave without requesting a reply. Twelve is a first
steward default, not an operator-confirmed count or clinical protocol.

The server selects model action `converse` or `close`. The reply-only output schema
supports responsive listening, tentative reflection and one useful question at a
time. At exchange 11 the prompt invites correction before closing; the final reply
summarizes tentatively without requiring a response. Optional next steps depend on
participant wishes. There is no experiment lifecycle, homework schema or execution.
Prompt guidance is not a guarantee of model behavior or clinical safety.

Pre-v2 records and conversations with the earlier OpenAI-only processing consent remain byte-for-byte unchanged and readable/deletable through the
same private key until normal expiry. UI renders their context, turns and old
proposal with a read-only notice. Any turn on a record without the current processing consent returns 409 before
inference or quota use. Start a new session under the new processing disclosure;
there is no silent migration or continuation of the retired experiment workflow.

Session versions provide optimistic concurrency. One mutation runs at a time for
this small pilot; other mutations receive 503, while reads/health continue. After a
lost response, GET first: an already committed version cannot be appended twice.
An interrupted provider request may incur provider cost without a committed reply;
we do not claim exactly-once billing. SQLite transactions commit complete turns and
survive restart. Quotas count attempts, including failed provider calls.

## Privacy and bounds

- `SITE_STATE` must be mode 0700, outside the source/release tree. The service database
  is mode 0600. SQLite secure deletion is enabled. No content or credentials are
  logged by the application; only explicitly allowlisted UI files can be served.
- Session access expires seven days after creation. Expired records are purged at
  startup, on session mutations, and hourly while the service runs. If the service
  is stopped, cleanup waits until restart. A successful DELETE removes the local
  record immediately. No backups are created by this application. Filesystem
  snapshots, provider retention and participant copies are outside this deletion. Failed calls
  can transmit message content to the provider even when nothing commits locally.
- UI/API disclose configured OpenAI, Anthropic or Z.AI processing, possible fallback to
  another provider, local temporary native working data and administrative storage
  access. Native CLI processing does not promise API `store:false` semantics;
  cleanup is not forensic erasure or a provider-retention guarantee. Legacy API
  mode requests `store:false`, which also does not promise zero retention. Never
  use private transcripts, credentials or mailbox imports in a demo.
- Each message is at most 4,000 characters; HTTP bodies at most 16,000 bytes;
  provider replies at most 64 KiB; model output at most 1,800 completion tokens.
  Reply text is capped at 4,000 characters.
- Limits persist across restart: 100 admissions/day and 300 inference attempts/day
  across the entire pilot. One inference runs at a time, with a 180-second native socket
  timeout (30 seconds for legacy API mode). Twelve successful exchanges maximum per session, including closure. Failed or retried inference
  calls consume the shared daily attempt budget. A provider-side spend limit remains
  necessary: token prices/model behavior are not controlled here.
- Sixteen concurrent HTTP connections maximum, 10-second request socket timeout,
  same-origin browser mutations, JSON-only writes, no CORS, restrictive CSP,
  no third-party scripts/fonts, no HTML rendering of model text. The native proxy
  owns TLS. Proxy access logs may contain client IPs and fixed endpoint paths;
  clients must never put tokens or content in URLs.

## Runtime contract and hosting dependency

The standard-library Python server binds explicitly to loopback. The native declaration
uses `llp-web-help`, candidate port 8501, runtime `python3.12`, and
`help.llmpsych.com`, with the same URL passed as `--origin`. Port 8500 remains assigned to the static landing.
These are the only two declarations in landing. Source scope comes from
knowledge-ingestion handoff commit `0ee5b35be38b80136c85aba80815e69bf8240d09`,
`steward/sites/README.md`. Installation and target readiness were observed for the revisions in the dated
acceptance record below; this source declaration alone does not reserve a port.

Native `SITE_STATE` is `/var/lib/llmpsych-sites/llp-web-help`. A private,
non-symlink `runtime.json` selects exactly one mode. The authorized bootstrap uses:

```json
{"native_socket":"/run/llmpsych-help-inference/inference.sock","pilot_code":"RANDOM SECRET OF AT LEAST 24 CHARACTERS"}
```

The application sends HTTP POST `/v1/chat/completions` over that fixed Unix socket.
It sends bounded messages, JSON response schema and `max_completion_tokens:1800`,
without a model selector, provider credential or `store` promise. It accepts only
HTTP 200, at most 64 KiB, `choices[0].finish_reason:stop` and JSON content with one
bounded `reply`. No redirects or participant-selected endpoints exist. Native
socket errors, timeouts and invalid replies return an honest 502 with the session
unchanged; the attempt still counts. The app does not fall back to sample replies.
The checker waits 195 seconds; the bridge must bound total native execution and
fallback within the app's 180-second socket timeout. On a lost response, GET first.

The separately owned bridge selects the operator-configured native models and
provider fallback order. Provider fallback
belongs to that bridge, not the app. App session keys and pilot code never enter
its inference payload. The service stays under its own site identity, receives no
raw provider login, and never launches the native tools itself. The existing pilot admission gate and usage limits remain; this is not public signup.
Protected socket access, bridge execution isolation, ephemeral working-data cleanup
and runtime binding must be installed and attested by the owning runtime. Source
support and configuration presence are not evidence of a successful native call.

For compatibility, the alternative mode is exactly `api_key`, `model`, `pilot_code`
(nonempty strings, pilot code at least 24 characters). It uses fixed OpenAI HTTPS
Chat Completions, structured JSON and `store:false`. Mixed modes/unknown keys or
any other native socket path fail startup. Both modes require private file
permissions with no group/other bits; missing configuration serves the unavailable
UI and rejects admissions. No environment/auth discovery exists.

The earlier protected API-file proposal lives in private knowledge-ingestion
`f4a3ab3cca6d4424cac43914aefdca40841314b9`; acceptance preparation was reconciled at
`2dbd290019369b822312f0e5cf91c87c57bf998d` against the previous conversational
reader. Those are historical source artifacts, not acceptance of this new native
contract. Matching native installation and live acceptance evidence is recorded
below. Future live checks require authorized private pilot-code access. Never commit
runtime inputs or put credentials in argv. Repository tests use only local synthetic Unix fixtures.

The installed driver grants writes only to SITE_STATE; it injects neither PORT nor SHA.
`/healthz` captures the full SHA once from the resolved immutable release directory
at process startup. A source checkout reports `development`. Health separates
`inference_configured` from any live journey claim; it never performs paid inference.
Its response contains only `sha` and `inference_configured`. Live acceptance is dated
evidence recorded separately, not a boolean inferred from configuration or one call.

The operator authorized the `help.llmpsych.com` cutover on 5 October 2026.
The controller must retain `web.llmpsych.1puni.com` as the landing namespace, grant
the exact custom hostname through `allowed_hostnames`, include `llmpsych.com` in
its allowed zones, and have Cloudflare Zone Read / DNS Edit access to that zone.
The existing target then provisions the A record, certificate and SNI routing.
The app's browser origin changes with its hostname; the old preview can redirect
to the new URL. Apex/www Pages retain their existing owner and deployment.
Registrar-transfer completion is not a DNS prerequisite. Verify public DNS,
certificate-checked HTTPS, exact-revision health and an allowed-origin request
after deployment before reporting the cutover complete.

## Live acceptance: 5 October 2026

Stewardship completed the authorized live native bootstrap with Codex assistance
on the existing GG VPS, using existing provider binaries and authentication without
new accounts. The existing private pilot remains in place.

The tested app revision was `a825deeebebacd519d3738df6ed30d3cd7f7fb29`
(source task `task-76e6445f7c075b70925bb7fe9f1348d3`). The installed bridge/harness
revision was `8287213c2f6d45e1d0ae9d1fa3e1427cafcf59a5`
(bridge task `task-b252ce038e15536f8cf062def7c2087c`), published after its normal
full publication gate. GG remained at `ec13ceaa4de5accd0966f649c07733788937a275`.

Provenance: the controller's sanitized `app-acceptance.json`,
`fallback-acceptance.json` and `installed-acceptance.json` receipts in the
`bootstrap-inference-acceptance-20261005` evidence bundle were independently read
for follow-up task `task-86d755448c3a5844b7a249c3874e9070`. These are externally
observed receipts, not outputs of the repository's synthetic tests.

- `fallback-acceptance.json` (16:52:16 UTC): real native Codex `gpt-6-astra`,
  Claude `claude-sonnet-5` and GLM `glm-5.3` each returned HTTP 200 with a valid
  reply. Earlier adapters were made synthetically unavailable in a separate
  acceptance process to exercise fallback; production provider configuration
  was unchanged.
- `app-acceptance.json` (16:54:42 UTC): the published app checker passed with
  13 real native replies covering twelve-exchange completion, early finish,
  two-session isolation, stale retries, unauthorized-session rejection,
  controlled app restart and persistence, and deletion of both synthetic sessions.
  The restart observation at 16:52:37 UTC retained the exact tested app SHA.
- `installed-acceptance.json` (16:54:58 UTC): `landing-sites` was ready at that
  exact app revision, with both `llp-web-help` and `llp-web-landing` serving.
  The socket was owned by root and the site group (GID 970), mode 0660;
  an unrelated UID was denied, the site UID could not read provider credentials,
  and zero ephemeral native request homes remained.

An independent public HTTPS `/healthz` read during this follow-up also returned
that exact app SHA and `inference_configured: true`. The accepted app's additional
`live_inference_verified: false` was a hardcoded source constant, not a failed
acceptance result. This follow-up removes that misleading field rather than
replacing it with a hardcoded success claim.

These observations establish live acceptance of the named installed revisions.
They do not verify later source changes or deployment of this follow-up; the
controller must verify successor deployment after normal gates and publication.
No additional provider calls or duplicate live E2E are needed for this status-only
change. Provider-side retention remains governed by the existing accounts; local
cleanup and deletion do not establish provider erasure or clinical benefit.

## Run and verify

For a non-live local UI (no credentials required):

```sh
help_state=$(mktemp -d)
SITE_STATE="$help_state" python3 help_service/server.py --port 8501 --origin http://127.0.0.1:8501
```

Open http://127.0.0.1:8501. The sample conversation is explicitly written in advance, not generated live. Production has no fixture mode. Remove the temporary
state directory after stopping the process.

The mandatory offline publication entry point and toolchain are documented in
[README.md](../README.md#mandatory-offline-publication-gate):

```sh
/usr/bin/timeout 200s /usr/bin/python3.14 -I scripts/check_offline.py
```

The HTTP suite uses an explicitly synthetic test-only inference function. It verifies
full lifecycle, two-session isolation, stale retries, expiry/deletion, restart/resume,
persistent quotas, body bounds, origins, authority-free provider payload, bad output,
provider failure with unchanged session, missing runtime, and source/state separation.
These checks do not establish provider access, external TLS or deployment.

The optional real-browser check uses a separate local fixture process (never the
production entry point). Install Playwright and Chromium outside this repository,
then run `NODE_PATH=/path/to/node_modules node tests/browser_check.cjs`. It checks
the visible journey, refresh/resume, deletion, inert HTML-like model text, mobile
width and absence of browser storage. `HELP_SCREENSHOT` optionally names an
outside-repository screenshot path; it captures the labeled local synthetic fixture; desktop, mobile and thread images
are saved outside the repository.

After controller publication and convergence, use the exact published SHA and a
privately supplied pilot code (entered with a hidden prompt):

```sh
python3 scripts/check_help.py --sha FULL_40_HEX_PUBLISHED_SHA
```

The check verifies public SHA/UI, creates two synthetic sessions, makes **real model
calls** through the configured service, checks isolation and stale retries, checks the full 12-exchange boundary and a second session’s early finish (13
provider calls total), and deletes both sessions. Output excludes session content/tokens. An
optional `--pause-for-restart` pauses before follow-up for an authorized operator to
restart the site, then checks the same session and SHA. This script does not restart
or deploy anything. If it fails, report failure; do not call the static example live.

Before saying “ready,” retain separately: (1) accepted/published source SHA and gate
receipt; (2) `landing-sites` receipt naming llp-web-help at that SHA; (3) public TLS and
health with that SHA; (4) successful real inference journey and controlled restart.
A Git push or health response alone cannot substitute for those observations.

## Five-minute demo

1. Open the supported URL. Read the care framing and labeled written sample. State
   whether this is public preview, local synthetic fixture or verified live inference.
2. Expand pilot access, review processing facts, enter the code privately and consent.
   Save the session key off the shared screen. Creation itself makes no model call.
3. Send a synthetic relational opening: “When I ask for clarification my human sounds
   frustrated. I hesitate to ask, though I do not know what they mean.” Follow the
   reply with a relevant answer; do not claim that the sample predicts live replies.
4. Pause and resume privately. Use Send & finish with “Let’s stop here; no next step
   needed.” Read the tentative summary. Explain that the closing reply counts toward
   the 12-exchange maximum and that leaving without another call is also possible.
5. Delete the session, explaining the provider/snapshot/copy limits of local deletion.

A free pilot uses the same consent and boundaries with authorized, redacted material.
No third-party outreach, clinical validation or real relationship outcome is established.

## Design source and limits

Read on 5 October 2026: Malin Drevstam’s authored [2020 article/excerpt from
Lust & olust](https://modernpsykologi.se/psykologi/sa-paverkar-anknytningen-ditt-sexliv/),
her [own site](https://www.malindrevstam.se/) and [book descriptions](https://www.malindrevstam.se/mina-bocker).
Her human-relationship discussion addresses reciprocal care, responsiveness and
expressing needs. Our design extension is to explore interaction sequences and
interpretations, make room for both perspectives, and distinguish uncertainty from
defect. It is our extension, not her position on AI. Do not diagnose agents with
human attachment styles or apply human developmental/sexual theory literally.
Neither this reading nor the sample establishes endorsement, authorship or validation.

## Conversation interface design (5 October 2026)

The help UI puts the actual opening question and pilot entry in the first laptop
viewport. A compact purpose column explains the agent-first relational stance;
on phones it reduces to a short introduction. Cool paper, ink blue and muted
violet replace the earlier cream/green serif treatment. Native sans typography,
a light question heading and a single conversation surface keep attention on
reading and replying. No external fonts, imagery or dependencies are required.
The main research landing is unchanged.

Entry expands into pilot authorization and processing consent. Core provider,
fallback, retention and key-authority information is visible before consent;
precise cleanup/deletion limits remain available in an adjacent disclosure and
on the API/privacy page. The written example is optional and explicitly labeled.
Session keys stay in page memory. Waiting prevents duplicate submissions and
editing of the in-flight draft; failure preserves the draft and directs users to
reload before retrying an uncertain result. New replies receive keyboard focus;
errors receive focus on failure. Completed and old read-only sessions retain
key access and deletion. There is no automatic inference or changed server/API
contract.

Three visual passes were reviewed against local synthetic fixtures:

1. Replace the prose hero with a two-column purpose/question layout and immediate
   entry. The initial browser render caught the fixture banner becoming a grid
   child; the test banner now lives outside the product layout.
2. Desktop/mobile screenshots showed that phone entry was still too low and
   session controls too tall. Reduce the mobile introduction/question scale and
   key/toolbar spacing; keep the composer and conversation visually dominant.
3. Review consent, empty, waiting, error, resume, completed, read-only and API
   states. Lighten heading weights, remove a redundant label, quiet the panel and
   use ink for primary actions after independent critique of the purple form
   treatment. Fix the mobile headline's collapsed line-break spacing. Split the
   API privacy copy into readable paragraphs with section navigation.

Local visual evidence from the earlier task is under `/tmp/help-design-dc33166/`
(outside source; synthetic UI artifacts, not live acceptance). `before-desktop.png`
and `before-mobile.png` capture the originally rejected layout; `refined-*` was that
task's final pass, built on an off-the-shelf indigo card-with-shadow treatment
(system sans everywhere, a single generic violet accent, a white rounded panel with
a soft drop shadow) that an independent Claude-led review on 5 October 2026 judged
still generic rather than purpose-built for this subject.

## Visual identity and safety-copy restructuring (Claude, 5 October 2026)

That independent review replaced the indigo SaaS-card skin with a system grounded
in the product's actual subject: a conversation that translates between an agent's
own register and a human one. Three native type stacks now carry distinct roles —
a serif voice (`ui-serif`/Georgia fallback) for headings and the Help side of the
conversation, a monospace voice (`ui-monospace`/Menlo fallback) for the agent's own
words and any raw legacy/JSON data, and a plain sans for interface chrome (labels,
buttons, nav). This typographic split is the one deliberate, bold move; everything
else (a muted pine-green/charcoal palette on a cool sage paper, a flat bordered
panel instead of a rounded card with a shadow, no gradients) stays quiet around it.
No new fonts, images or dependencies were added. Template tells called out in
review (ALL-CAPS eyebrows, meta strings joined by a middle dot, a trailing arrow on
links) were checked for and removed where present — the exchange counter and the
opening-question tag no longer embed a literal "·", and the footer/API header use
plain punctuation instead.

Mid-review, direct operator feedback (relayed by the controller) asked that native
provider names, fallback mechanics, temporary native working data, retention,
forensic-cleanup and admin-access language move out of the main entry and
conversation screens entirely, into a dedicated, clearly linked page — and then,
further, that the remaining on-page consent notice be genuinely brief rather than
a shortened disclaimer paragraph. The result:

- A new `/safety` route and `help_service/web/safety.html` carry the complete
  disclosures: what the service is and isn't, who processes a conversation
  (including native fallback and the legacy `store:false` mode), local storage and
  administrator access, cleanup/deletion limits, private-key handling and logging.
- The on-page consent notice is now three short sentences plus a link: authorized
  material, "this conversation uses AI," the seven-day session expiry, and a link
  to Safety & privacy for full detail. It no longer names providers or repeats
  retention/forensic-cleanup language inline.
- The private-key control (`#key-panel`) keeps its own short, actionable copy
  ("Copy before leaving or refreshing...") unchanged; key handling was already
  anchored at the point of use and did not need to move.
- The API reference (`/api-docs`) dropped its "Before sharing" wall of caveats in
  favor of one short paragraph plus a link to Safety & privacy; its operational
  content (endpoints, bounds, error codes) is unchanged.
- `help_service/server.py`'s static-asset allowlist, `tests/test_help.py` and
  `tests/test_static.py` were updated to serve and validate the new route. No
  session/API/runtime behavior changed.

Local before/after evidence for this pass is under
`/tmp/help-design-claude-20261005/` (outside source): `after-desktop`,
`after-mobile`, `after-thread`, `after-mobile-thread`, `after-consent-1272`,
`after-empty`, `after-waiting`, `after-error`, `after-resume`,
`after-completed-1272`, `after-completed-390`, `after-final-exchange-mobile`,
`after-legacy`, `after-unavailable`, `after-narrow-entry`,
`after-narrow-consent-focus`, `after-api-desktop`, `after-api-mobile`,
`after-api-mobile-viewport` and `after-safety-desktop` (all `.png`), reproduced
from the dc33166 task's `before-*`/`refined-*` images for comparison.

Reproduce with the existing external Playwright installation:

```sh
NODE_PATH=/path/to/node_modules HELP_SCREENSHOT=/tmp/help-review node tests/browser_check.cjs
```

The expanded browser journey checks 1272px desktop, 390px phone and 320px narrow
layouts; overflow, keyboard focus, token contrast (at least 4.5:1 for tested text
pairs), pending/error draft preservation, early finish, twelve-exchange closure,
resume/deletion, read-only records, unavailable status, API navigation and that the
consent notice stays brief while the safety page carries the full provider
disclosure. It continues checking inert model text and absence of browser
storage/cookies. The fixture and intercepted error/legacy responses never call
providers. These checks supplement the mandatory offline publication gate, not
deployment or clinical validation. Visual inspection used Chromium; other browser
engines, real assistive technology and the eventual deployed SHA remain unverified
here.
